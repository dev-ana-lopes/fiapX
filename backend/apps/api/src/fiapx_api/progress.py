from typing import Protocol
from uuid import UUID

from redis.asyncio import Redis

from .config import get_settings


class ProgressStore(Protocol):
    async def set_progress(self, video_id: UUID, progress: int, status: str) -> None: ...


class RedisProgressStore:
    def __init__(self, client: Redis | None = None) -> None:
        self.client = client or Redis.from_url(get_settings().redis_url, decode_responses=True)

    async def set_progress(self, video_id: UUID, progress: int, status: str) -> None:
        async with self.client.pipeline(transaction=True) as pipeline:
            await pipeline.set(f"video:{video_id}:progress", progress)
            await pipeline.set(f"video:{video_id}:status", status)
            await pipeline.execute()
