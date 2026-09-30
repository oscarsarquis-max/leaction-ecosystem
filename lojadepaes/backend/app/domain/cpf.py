from __future__ import annotations

import hashlib
import hmac
import re

from app.core.config import Settings
from app.domain.errors import ConfirmationError

_DIGITS = re.compile(r"\D+")


def only_cpf_digits(value: str) -> str:
    return _DIGITS.sub("", value or "")[:11]


def is_valid_cpf(value: str) -> bool:
    digits = only_cpf_digits(value)
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    numbers = [int(item) for item in digits]

    def check(limit: int) -> bool:
        total = sum(numbers[index] * (limit + 1 - index) for index in range(limit))
        rest = (total * 10) % 11
        return (0 if rest == 10 else rest) == numbers[limit]

    return check(9) and check(10)


def require_cpf(value: str) -> str:
    digits = only_cpf_digits(value)
    if not is_valid_cpf(digits):
        raise ConfirmationError("informe um CPF válido")
    return digits


def identity_secret(settings: Settings) -> str:
    raw = (settings.customer_identity_secret or settings.admin_session_secret or "").strip()
    if len(raw) < 32:
        raise ConfirmationError("cadastro temporariamente indisponível")
    return raw


def cpf_hmac(settings: Settings, digits: str) -> str:
    return hmac.new(
        identity_secret(settings).encode("utf-8"),
        f"cpf:{digits}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def mask_cpf(last2: str) -> str:
    tail = (last2 or "")[-2:].zfill(2)
    return f"***.***.***-{tail}"
