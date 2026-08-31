"""Armazenamento de anexos fiscais. Nada é gravado sem chave, MIME e tamanho válidos."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.modules.fiscal_inbound.constants import (
    ALLOWED_MIME_TYPES,
    MAX_ATTACHMENT_BYTES,
    MIME_TO_KIND,
)
from app.modules.production_planning.errors import ValidationError

_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class StoredObject:
    key: str
    content_type: str
    byte_size: int
    sha256: str
    kind: str


class FiscalObjectStore(Protocol):
    def put(self, key: str, payload: bytes, *, content_type: str) -> StoredObject: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...


def sha256_of(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def assert_safe_key(key: str) -> str:
    if not key or key != key.strip():
        raise ValidationError("chave_anexo_invalida")
    if "\\" in key or key.startswith("/") or ".." in key:
        raise ValidationError("chave_anexo_invalida")
    segments = key.split("/")
    if any(not _SEGMENT.match(segment) for segment in segments):
        raise ValidationError("chave_anexo_invalida")
    return key


def assert_allowed_mime(content_type: str) -> str:
    normalized = (content_type or "").split(";")[0].strip().lower()
    if normalized not in ALLOWED_MIME_TYPES:
        raise ValidationError("anexo_tipo_nao_suportado")
    return normalized


def assert_size(payload: bytes) -> int:
    size = len(payload)
    if size <= 0:
        raise ValidationError("anexo_vazio")
    if size > MAX_ATTACHMENT_BYTES:
        raise ValidationError("anexo_excede_limite")
    return size


def kind_for(content_type: str) -> str:
    return MIME_TO_KIND[assert_allowed_mime(content_type)]


def build_key(organization_id: UUID, document_id: UUID, digest: str, content_type: str) -> str:
    suffix = {
        "application/xml": "xml",
        "text/xml": "xml",
        "application/pdf": "pdf",
        "image/jpeg": "jpg",
        "image/png": "png",
    }[assert_allowed_mime(content_type)]
    return assert_safe_key(f"fiscal/{organization_id}/{document_id}/{digest}.{suffix}")


class MemoryFiscalObjectStore:
    """Implementação em memória usada em desenvolvimento, demo e testes."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put(self, key: str, payload: bytes, *, content_type: str) -> StoredObject:
        safe = assert_safe_key(key)
        mime = assert_allowed_mime(content_type)
        size = assert_size(payload)
        digest = sha256_of(payload)
        self._objects[safe] = payload
        return StoredObject(
            key=safe,
            content_type=mime,
            byte_size=size,
            sha256=digest,
            kind=MIME_TO_KIND[mime],
        )

    def get(self, key: str) -> bytes:
        safe = assert_safe_key(key)
        if safe not in self._objects:
            raise ValidationError("recurso_nao_encontrado")
        return self._objects[safe]

    def exists(self, key: str) -> bool:
        return assert_safe_key(key) in self._objects


_DEFAULT_STORE = MemoryFiscalObjectStore()


def default_object_store() -> FiscalObjectStore:
    return _DEFAULT_STORE
