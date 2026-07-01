"""File storage abstraction (local filesystem or S3)."""
from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LocalStorage:
    def __init__(self, base_dir: str | None = None) -> None:
        self.base = Path(base_dir or settings.STORAGE_DIR)
        self.base.mkdir(parents=True, exist_ok=True)

    async def save(self, data: bytes, *, filename: str, user_id: str) -> str:
        safe_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
        user_dir = self.base / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        path = user_dir / safe_name
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        logger.info("file_saved", path=str(path), size=len(data))
        return str(path)

    async def delete(self, path: str) -> None:
        p = Path(path)
        if p.exists():
            p.unlink()

    def local_path(self, path: str) -> str:
        return path


class S3Storage:
    def __init__(self) -> None:
        import boto3

        self.bucket = settings.S3_BUCKET
        self._client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        self._tmp = Path("/tmp/researchmate")
        self._tmp.mkdir(parents=True, exist_ok=True)

    async def save(self, data: bytes, *, filename: str, user_id: str) -> str:
        key = f"{user_id}/{uuid.uuid4().hex}_{Path(filename).name}"
        self._client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key

    async def delete(self, path: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=path)

    def local_path(self, path: str) -> str:
        """Download to a temp file so PyMuPDF can open it, return the local path."""
        local = self._tmp / Path(path).name
        self._client.download_file(self.bucket, path, str(local))
        return str(local)


def get_storage():
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage()
    return LocalStorage()
