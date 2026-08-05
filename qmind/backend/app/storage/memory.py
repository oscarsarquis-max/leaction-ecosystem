"""In-memory object storage for unit/API tests (not for production)."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from urllib.parse import quote

from app.storage.base import ObjectHead, PresignedUpload


@dataclass
class _Obj:
    data: bytes
    content_type: str
    committed: bool = False


class InMemoryObjectStorage:
    _lock = threading.Lock()
    _singleton: InMemoryObjectStorage | None = None

    def __init__(self) -> None:
        self._objects: dict[str, _Obj] = {}

    @classmethod
    def instance(cls) -> InMemoryObjectStorage:
        with cls._lock:
            if cls._singleton is None:
                cls._singleton = cls()
            return cls._singleton

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._singleton = cls()

    def generate_key(self, organization_id: str, evidence_id: str, version_no: int = 1) -> str:
        return f"org/{organization_id}/evidence/{evidence_id}/v{version_no}"

    def generate_report_pdf_key(
        self, organization_id: str, report_id: str, version_no: int
    ) -> str:
        return f"org/{organization_id}/reports/{report_id}/v{version_no}.pdf"

    def put_bytes(self, key: str, data: bytes, *, content_type: str) -> None:
        self._objects[key] = _Obj(data=data, content_type=content_type, committed=True)

    def put_test_object(self, key: str, data: bytes, content_type: str) -> None:
        self.put_bytes(key, data, content_type=content_type)

    def presign_upload(
        self,
        key: str,
        *,
        content_type: str,
        max_bytes: int,
        expires_in: int,
    ) -> PresignedUpload:
        self._objects.setdefault(
            key, _Obj(data=b"", content_type=content_type, committed=False)
        )
        return PresignedUpload(
            url=f"memory://upload/{quote(key, safe='/')}?max={max_bytes}",
            method="PUT",
            headers={"Content-Type": content_type},
            expires_in_seconds=expires_in,
        )

    def presign_download(self, key: str, *, expires_in: int) -> str:
        return f"memory://download/{quote(key, safe='/')}?exp={expires_in}"

    def head(self, key: str) -> ObjectHead:
        obj = self._objects.get(key)
        if obj is None or not obj.committed:
            return ObjectHead(exists=False)
        return ObjectHead(
            exists=True,
            content_length=len(obj.data),
            content_type=obj.content_type,
            etag=f'"{len(obj.data):x}"',
        )

    def get_bytes(self, key: str) -> bytes:
        obj = self._objects.get(key)
        if obj is None or not obj.committed:
            raise FileNotFoundError(key)
        return obj.data

    def delete(self, key: str) -> None:
        self._objects.pop(key, None)
