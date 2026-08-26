import json
from typing import Protocol

from aio_pika import DeliveryMode, ExchangeType, Message, connect_robust
from fiapx_shared.contracts import VideoProcessingMessage

from fiapx_api.config import get_settings

EXCHANGE = "fiapx.events"
PROCESSING_QUEUE = "video.processing"
DLQ = "video.processing.dlq"


class Publisher(Protocol):
    async def publish(self, payload: VideoProcessingMessage) -> None: ...


class RabbitPublisher:
    async def publish(self, payload: VideoProcessingMessage) -> None:
        connection = await connect_robust(get_settings().rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(EXCHANGE, ExchangeType.TOPIC, durable=True)
            queue = await channel.declare_queue(PROCESSING_QUEUE, durable=True)
            dlq = await channel.declare_queue(DLQ, durable=True)
            await queue.bind(exchange, routing_key="video.uploaded")
            await dlq.bind(exchange, routing_key="video.processing.failed")
            await exchange.publish(
                Message(
                    json.dumps(payload.model_dump(mode="json")).encode(),
                    content_type="application/json",
                    delivery_mode=DeliveryMode.PERSISTENT,
                    message_id=str(payload.event_id),
                ),
                routing_key="video.uploaded",
            )
