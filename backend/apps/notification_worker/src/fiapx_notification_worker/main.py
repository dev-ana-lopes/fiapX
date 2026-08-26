import asyncio
import json
import logging

from aio_pika import IncomingMessage, connect_robust
from fiapx_api.config import get_settings
from fiapx_api.messaging import EXCHANGE
from fiapx_shared.contracts import VideoEvent

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)
QUEUE = "video.notification"


async def handle(message: IncomingMessage) -> None:
    async with message.process(requeue=False):
        event = VideoEvent.model_validate(json.loads(message.body))
        logger.info(
            "notification recorded",
            extra={
                "job_id": str(event.job_id),
                "video_id": str(event.video_id),
                "status": event.status,
            },
        )


async def run() -> None:
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
