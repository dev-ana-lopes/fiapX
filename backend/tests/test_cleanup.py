from unittest.mock import AsyncMock

import pytest
from fiapx_api.cleanup import delete_orphaned_objects, find_orphaned_objects


class FakeResult:
    def all(self) -> list[tuple[str, str | None]]:
        return [("users/u/videos/v/original/a.mp4", "users/u/videos/v/result/frames.zip")]


class FakeSession:
    async def execute(self, _query: object) -> FakeResult:
        return FakeResult()


class FakeStorage:
    async def list(self, _prefix: str = "") -> list[str]:
        return [
            "users/u/videos/v/original/a.mp4",
            "users/u/videos/v/result/frames.zip",
            "users/u/videos/deleted/original/b.mp4",
        ]


@pytest.mark.asyncio
async def test_cleanup_detects_only_unreferenced_objects() -> None:
    assert await find_orphaned_objects(FakeStorage(), FakeSession()) == [
        "users/u/videos/deleted/original/b.mp4"
    ]


@pytest.mark.asyncio
async def test_cleanup_deletes_only_reviewed_objects() -> None:
    storage = AsyncMock()
    assert await delete_orphaned_objects(storage, ["orphan-a", "orphan-b"]) == 2
    assert storage.delete.await_count == 2
