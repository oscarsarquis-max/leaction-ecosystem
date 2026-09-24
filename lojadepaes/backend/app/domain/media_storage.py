from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.config import Settings
from app.domain.errors import ProductError
from app.domain.paths import media_root


class MediaStorage(Protocol):
    backend_name: str

    def put(self, object_key: str, payload: bytes, content_type: str) -> None: ...

    def exists(self, object_key: str) -> bool: ...

    def open_bytes(self, object_key: str) -> bytes: ...

    def local_path(self, object_key: str) -> Path | None: ...


@dataclass(frozen=True)
class LocalMediaStorage:
    root: Path
    backend_name: str = "local"

    def put(self, object_key: str, payload: bytes, content_type: str) -> None:
        del content_type
        _assert_safe_key(object_key)
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / object_key
        target.write_bytes(payload)

    def exists(self, object_key: str) -> bool:
        _assert_safe_key(object_key)
        return (self.root / object_key).is_file()

    def open_bytes(self, object_key: str) -> bytes:
        path = self.local_path(object_key)
        if path is None:
            raise ProductError("arquivo de mídia ausente")
        return path.read_bytes()

    def local_path(self, object_key: str) -> Path | None:
        _assert_safe_key(object_key)
        path = self.root / object_key
        return path if path.is_file() else None


@dataclass(frozen=True)
class S3MediaStorage:
    bucket: str
    region: str
    prefix: str
    endpoint_url: str | None
    access_key_id: str = ""
    secret_access_key: str = ""
    backend_name: str = "s3"

    def _client(self):
        try:
            import boto3
        except ImportError as exc:
            raise ProductError(
                "armazenamento S3 não disponível: instale a extra de produção do backend"
            ) from exc
        kwargs: dict[str, str] = {"region_name": self.region}
        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url
        if self.access_key_id.strip() and self.secret_access_key.strip():
            kwargs["aws_access_key_id"] = self.access_key_id.strip()
            kwargs["aws_secret_access_key"] = self.secret_access_key.strip()
        return boto3.client("s3", **kwargs)

    def _key(self, object_key: str) -> str:
        _assert_safe_key(object_key)
        prefix = self.prefix.strip("/")
        return f"{prefix}/{object_key}" if prefix else object_key

    def put(self, object_key: str, payload: bytes, content_type: str) -> None:
        self._client().put_object(
            Bucket=self.bucket,
            Key=self._key(object_key),
            Body=payload,
            ContentType=content_type,
        )

    def exists(self, object_key: str) -> bool:
        try:
            self._client().head_object(Bucket=self.bucket, Key=self._key(object_key))
        except Exception:
            return False
        return True

    def open_bytes(self, object_key: str) -> bytes:
        try:
            response = self._client().get_object(Bucket=self.bucket, Key=self._key(object_key))
        except Exception as exc:
            raise ProductError("arquivo de mídia ausente") from exc
        return response["Body"].read()

    def local_path(self, object_key: str) -> Path | None:
        del object_key
        return None


def _assert_safe_key(object_key: str) -> None:
    if not object_key or "/" in object_key or "\\" in object_key or ".." in object_key:
        raise ProductError("referência de mídia inválida")


def media_storage(settings: Settings, backend_name: str | None = None) -> MediaStorage:
    chosen = (backend_name or settings.media_backend).strip().lower()
    if chosen == "local":
        return LocalMediaStorage(root=media_root(settings))
    if chosen == "s3":
        bucket = settings.media_s3_bucket.strip()
        region = settings.media_s3_region.strip()
        if not bucket or not region:
            raise ProductError(
                "armazenamento S3 exige bucket e região configurados no servidor"
            )
        endpoint = settings.media_s3_endpoint_url.strip() or None
        return S3MediaStorage(
            bucket=bucket,
            region=region,
            prefix=settings.media_s3_prefix.strip(),
            endpoint_url=endpoint,
            access_key_id=settings.aws_access_key_id,
            secret_access_key=settings.aws_secret_access_key,
        )
    raise ProductError("backend de mídia não suportado")
