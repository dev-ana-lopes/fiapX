import asyncio
import json
import logging
import os
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID

from aio_pika import DeliveryMode, ExchangeType, IncomingMessage, Message, connect_robust
from fiapx_api.config import get_settings
from fiapx_api.db import session_factory
from fiapx_api.messaging import (
    EXCHANGE,
    FAILED_ROUTING_KEY,
    RETRY_ROUTING_KEY,
    declare_video_topology,
)
from fiapx_api.minio_storage import MinioStorage
from fiapx_api.models import ProcessingJob, Video
from fiapx_api.progress import RedisProgressStore
from fiapx_shared import VideoEvent, VideoProcessingMessage, VideoStatus
from prometheus_client import Counter, Histogram, start_http_server
from sqlalchemy import select, update

from .processor import VideoProcessor, make_zip
from .resilience import PermanentError, lease_for, retry_delay, should_retry

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)
storage = MinioStorage()
WORKER_ID = os.getenv("HOSTNAME", "video-worker")
processing_retries = Counter(
    "fiapx_video_processing_retries_total", "Video processing retries requested"
)
processing_completed = Counter(
    "fiapx_video_processing_completed_total", "Videos processed successfully"
)
processing_failed = Counter("fiapx_video_processing_failed_total", "Videos that failed processing")
processing_duration = Histogram(
    "fiapx_video_processing_duration_seconds", "Video processing duration in seconds"
)


async def progress(video_id: UUID, value: int, state: VideoStatus, stage: str) -> None:
    store = RedisProgressStore()
    try:
        await store.set_progress(video_id, value, state.value, stage)
    finally:
        await store.client.aclose()
    async with session_factory() as session:
        await session.execute(
            update(Video).where(Video.id == video_id).values(progress=value, progress_stage=stage)
        )
        await session.commit()
    delay = get_settings().video_processing_stage_delay_seconds
    if delay > 0:
        await asyncio.sleep(delay)


async def publish_event(
    payload: VideoProcessingMessage, status: VideoStatus, error: str | None = None
) -> None:
    event = VideoEvent(
        event_type=f"video.processing.{status.value.lower()}",
        job_id=payload.job_id,
        video_id=payload.video_id,
        user_id=payload.user_id,
        status=status,
        error_message=error,
        correlation_id=payload.correlation_id,
    )
    connection = await connect_robust(get_settings().rabbitmq_url)
    async with connection:
        channel = await connection.channel(publisher_confirms=True)
        exchange = await channel.declare_exchange(EXCHANGE, ExchangeType.TOPIC, durable=True)
        await exchange.publish(
            Message(
                event.model_dump_json().encode(),
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
                message_id=str(event.event_id),
            ),
            routing_key=event.event_type,
        )


async def publish_job(
    payload: VideoProcessingMessage, routing_key: str, expiration: int | None = None
) -> None:
    connection = await connect_robust(get_settings().rabbitmq_url)
    async with connection:
        channel = await connection.channel(publisher_confirms=True)
        exchange, _ = await declare_video_topology(channel)
        await exchange.publish(
            Message(
                payload.model_dump_json().encode(),
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
                message_id=str(payload.event_id),
                expiration=expiration,
            ),
            routing_key=routing_key,
        )


async def mark_processing(video_id: UUID, job_id: UUID | None, attempt: int) -> bool:
    async with session_factory() as session:
        job: ProcessingJob | None = None
        if job_id:
            job = (
                await session.execute(
                    select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update()
                )
            ).scalar_one_or_none()
            if job and attempt < job.attempt:
                return False
        result = await session.execute(
            update(Video)
            .where(Video.id == video_id, Video.status == VideoStatus.QUEUED)
            .values(
                status=VideoStatus.PROCESSING,
                progress=5,
                progress_stage="Preparando processamento",
                started_at=datetime.now(UTC),
                error_message=None,
            )
        )
        if cast(int, getattr(result, "rowcount", 0)) != 1:
            return False
        if job_id:
            if job:
                job.status, job.started_at, job.attempt = (
                    VideoStatus.PROCESSING,
                    datetime.now(UTC),
                    attempt,
                )
        await session.commit()
        return True


async def finish(
    payload: VideoProcessingMessage, result_key: str | None, error: str | None = None
) -> None:
    async with session_factory() as session:
        video = await session.get(Video, payload.video_id)
        if video:
            video.status = VideoStatus.COMPLETED if result_key else VideoStatus.FAILED
            video.progress = 100 if result_key else 0
            video.finished_at = datetime.now(UTC)
            video.result_object_key = result_key
            video.error_message = error[:500] if error else None
        if payload.job_id:
            job = await session.get(ProcessingJob, payload.job_id)
            if job:
                job.status = VideoStatus.COMPLETED if result_key else VideoStatus.FAILED
                job.finished_at = datetime.now(UTC)
        await session.commit()


async def return_to_queue(video_id: UUID, job_id: UUID | None, next_attempt: int) -> None:
    async with session_factory() as session:
        video = await session.get(Video, video_id)
        if video and video.status == VideoStatus.PROCESSING:
            video.status, video.progress, video.progress_stage = (
                VideoStatus.QUEUED,
                0,
                "Aguardando nova tentativa",
            )
            if job_id:
                job = await session.get(ProcessingJob, job_id)
                if job:
                    job.status, job.attempt = VideoStatus.QUEUED, next_attempt
            await session.commit()


async def handle(message: IncomingMessage) -> None:
    try:
        payload = VideoProcessingMessage.model_validate(json.loads(message.body))
    except Exception:
        logger.exception("video.processing.invalid_message")
        await message.reject(requeue=False)
        return
    started = time.monotonic()
    # If publishing the retry/DLQ marker itself fails, leave the delivery unacked
    # so RabbitMQ can redeliver it after the broker recovers.
    async with message.process(requeue=True):
        async with lease_for(payload.video_id, WORKER_ID):
            if not await mark_processing(payload.video_id, payload.job_id, payload.attempt):
                return
            try:
                with tempfile.TemporaryDirectory(prefix=f"fiapx-{payload.video_id}-") as directory:
                    root = Path(directory)
                    input_path, frames, archive = (
                        root / "input",
                        root / "frames",
                        root / "frames.zip",
                    )
                    await progress(payload.video_id, 10, VideoStatus.PROCESSING, "Baixando vídeo")
                    await storage.download(payload.object_key, input_path)
                    await progress(payload.video_id, 25, VideoStatus.PROCESSING, "Validando vídeo")
                    processor = VideoProcessor()
                    duration = await processor.probe(input_path)
                    await progress(payload.video_id, 35, VideoStatus.PROCESSING, "Extraindo frames")
                    result = await processor.extract_frames(input_path, frames, duration)
                    await progress(payload.video_id, 70, VideoStatus.PROCESSING, "Frames extraídos")
                    make_zip(result.output_directory, archive)
                    await progress(payload.video_id, 80, VideoStatus.PROCESSING, "Compactando ZIP")
                    result_key = (
                        f"users/{payload.user_id}/videos/{payload.video_id}/result/frames.zip"
                        if payload.user_id
                        else f"videos/{payload.video_id}/result/frames.zip"
                    )
                    await storage.upload(result_key, archive, "application/zip")
                    await progress(
                        payload.video_id, 90, VideoStatus.PROCESSING, "Enviando resultado"
                    )
                    if not await storage.exists(result_key):
                        raise RuntimeError("result upload could not be verified")
                await finish(payload, result_key)
                await progress(payload.video_id, 100, VideoStatus.COMPLETED, "Concluído")
                await publish_event(payload, VideoStatus.COMPLETED)
                processing_completed.inc()
                processing_duration.observe(time.monotonic() - started)
                logger.info(
                    "video.processing.completed",
                    extra={
                        "video_id": str(payload.video_id),
                        "worker_id": WORKER_ID,
                        "attempt": payload.attempt,
                        "correlation_id": payload.correlation_id,
                    },
                )
            except (ValueError, PermanentError) as error:
                await finish(payload, None, str(error))
                await publish_event(payload, VideoStatus.FAILED, str(error)[:500])
                await publish_job(payload, FAILED_ROUTING_KEY)
                await progress(payload.video_id, 0, VideoStatus.FAILED, "Falha no processamento")
                processing_failed.inc()
                processing_duration.observe(time.monotonic() - started)
            except Exception as error:
                if should_retry(payload.attempt, get_settings().video_processing_max_retries):
                    await return_to_queue(payload.video_id, payload.job_id, payload.attempt + 1)
                    next_payload = payload.model_copy(update={"attempt": payload.attempt + 1})
                    processing_retries.inc()
                    await publish_job(
                        next_payload, RETRY_ROUTING_KEY, retry_delay(payload.attempt) * 1000
                    )
                    logger.warning(
                        "video.processing.retry",
                        extra={
                            "video_id": str(payload.video_id),
                            "worker_id": WORKER_ID,
                            "attempt": payload.attempt,
                            "correlation_id": payload.correlation_id,
                            "error_type": type(error).__name__,
                        },
                    )
                else:
                    await finish(payload, None, "não foi possível processar o vídeo")
                    await publish_event(
                        payload, VideoStatus.FAILED, "não foi possível processar o vídeo"
                    )
                    await publish_job(payload, FAILED_ROUTING_KEY)
                    await progress(
                        payload.video_id, 0, VideoStatus.FAILED, "Falha no processamento"
                    )
                processing_failed.inc()
                processing_duration.observe(time.monotonic() - started)
                logger.exception(
                    "video.processing.failed",
                    extra={
                        "video_id": str(payload.video_id),
                        "worker_id": WORKER_ID,
                        "attempt": payload.attempt,
                        "correlation_id": payload.correlation_id,
                    },
                )


async def run() -> None:
    start_http_server(int(os.getenv("METRICS_PORT", "8001")), addr="0.0.0.0")
    connection = await connect_robust(get_settings().rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=get_settings().video_worker_prefetch)
    _, queue = await declare_video_topology(channel)
    await queue.consume(handle, no_ack=False)
    try:
        await asyncio.Future()
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(run())
