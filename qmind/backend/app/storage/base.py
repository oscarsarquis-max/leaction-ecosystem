from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class PresignedUpload:
    url: str
    method: str
    headers: dict[str, str]
    expires_in_seconds: int


@dataclass(frozen=True, slots=True)
class ObjectHead:
    exists: bool
    content_length: int | None = None
    content_type: str | None = None
    # Diagnostic only — NEVER use as content integrity hash.
    # S3 ETag is MD5 for single-part PUTs and a composite (not SHA-256) for multipart.
    etag: str | None = None


class ObjectStorage(Protocol):
    def generate_key(self, organization_id: str, evidence_id: str, version_no: int = 1) -> str: ...

    def generate_report_pdf_key(
        self, organization_id: str, report_id: str, version_no: int
    ) -> str: ...

    def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
    ) -> None: ...

    def presign_upload(
        self,
        key: str,
        *,
        content_type: str,
        max_bytes: int,
        expires_in: int,
    ) -> PresignedUpload: ...

    def presign_download(self, key: str, *, expires_in: int) -> str: ...

    def head(self, key: str) -> ObjectHead: ...

    def get_bytes(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


def get_storage(settings: Settings | None = None) -> ObjectStorage:
    settings = settings or get_settings()
    backend = settings.storage_backend
    if backend == "memory":
        from app.storage.memory import InMemoryObjectStorage

        return InMemoryObjectStorage.instance()
    if backend == "s3":
        from app.storage.s3 import S3ObjectStorage

        return S3ObjectStorage(settings)
    raise ValueError(f"Unknown STORAGE_BACKEND={backend}")
