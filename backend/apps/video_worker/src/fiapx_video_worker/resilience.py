import asyncio
import random
from dataclasses import dataclass
from uuid import UUID, uuid4

from fiapx_api.config import get_settings
from redis.asyncio import Redis


class RetryableError(Exception):
    """A dependency or resource may succeed on a later attempt."""


class PermanentError(Exception):
    """The input or operation cannot succeed by retrying."""


def should_retry(attempt: int, max_retries: int) -> bool:
    """Return whether another delivery may be scheduled after this attempt."""
    return attempt < max_retries


def retry_delay(attempt: int) -> int:
    settings = get_settings()
    base: int = min(
        int(settings.video_retry_max_delay_seconds),
        int(settings.video_retry_base_delay_seconds) * 2 ** max(0, attempt - 1),
    )
    jitter = int(settings.video_retry_jitter_seconds)
    return int(base + random.randint(0, max(0, jitter)))


RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end
"""
RENEW_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('expire', KEYS[1], ARGV[2])
else
  return 0
end
"""


@dataclass
class ProcessingLease:
    client: Redis
    key: str
    owner: str
    ttl: int
    _renew_task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> ProcessingLease:
        acquired = await self.client.set(self.key, self.owner, nx=True, ex=self.ttl)
        if not acquired:
            raise RetryableError("video is already being processed by another worker")
        self._renew_task = asyncio.create_task(self._renew_loop())
        return self

    async def _renew_loop(self) -> None:
        interval = max(1, get_settings().video_processing_lease_renew_seconds)
        try:
            while True:
                await asyncio.sleep(interval)
                await self.client.eval(RENEW_SCRIPT, 1, self.key, self.owner, self.ttl)
        except asyncio.CancelledError:
            return

    async def __aexit__(self, *_: object) -> None:
        if self._renew_task:
            self._renew_task.cancel()
            await self._renew_task
        await self.client.eval(RELEASE_SCRIPT, 1, self.key, self.owner)
        await self.client.aclose()


def lease_for(video_id: UUID, worker_id: str | None = None) -> ProcessingLease:
    settings = get_settings()
    return ProcessingLease(
        Redis.from_url(settings.redis_url, decode_responses=True),
        f"video:{video_id}:processing-lease",
        worker_id or str(uuid4()),
        settings.video_processing_lease_seconds,
    )
