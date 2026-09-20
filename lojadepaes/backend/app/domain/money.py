from __future__ import annotations

import re
import unicodedata

from app.domain.errors import ProductError


def parse_brl_to_cents(raw: str | int | None) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, int):
        if raw <= 0:
            raise ProductError("preço deve ser maior que zero")
        return raw
    text = raw.strip()
    if not text:
        return None
    if not re.fullmatch(r"\d{1,3}(\.\d{3})*,\d{2}|\d+,\d{2}|\d+", text):
        raise ProductError("informe o preço como 24,90")
    if "," in text:
        whole, fraction = text.rsplit(",", 1)
        whole = whole.replace(".", "")
        cents = int(whole) * 100 + int(fraction)
    else:
        cents = int(text) * 100
    if cents <= 0:
        raise ProductError("preço deve ser maior que zero")
    return cents


def cents_to_brl(cents: int) -> str:
    whole, fraction = divmod(cents, 100)
    whole_txt = f"{whole:,}".replace(",", ".")
    return f"{whole_txt},{fraction:02d}"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug[:80]
