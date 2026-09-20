from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from app.core.config import Settings
from app.domain.errors import ProductError
from app.domain.paths import media_root

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_PIXELS = 40_000_000
MAX_EDGE = 8000


def sniff_content_type(header: bytes) -> str | None:
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return None


def store_image(settings: Settings, payload: bytes) -> tuple[str, str, int, int, int]:
    if len(payload) > settings.media_max_bytes:
        raise ProductError("a imagem excede o limite de 8 MB")
    if not payload:
        raise ProductError("arquivo de imagem vazio")
    content_type = sniff_content_type(payload[:16])
    if content_type is None:
        raise ProductError("envie JPEG, PNG ou WebP")
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.load()
            width, height = image.size
            detected = image.format
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ProductError("imagem inválida ou corrompida") from exc
    expected = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
    if expected.get(detected or "") != content_type:
        raise ProductError("o conteúdo da imagem não corresponde ao formato")
    if width < 1 or height < 1 or width > MAX_EDGE or height > MAX_EDGE:
        raise ProductError("dimensões da imagem fora do limite permitido")
    extension = ALLOWED_TYPES[content_type]
    stored_name = f"{uuid4().hex}{extension}"
    target = media_root(settings) / stored_name
    target.write_bytes(payload)
    return stored_name, content_type, len(payload), width, height


def media_file(settings: Settings, stored_name: str) -> Path:
    if "/" in stored_name or "\\" in stored_name or ".." in stored_name:
        raise ProductError("referência de mídia inválida")
    path = media_root(settings) / stored_name
    if not path.is_file():
        raise ProductError("arquivo de mídia ausente")
    return path
