import json
from typing import Any, Protocol

from aio_pika import DeliveryMode, ExchangeType, Message, connect_robust
from fiapx_shared import VideoProcessingMessage

from .config import get_settings

EXCHANGE = "fiapx.events"
PROCESSING_QUEUE = "video.processing"
RETRY_QUEUE = "video.processing.retry"
DLQ = "video.processing.dlq"
FAILED_ROUTING_KEY = "video.processing.failed"
RETRY_ROUTING_KEY = "video.processing.retry"


async def declare_video_topology(channel: Any) -> tuple[Any, Any]:
    """Declare the durable processing topology in one place for API and workers."""
    exchange = await channel.declare_exchange(EXCHANGE, ExchangeType.TOPIC, durable=True)
    dlq = await channel.declare_queue(DLQ, durable=True)
    await dlq.bind(exchange, routing_key=FAILED_ROUTING_KEY)
    retry = await channel.declare_queue(
        RETRY_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": EXCHANGE,
            "x-dead-letter-routing-key": "video.uploaded",
        },
    )
    await retry.bind(exchange, routing_key=RETRY_ROUTING_KEY)
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
            channel = await connection.channel(publisher_confirms=True)
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


async def publish_message(
    payload: VideoProcessingMessage, routing_key: str, expiration: int | None = None
) -> None:
    connection = await connect_robust(get_settings().rabbitmq_url)
    async with connection:
        channel = await connection.channel(publisher_confirms=True)
        exchange, _ = await declare_video_topology(channel)
        await publish_raw(
            channel,
            exchange,
            payload.model_dump_json().encode(),
            routing_key,
            str(payload.event_id),
            payload.correlation_id,
            expiration,
        )


async def publish_raw(
    channel: Any,
    exchange: Any,
    body: bytes,
    routing_key: str,
    message_id: str | None = None,
    correlation_id: str | None = None,
    expiration: int | None = None,
) -> None:
    await exchange.publish(
        Message(
            body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=message_id,
            correlation_id=correlation_id,
            expiration=expiration,
        ),
        routing_key=routing_key,
    )
