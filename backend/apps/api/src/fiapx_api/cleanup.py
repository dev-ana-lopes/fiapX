from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Video
from .storage import Storage


async def find_orphaned_objects(
    storage: Storage, session: AsyncSession, prefix: str = ""
) -> list[str]:
    """List storage objects not referenced by any video; this operation never deletes."""
    result = await session.execute(select(Video.object_key, Video.result_object_key))
    referenced = {key for row in result.all() for key in row if key is not None}
    return [key for key in await storage.list(prefix) if key not in referenced]


async def delete_orphaned_objects(storage: Storage, orphaned: Iterable[str]) -> int:
    """Delete only a previously reviewed orphan list and return the count removed."""
    deleted = 0
    for object_key in orphaned:
        await storage.delete(object_key)
        deleted += 1
    return deleted
