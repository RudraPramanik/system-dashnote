from pathlib import Path
from typing import Protocol

import aioboto3
import boto3
from fastapi import HTTPException, status

from config import settings


class StorageBackend(Protocol):
    async def upload(self, key: str, data: bytes, mime_type: str) -> str: ...

    async def download(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...

    def presigned_url(self, key: str, expires_seconds: int = 3600) -> str | None: ...


class LocalStorageBackend:
    def __init__(self, base_path: str) -> None:
        self.base_path = Path(base_path)

    async def upload(self, key: str, data: bytes, mime_type: str) -> str:
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        return key

    async def download(self, key: str) -> bytes:
        file_path = self.base_path / key
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found.",
            )
        return file_path.read_bytes()

    async def delete(self, key: str) -> None:
        file_path = self.base_path / key
        if file_path.exists():
            file_path.unlink()

    def presigned_url(self, key: str, expires_seconds: int = 3600) -> str | None:
        return None


class _S3CompatibleStorageBackend:
    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        use_ssl: bool = True,
    ) -> None:
        self.bucket = bucket
        self._client_kwargs = {
            "service_name": "s3",
            "endpoint_url": endpoint_url,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "use_ssl": use_ssl,
        }
        self._aio_session = aioboto3.Session()
        self._sync_session = boto3.session.Session()

    async def upload(self, key: str, data: bytes, mime_type: str) -> str:
        async with self._aio_session.client(**self._client_kwargs) as client:
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=mime_type,
            )
        return key

    async def download(self, key: str) -> bytes:
        async with self._aio_session.client(**self._client_kwargs) as client:
            try:
                response = await client.get_object(Bucket=self.bucket, Key=key)
            except client.exceptions.NoSuchKey as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found.",
                ) from exc
            return await response["Body"].read()

    async def delete(self, key: str) -> None:
        async with self._aio_session.client(**self._client_kwargs) as client:
            await client.delete_object(Bucket=self.bucket, Key=key)

    def presigned_url(self, key: str, expires_seconds: int = 3600) -> str | None:
        client = self._sync_session.client(**self._client_kwargs)
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )


class MinIOStorageBackend(_S3CompatibleStorageBackend):
    def __init__(self) -> None:
        super().__init__(
            endpoint_url=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            bucket=settings.MINIO_BUCKET,
            use_ssl=settings.MINIO_USE_SSL,
        )


class R2StorageBackend(_S3CompatibleStorageBackend):
    def __init__(self) -> None:
        super().__init__(
            endpoint_url=settings.R2_ENDPOINT,
            access_key=settings.R2_ACCESS_KEY_ID,
            secret_key=settings.R2_SECRET_ACCESS_KEY,
            bucket=settings.R2_BUCKET,
            use_ssl=True,
        )


def get_storage() -> StorageBackend:
    backend = settings.STORAGE_BACKEND.lower()
    if backend == "local":
        return LocalStorageBackend(settings.LOCAL_STORAGE_PATH)
    if backend == "minio":
        return MinIOStorageBackend()
    if backend == "r2":
        return R2StorageBackend()
    raise ValueError(f"Unknown storage backend: {settings.STORAGE_BACKEND}")
