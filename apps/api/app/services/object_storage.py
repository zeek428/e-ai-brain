from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from app.core.config import get_settings


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    object_key: str
    size_bytes: int


class ObjectStorage:
    provider = "local"

    def put_bytes(
        self,
        *,
        bucket: str,
        object_key: str,
        content: bytes,
        mime_type: str,
    ) -> StoredObject:
        raise NotImplementedError

    def get_bytes(self, *, bucket: str, object_key: str) -> bytes:
        raise NotImplementedError


class LocalObjectStorage(ObjectStorage):
    provider = "local"

    def __init__(self, root_dir: str) -> None:
        self.root_dir = Path(root_dir)

    def _path_for(self, bucket: str, object_key: str) -> Path:
        safe_parts = [part for part in object_key.split("/") if part not in {"", ".", ".."}]
        return self.root_dir.joinpath(bucket, *safe_parts)

    def put_bytes(
        self,
        *,
        bucket: str,
        object_key: str,
        content: bytes,
        mime_type: str,
    ) -> StoredObject:
        path = self._path_for(bucket, object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return StoredObject(bucket=bucket, object_key=object_key, size_bytes=len(content))

    def get_bytes(self, *, bucket: str, object_key: str) -> bytes:
        return self._path_for(bucket, object_key).read_bytes()


class MinioObjectStorage(ObjectStorage):
    provider = "minio"

    def __init__(
        self,
        *,
        access_key: str,
        endpoint: str,
        secret_key: str,
        secure: bool,
    ) -> None:
        try:
            from minio import Minio
        except ImportError as exc:  # pragma: no cover - depends on deployment extras
            raise RuntimeError(
                "minio package is required when OBJECT_STORAGE_PROVIDER=minio"
            ) from exc
        normalized_endpoint = endpoint.removeprefix("http://").removeprefix("https://")
        self.client = Minio(
            normalized_endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def _ensure_bucket(self, bucket: str) -> None:
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def put_bytes(
        self,
        *,
        bucket: str,
        object_key: str,
        content: bytes,
        mime_type: str,
    ) -> StoredObject:
        self._ensure_bucket(bucket)
        self.client.put_object(
            bucket,
            object_key,
            BytesIO(content),
            length=len(content),
            content_type=mime_type,
        )
        return StoredObject(bucket=bucket, object_key=object_key, size_bytes=len(content))

    def get_bytes(self, *, bucket: str, object_key: str) -> bytes:
        response = self.client.get_object(bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()


def object_storage() -> ObjectStorage:
    settings = get_settings()
    if settings.object_storage_provider == "minio":
        return MinioObjectStorage(
            access_key=settings.object_storage_access_key,
            endpoint=settings.object_storage_endpoint,
            secret_key=settings.object_storage_secret_key,
            secure=settings.object_storage_secure,
        )
    return LocalObjectStorage(settings.object_storage_local_dir)
