from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from config import settings
from core.storage.client import (
    LocalStorageBackend,
    MinIOStorageBackend,
    R2StorageBackend,
)


def _s3_client_mocks():
    mock_client = MagicMock()
    mock_client.put_object = AsyncMock()
    mock_body = MagicMock()
    mock_body.read = AsyncMock(return_value=b"s3-body")
    mock_client.get_object = AsyncMock(return_value={"Body": mock_body})
    mock_client.delete_object = AsyncMock()
    NoSuchKey = type("NoSuchKey", (Exception,), {})
    mock_client.exceptions = MagicMock()
    mock_client.exceptions.NoSuchKey = NoSuchKey

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    mock_aio_session = MagicMock()
    mock_aio_session.client = MagicMock(return_value=mock_cm)

    mock_sync_client = MagicMock()
    mock_sync_client.generate_presigned_url.return_value = "https://example.com/presigned"
    mock_sync_session = MagicMock()
    mock_sync_session.client.return_value = mock_sync_client

    return mock_client, mock_aio_session, mock_sync_session


@pytest.mark.asyncio
async def test_local_upload_writes_file():
    mock_joined = MagicMock()
    mock_parent = MagicMock()
    mock_joined.parent = mock_parent
    mock_joined.write_bytes = MagicMock()

    base_mock = MagicMock()
    base_mock.__truediv__ = MagicMock(return_value=mock_joined)

    with patch("core.storage.client.Path", return_value=base_mock):
        backend = LocalStorageBackend("/tmp/storage-root")
        await backend.upload("ws1/uuid/doc.pdf", b"payload", "application/pdf")

    mock_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_joined.write_bytes.assert_called_once_with(b"payload")


@pytest.mark.asyncio
async def test_local_download_reads_file():
    mock_joined = MagicMock()
    mock_joined.parent = MagicMock()
    mock_joined.exists.return_value = True
    mock_joined.read_bytes.return_value = b"file-bytes"

    base_mock = MagicMock()
    base_mock.__truediv__ = MagicMock(return_value=mock_joined)

    with patch("core.storage.client.Path", return_value=base_mock):
        backend = LocalStorageBackend("/tmp/storage-root")
        out = await backend.download("ws1/uuid/doc.pdf")

    assert out == b"file-bytes"


@pytest.mark.asyncio
async def test_local_download_missing_raises_404():
    mock_joined = MagicMock()
    mock_joined.exists.return_value = False

    base_mock = MagicMock()
    base_mock.__truediv__ = MagicMock(return_value=mock_joined)

    with patch("core.storage.client.Path", return_value=base_mock):
        backend = LocalStorageBackend("/tmp/storage-root")
        with pytest.raises(HTTPException) as exc_info:
            await backend.download("missing/key")
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_local_delete_unlinks():
    mock_joined = MagicMock()
    mock_joined.exists.return_value = True
    mock_joined.unlink = MagicMock()

    base_mock = MagicMock()
    base_mock.__truediv__ = MagicMock(return_value=mock_joined)

    with patch("core.storage.client.Path", return_value=base_mock):
        backend = LocalStorageBackend("/tmp/storage-root")
        await backend.delete("ws1/uuid/doc.pdf")

    mock_joined.unlink.assert_called_once()


def test_local_presigned_url_is_none():
    backend = LocalStorageBackend("/tmp/storage-root")
    assert backend.presigned_url("any-key") is None


@pytest.mark.asyncio
async def test_minio_upload_calls_put_object(monkeypatch):
    mock_client, mock_aio_session, mock_sync_session = _s3_client_mocks()
    monkeypatch.setattr(settings, "MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr(settings, "MINIO_ACCESS_KEY", "access")
    monkeypatch.setattr(settings, "MINIO_SECRET_KEY", "secret")
    monkeypatch.setattr(settings, "MINIO_BUCKET", "mybucket")
    monkeypatch.setattr(settings, "MINIO_USE_SSL", False)

    with patch("core.storage.client.aioboto3.Session", return_value=mock_aio_session):
        with patch("core.storage.client.boto3.session.Session", return_value=mock_sync_session):
            backend = MinIOStorageBackend()
            await backend.upload("object-key", b"bytes", "application/pdf")

    mock_client.put_object.assert_awaited_once()
    kwargs = mock_client.put_object.call_args.kwargs
    assert kwargs["Bucket"] == "mybucket"
    assert kwargs["Key"] == "object-key"
    assert kwargs["Body"] == b"bytes"


@pytest.mark.asyncio
async def test_minio_download_returns_bytes(monkeypatch):
    mock_client, mock_aio_session, mock_sync_session = _s3_client_mocks()
    monkeypatch.setattr(settings, "MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr(settings, "MINIO_ACCESS_KEY", "access")
    monkeypatch.setattr(settings, "MINIO_SECRET_KEY", "secret")
    monkeypatch.setattr(settings, "MINIO_BUCKET", "mybucket")
    monkeypatch.setattr(settings, "MINIO_USE_SSL", False)

    with patch("core.storage.client.aioboto3.Session", return_value=mock_aio_session):
        with patch("core.storage.client.boto3.session.Session", return_value=mock_sync_session):
            backend = MinIOStorageBackend()
            data = await backend.download("object-key")

    assert data == b"s3-body"


@pytest.mark.asyncio
async def test_minio_delete_calls_delete_object(monkeypatch):
    mock_client, mock_aio_session, mock_sync_session = _s3_client_mocks()
    monkeypatch.setattr(settings, "MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr(settings, "MINIO_ACCESS_KEY", "access")
    monkeypatch.setattr(settings, "MINIO_SECRET_KEY", "secret")
    monkeypatch.setattr(settings, "MINIO_BUCKET", "mybucket")
    monkeypatch.setattr(settings, "MINIO_USE_SSL", False)

    with patch("core.storage.client.aioboto3.Session", return_value=mock_aio_session):
        with patch("core.storage.client.boto3.session.Session", return_value=mock_sync_session):
            backend = MinIOStorageBackend()
            await backend.delete("object-key")

    mock_client.delete_object.assert_awaited_once()


def test_minio_presigned_url_returns_string(monkeypatch):
    _, mock_aio_session, mock_sync_session = _s3_client_mocks()
    monkeypatch.setattr(settings, "MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr(settings, "MINIO_ACCESS_KEY", "access")
    monkeypatch.setattr(settings, "MINIO_SECRET_KEY", "secret")
    monkeypatch.setattr(settings, "MINIO_BUCKET", "mybucket")
    monkeypatch.setattr(settings, "MINIO_USE_SSL", False)

    with patch("core.storage.client.aioboto3.Session", return_value=mock_aio_session):
        with patch("core.storage.client.boto3.session.Session", return_value=mock_sync_session):
            backend = MinIOStorageBackend()
            url = backend.presigned_url("object-key")

    assert url == "https://example.com/presigned"


@pytest.mark.asyncio
async def test_r2_upload_calls_put_object(monkeypatch):
    mock_client, mock_aio_session, mock_sync_session = _s3_client_mocks()
    monkeypatch.setattr(settings, "R2_ENDPOINT", "https://account.r2.cloudflarestorage.com")
    monkeypatch.setattr(settings, "R2_ACCESS_KEY_ID", "r2-key-id")
    monkeypatch.setattr(settings, "R2_SECRET_ACCESS_KEY", "r2-secret")
    monkeypatch.setattr(settings, "R2_BUCKET", "r2-bucket")

    with patch("core.storage.client.aioboto3.Session", return_value=mock_aio_session):
        with patch("core.storage.client.boto3.session.Session", return_value=mock_sync_session):
            backend = R2StorageBackend()
            await backend.upload("r2-key", b"data", "text/plain")

    mock_client.put_object.assert_awaited_once()
    assert mock_client.put_object.call_args.kwargs["Bucket"] == "r2-bucket"


@pytest.mark.asyncio
async def test_r2_download_returns_bytes(monkeypatch):
    mock_client, mock_aio_session, mock_sync_session = _s3_client_mocks()
    monkeypatch.setattr(settings, "R2_ENDPOINT", "https://account.r2.cloudflarestorage.com")
    monkeypatch.setattr(settings, "R2_ACCESS_KEY_ID", "r2-key-id")
    monkeypatch.setattr(settings, "R2_SECRET_ACCESS_KEY", "r2-secret")
    monkeypatch.setattr(settings, "R2_BUCKET", "r2-bucket")

    with patch("core.storage.client.aioboto3.Session", return_value=mock_aio_session):
        with patch("core.storage.client.boto3.session.Session", return_value=mock_sync_session):
            backend = R2StorageBackend()
            data = await backend.download("r2-key")

    assert data == b"s3-body"


@pytest.mark.asyncio
async def test_r2_delete_calls_delete_object(monkeypatch):
    mock_client, mock_aio_session, mock_sync_session = _s3_client_mocks()
    monkeypatch.setattr(settings, "R2_ENDPOINT", "https://account.r2.cloudflarestorage.com")
    monkeypatch.setattr(settings, "R2_ACCESS_KEY_ID", "r2-key-id")
    monkeypatch.setattr(settings, "R2_SECRET_ACCESS_KEY", "r2-secret")
    monkeypatch.setattr(settings, "R2_BUCKET", "r2-bucket")

    with patch("core.storage.client.aioboto3.Session", return_value=mock_aio_session):
        with patch("core.storage.client.boto3.session.Session", return_value=mock_sync_session):
            backend = R2StorageBackend()
            await backend.delete("r2-key")

    mock_client.delete_object.assert_awaited_once()


def test_r2_presigned_url_returns_string(monkeypatch):
    _, mock_aio_session, mock_sync_session = _s3_client_mocks()
    monkeypatch.setattr(settings, "R2_ENDPOINT", "https://account.r2.cloudflarestorage.com")
    monkeypatch.setattr(settings, "R2_ACCESS_KEY_ID", "r2-key-id")
    monkeypatch.setattr(settings, "R2_SECRET_ACCESS_KEY", "r2-secret")
    monkeypatch.setattr(settings, "R2_BUCKET", "r2-bucket")

    with patch("core.storage.client.aioboto3.Session", return_value=mock_aio_session):
        with patch("core.storage.client.boto3.session.Session", return_value=mock_sync_session):
            backend = R2StorageBackend()
            url = backend.presigned_url("r2-key")

    assert url == "https://example.com/presigned"
