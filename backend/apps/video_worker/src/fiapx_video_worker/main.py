import asyncio
import json
import logging
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from aio_pika import DeliveryMode, ExchangeType, IncomingMessage, Message, connect_robust
from fiapx_api.config import get_settings
from fiapx_api.db import session_factory
from fiapx_api.messaging import EXCHANGE, declare_video_topology
from fiapx_api.minio_storage import MinioStorage
from fiapx_api.models import ProcessingJob, Video
from fiapx_api.progress import RedisProgressStore
from fiapx_shared import VideoEvent, VideoProcessingMessage, VideoStatus

from fiapx_video_worker.processor import VideoProcessor, make_zip

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)
storage = MinioStorage()


async def progress(video_id, value: int, state: VideoStatus) -> None:
    store = RedisProgressStore()
    try:
        await store.set_progress(video_id, value, state.value)
    finally:
        await store.client.aclose()


async def publish_payload(payload: VideoProcessingMessage | VideoEvent, routing_key: str) -> None:
    connection = await connect_robust(get_settings().rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(EXCHANGE, ExchangeType.TOPIC, durable=True)
        await exchange.publish(
            Message(
                payload.model_dump_json().encode(),
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
            ),
            routing_key=routing_key,
        )


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
    )
    await publish_payload(event, event.event_type)


async def handle(message: IncomingMessage) -> None:
    payload = VideoProcessingMessage.model_validate(json.loads(message.body))
    async with message.process(requeue=False):
        async with session_factory() as session:
            video = await session.get(Video, payload.video_id)
            job = await session.get(ProcessingJob, payload.job_id) if payload.job_id else None
            if video is None or video.status == VideoStatus.COMPLETED:
                return
            now = datetime.now(UTC)
            video.status, video.progress, video.started_at, video.error_message = (
                VideoStatus.PROCESSING,
                5,
                now,
                None,
            )
            if job:
                job.status, job.started_at, job.attempt = (
                    VideoStatus.PROCESSING,
                    now,
                    payload.attempt,
                )
            await session.commit()
        await progress(payload.video_id, 5, VideoStatus.PROCESSING)
        try:
            with tempfile.TemporaryDirectory(prefix=f"fiapx-{payload.video_id}-") as directory:
                root = Path(directory)
                input_path = root / "input"
                frames = root / "frames"
                archive = root / "frames.zip"
                await storage.download(payload.object_key, input_path)
                await progress(payload.video_id, 20, VideoStatus.PROCESSING)
                result = await VideoProcessor().extract_frames(input_path, frames)
                await progress(payload.video_id, 70, VideoStatus.PROCESSING)
                make_zip(result.output_directory, archive)
                await progress(payload.video_id, 80, VideoStatus.PROCESSING)
                result_key = (
                    f"users/{payload.user_id}/videos/{payload.video_id}/result/frames.zip"
                    if payload.user_id
                    else f"videos/{payload.video_id}/result/frames.zip"
                )
                await storage.upload(result_key, archive, "application/zip")
                if not await storage.exists(result_key):
                    raise RuntimeError("result upload could not be verified")
            async with session_factory() as session:
                video = await session.get(Video, payload.video_id)
                job = await session.get(ProcessingJob, payload.job_id) if payload.job_id else None
                if video:
                    video.status, video.progress, video.finished_at, video.result_object_key = (
                        VideoStatus.COMPLETED,
                        100,
                        datetime.now(UTC),
                        result_key,
                    )
                if job:
                    job.status, job.finished_at = VideoStatus.COMPLETED, datetime.now(UTC)
                await session.commit()
            await progress(payload.video_id, 100, VideoStatus.COMPLETED)
            await publish_event(payload, VideoStatus.COMPLETED)
            logger.info(
                "video_processing_completed",
                extra={
                    "event_id": str(payload.event_id),
                    "video_id": str(payload.video_id),
                    "frame_count": result.frame_count,
                },
            )
        except Exception as error:
            if payload.attempt < get_settings().video_processing_max_retries:
                await publish_payload(
                    payload.model_copy(update={"attempt": payload.attempt + 1}), "video.uploaded"
                )
            else:
                async with session_factory() as session:
                    video = await session.get(Video, payload.video_id)
                    if video:
                        video.status, video.progress, video.finished_at, video.error_message = (
                            VideoStatus.FAILED,
                            0,
                            datetime.now(UTC),
                            "não foi possível processar o vídeo",
                        )
                        await session.commit()
                await progress(payload.video_id, 0, VideoStatus.FAILED)
                await publish_event(
                    payload, VideoStatus.FAILED, "não foi possível processar o vídeo"
                )
            logger.exception(
                "video_processing_error",
                extra={
                    "event_id": str(payload.event_id),
                    "video_id": str(payload.video_id),
                    "attempt": payload.attempt,
                    "exception_type": type(error).__name__,
                },
            )


async def run() -> None:
    connection = await connect_robust(get_settings().rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    exchange, queue = await declare_video_topology(channel)
    await queue.consume(handle, no_ack=False)
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(run())
