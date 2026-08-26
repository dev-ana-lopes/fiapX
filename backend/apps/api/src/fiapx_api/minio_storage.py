import asyncio
import io
from datetime import timedelta
from pathlib import Path
from typing import Any

from minio import Minio

from fiapx_api.config import get_settings


class MinioStorage:
    """Async facade over MinIO's blocking SDK, isolated behind the storage boundary."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = Minio(
            settings.minio_endpoint,
            settings.minio_access_key,
            settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket

    async def _ensure_bucket(self) -> None:
        exists = await asyncio.to_thread(self.client.bucket_exists, self.bucket)
        if not exists:
            await asyncio.to_thread(self.client.make_bucket, self.bucket)

    async def put(self, object_key: str, content: bytes) -> None:
        await self._ensure_bucket()
        await asyncio.to_thread(
            self.client.put_object,
            self.bucket,
            object_key,
            io.BytesIO(content),
            len(content),
        )

    async def upload(
        self, object_key: str, file_path: Path, content_type: str | None = None
    ) -> None:
        await self._ensure_bucket()
        await asyncio.to_thread(
            self.client.fput_object,
            self.bucket,
            object_key,
            str(file_path),
            content_type=content_type,
        )

    async def get(self, object_key: str, destination: Path) -> None:
        response: Any = await asyncio.to_thread(self.client.get_object, self.bucket, object_key)
        try:
            destination.write_bytes(response.read())
        finally:
            response.close()
            response.release_conn()

    async def download(self, object_key: str, destination: Path) -> Path:
        await self.get(object_key, destination)
        return destination

    async def delete(self, object_key: str) -> None:
        await asyncio.to_thread(self.client.remove_object, self.bucket, object_key)

    async def exists(self, object_key: str) -> bool:
        try:
            await asyncio.to_thread(self.client.stat_object, self.bucket, object_key)
            return True
        except Exception:
            return False

    async def presigned_get(self, object_key: str, expires_seconds: int) -> str:
        await self._ensure_bucket()
        return await asyncio.to_thread(
            self.client.presigned_get_object,
            self.bucket,
            object_key,
            expires=timedelta(seconds=expires_seconds),
        )
