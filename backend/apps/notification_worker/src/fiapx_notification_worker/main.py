import asyncio
import json
import logging
import os

from aio_pika import connect_robust
from aio_pika.abc import AbstractIncomingMessage
from fiapx_api.config import get_settings
from fiapx_api.db import session_factory
from fiapx_api.messaging import EXCHANGE
from fiapx_api.models import Notification, Video
from fiapx_shared import VideoEvent
from prometheus_client import Counter, start_http_server
from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import insert

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)
QUEUE = "video.notification"
notifications_recorded = Counter(
    "fiapx_notifications_recorded_total", "Notifications persisted by the worker"
)


def notification_content(event: VideoEvent, filename: str) -> tuple[str, str, str]:
    """Return the persisted type, title and message for a processing event."""
    if event.status.value == "FAILED":
        return (
            "VIDEO_FAILED",
            f'Falha ao processar o vídeo "{filename}".',
            event.error_message or "Não foi possível processar este vídeo.",
        )
    return (
        "VIDEO_COMPLETED",
        f'Seu vídeo "{filename}" foi concluído com sucesso.',
        "Agora você já pode baixar o arquivo ZIP com as imagens.",
    )


async def handle(message: AbstractIncomingMessage) -> None:
    try:
        body = json.loads(message.body)
    except json.JSONDecodeError:
        logger.exception("notification.invalid_message")
        await message.reject(requeue=False)
        return
    try:
        event = VideoEvent.model_validate(body)
    except ValidationError:
        logger.exception("notification.invalid_message")
        await message.reject(requeue=False)
        return
    if event.user_id is None:
        logger.error("notification event has no user_id", extra={"event_id": str(event.event_id)})
        await message.reject(requeue=False)
        return
    async with message.process(requeue=True):
        async with session_factory() as session:
            video = await session.get(Video, event.video_id)
            filename = video.original_filename if video else str(event.video_id)
            notification_type, title, notification_message = notification_content(event, filename)
            await session.execute(
                insert(Notification)
                .values(
                    event_id=event.event_id,
                    user_id=event.user_id,
                    video_id=event.video_id,
                    type=notification_type,
                    status="PENDING",
                    title=title,
                    message=notification_message,
                )
                .on_conflict_do_nothing(index_elements=[Notification.event_id])
            )
            await session.commit()
            notifications_recorded.inc()
        logger.info(
            "notification recorded",
            extra={
                "event_id": str(event.event_id),
                "job_id": str(event.job_id),
                "video_id": str(event.video_id),
                "status": event.status,
                "correlation_id": event.correlation_id,
            },
        )


async def run() -> None:
    start_http_server(int(os.getenv("METRICS_PORT", "8002")), addr="0.0.0.0")
    connection = await connect_robust(get_settings().rabbitmq_url)
    channel = await connection.channel()
    exchange = await channel.declare_exchange(EXCHANGE, "topic", durable=True)
    queue = await channel.declare_queue(QUEUE, durable=True)
    for key in ("video.processing.completed", "video.processing.failed"):
        await queue.bind(exchange, routing_key=key)
    await queue.consume(handle, no_ack=False)
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(run())
