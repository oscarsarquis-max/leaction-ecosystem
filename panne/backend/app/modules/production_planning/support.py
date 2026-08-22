import hashlib
import json
from decimal import Decimal
from uuid import UUID

from app.modules.production_planning.errors import ValidationError


def reject_float(value: object, label: str) -> None:
    if isinstance(value, float):
        raise ValidationError(f"float rejeitado: {label}")


def as_decimal(value: Decimal | int | str, label: str) -> Decimal:
    reject_float(value, label)
    if isinstance(value, bool) or not isinstance(value, Decimal | int | str):
        raise ValidationError(f"{label} inválido")
    return Decimal(value)


def require_positive(value: Decimal, label: str) -> Decimal:
    if value <= 0:
        raise ValidationError(f"{label} deve ser positivo")
    return value


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"tipo não canônico: {type(value)!r}")
