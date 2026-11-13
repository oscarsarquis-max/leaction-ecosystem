"""Regras do marketplace. A técnica de comparação foi copiada; o módulo não importa a Loja."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from uuid import UUID

ALLOWED_CATEGORIES = frozenset(
    {
        "queijos",
        "frios",
        "vinhos",
        "cervejas",
        "azeites",
        "manteigas",
        "geleias",
        "cafe_cha",
        "pratos",
    }
)

# Lista copiada de offer_contract.py. Fica aqui para o módulo não importar aquele arquivo.
COPIED_FORBIDDEN = (
    "livro",
    "livros",
    "ebook",
    "poema",
    "poesia",
    "3drose",
    "poster",
    "pôster",
    "quadro",
    "adesivo",
    "gravata",
    "camisa",
    "camiseta",
    "chaveiro",
    "copa do mundo",
    "bola de",
    "porta azeite",
    "galheteiro",
    "dispenser",
)

BAKERY_MARKS = (
    "pao",
    "paes",
    "focaccia",
    "foccacia",
    "fermentacao natural",
    "massa",
    "confeitaria",
    "padaria",
    "croissant",
    "brioche",
    "baguete",
    "baguette",
)

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class MarketplaceError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        self.status = status
        self.detail = detail
        super().__init__(detail)


def _fold(value: object) -> str:
    text = " ".join(str(value or "").split()).casefold()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(char for char in nfkd if not unicodedata.combining(char))


def _has(hay: str, needles: tuple[str, ...]) -> bool:
    return any(_fold(item) in hay for item in needles)


def clean_category(value: str) -> str:
    shelf = (value or "").strip().casefold()
    if shelf not in ALLOWED_CATEGORIES:
        raise MarketplaceError(400, "categoria não permitida")
    return shelf


def refuse_bakery_text(name: str, description: str) -> None:
    hay = _fold(f"{name} {description}")
    if _has(hay, BAKERY_MARKS) or _has(hay, COPIED_FORBIDDEN):
        raise MarketplaceError(400, "nome ou descrição não podem indicar pão, massa ou item fora do contrato")


def clean_fee(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 100000:
        raise MarketplaceError(400, "a taxa por pedido precisa ser um valor de 0 a 100000 centavos")
    return value


def clean_slug(value: str) -> str:
    slug = (value or "").strip().casefold()
    if not slug or len(slug) > 80 or _SLUG.fullmatch(slug) is None:
        raise MarketplaceError(400, "o slug da marca só pode ter letras minúsculas, números e hífen")
    return slug


def clean_hex(value: str) -> str:
    color = (value or "").strip()
    if _HEX.fullmatch(color) is None:
        raise MarketplaceError(400, "a cor de destaque precisa ser um hex de seis dígitos")
    return color


def clean_required(value: str, label: str, limit: int) -> str:
    text = " ".join((value or "").split())
    if not text or len(text) > limit:
        raise MarketplaceError(400, f"{label} é obrigatório")
    return text


def clean_optional_text(value: str, label: str, limit: int) -> str:
    text = " ".join((value or "").split())
    if len(text) > limit:
        raise MarketplaceError(400, f"{label} passou do tamanho")
    return text


def clean_url(value: str, label: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if not (text.startswith("https://") or text.startswith("http://")) or len(text) > 500:
        raise MarketplaceError(400, f"{label} precisa ser um endereço http")
    return text


def clean_money(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MarketplaceError(400, f"{label} precisa ser um valor em centavos")
    return value


def clean_days(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 60:
        raise MarketplaceError(400, "o prazo de entrega precisa ser um número de dias")
    return value


def clean_names(values: object, label: str) -> list[str]:
    if not isinstance(values, list):
        raise MarketplaceError(400, f"{label} precisa ser uma lista")
    cleaned: list[str] = []
    for item in values:
        text = " ".join(str(item or "").split())
        if not text or len(text) > 80:
            raise MarketplaceError(400, f"{label} inválido")
        cleaned.append(text)
    if len(cleaned) > 40:
        raise MarketplaceError(400, f"{label} tem itens demais")
    return cleaned


def clean_ceps(values: object) -> list[str]:
    if not isinstance(values, list):
        raise MarketplaceError(400, "os prefixos de CEP precisam ser uma lista")
    cleaned: list[str] = []
    for item in values:
        digits = "".join(char for char in str(item or "") if char.isdigit())
        if not digits or len(digits) > 8:
            raise MarketplaceError(400, "prefixo de CEP inválido")
        cleaned.append(digits)
    if len(cleaned) > 40:
        raise MarketplaceError(400, "há prefixos de CEP demais")
    return cleaned


_MEDIA_PREFIX = "/api/v1/marketplace/media/"


def media_id_of(url: str) -> UUID | None:
    if not url.startswith(_MEDIA_PREFIX):
        return None
    try:
        return UUID(url[len(_MEDIA_PREFIX) :])
    except ValueError:
        return None


def clean_photos(values: object) -> list[str]:
    if not isinstance(values, list):
        raise MarketplaceError(400, "as fotos precisam ser uma lista de endereços")
    photos: list[str] = []
    for item in values:
        text = str(item or "").strip()
        if not text:
            continue
        if text.startswith(_MEDIA_PREFIX):
            media_id = media_id_of(text)
            if media_id is None:
                raise MarketplaceError(400, "a foto enviada não é válida")
            photos.append(f"{_MEDIA_PREFIX}{media_id}")
            continue
        cleaned = clean_url(text, "a foto")
        if cleaned:
            photos.append(cleaned)
    if len(photos) > 8:
        raise MarketplaceError(400, "são permitidas até 8 fotos")
    return photos


def delivery_complete(cities: list[str], districts: list[str], ceps: list[str], days: int | None, freight: int | None) -> bool:
    return bool(cities or districts or ceps) and days is not None and freight is not None


def periods_overlap(start_a: date, end_a: date | None, start_b: date, end_b: date | None) -> bool:
    end_a = end_a or date.max
    end_b = end_b or date.max
    return start_a <= end_b and start_b <= end_a


def clean_scores(quality: object, visual: object, complementarity: object) -> tuple[int, int, int]:
    scores: list[int] = []
    for value in (quality, visual, complementarity):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 5:
            raise MarketplaceError(400, "as três notas vão de 1 a 5")
        scores.append(value)
    return scores[0], scores[1], scores[2]


def clean_decision(decision: str, note: str) -> tuple[str, str | None]:
    choice = (decision or "").strip().casefold()
    if choice not in {"approve", "return", "reject"}:
        raise MarketplaceError(400, "a decisão precisa ser aprovar, devolver ou recusar")
    text = " ".join((note or "").split())
    if choice in {"return", "reject"} and not text:
        raise MarketplaceError(400, "devolução e recusa precisam da observação")
    if len(text) > 2000:
        raise MarketplaceError(400, "a observação passou do tamanho")
    return choice, text or None
