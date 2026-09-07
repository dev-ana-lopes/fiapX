from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    async def upload(
        self, object_key: str, file_path: Path, content_type: str | None = None
    ) -> None: ...
    async def download(self, object_key: str, destination: Path) -> Path: ...
    async def delete(self, object_key: str) -> None: ...
    async def exists(self, object_key: str) -> bool: ...
    async def presigned_get(self, object_key: str, expires_seconds: int) -> str: ...

    async def put(self, object_key: str, content: bytes) -> None: ...
    async def get(self, object_key: str, destination: Path) -> None: ...
    async def read(self, object_key: str) -> bytes: ...
    async def list(self, prefix: str = "") -> list[str]: ...


class InMemoryStorage:
    """Local adapter used by the foundation until the MinIO adapter is enabled."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, object_key: str, content: bytes) -> None:
        self.objects[object_key] = content

    async def upload(
        self, object_key: str, file_path: Path, content_type: str | None = None
    ) -> None:
        await self.put(object_key, file_path.read_bytes())

    async def get(self, object_key: str, destination: Path) -> None:
        destination.write_bytes(self.objects[object_key])

    async def read(self, object_key: str) -> bytes:
        return self.objects[object_key]

    async def download(self, object_key: str, destination: Path) -> Path:
        await self.get(object_key, destination)
        return destination

    async def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)

    async def exists(self, object_key: str) -> bool:
        return object_key in self.objects

    async def presigned_get(self, object_key: str, expires_seconds: int) -> str:
        return f"memory://{object_key}"

    async def list(self, prefix: str = "") -> list[str]:
        return sorted(key for key in self.objects if key.startswith(prefix))
