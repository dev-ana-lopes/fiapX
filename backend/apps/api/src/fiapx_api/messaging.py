import json
from typing import Any, Protocol

from aio_pika import DeliveryMode, ExchangeType, Message, connect_robust
from fiapx_shared import VideoProcessingMessage

from .config import get_settings

EXCHANGE = "fiapx.events"
PROCESSING_QUEUE = "video.processing"
DLQ = "video.processing.dlq"
FAILED_ROUTING_KEY = "video.processing.failed"


async def declare_video_topology(channel: Any) -> tuple[Any, Any]:
    """Declare the durable processing topology in one place for API and workers."""
    exchange = await channel.declare_exchange(EXCHANGE, ExchangeType.TOPIC, durable=True)
    dlq = await channel.declare_queue(DLQ, durable=True)
    await dlq.bind(exchange, routing_key=FAILED_ROUTING_KEY)
    queue = await channel.declare_queue(
        PROCESSING_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": EXCHANGE,
            "x-dead-letter-routing-key": FAILED_ROUTING_KEY,
        },
    )
    await queue.bind(exchange, routing_key="video.uploaded")
    return exchange, queue


class Publisher(Protocol):
    async def publish(self, payload: VideoProcessingMessage) -> None: ...


class RabbitPublisher:
    async def publish(self, payload: VideoProcessingMessage) -> None:
        connection = await connect_robust(get_settings().rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            exchange, _ = await declare_video_topology(channel)
            await exchange.publish(
                Message(
                    json.dumps(payload.model_dump(mode="json")).encode(),
                    content_type="application/json",
                    delivery_mode=DeliveryMode.PERSISTENT,
                    message_id=str(payload.event_id),
                ),
                routing_key="video.uploaded",
            )
