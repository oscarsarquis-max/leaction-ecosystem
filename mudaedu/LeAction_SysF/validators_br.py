# -*- coding: utf-8 -*-
"""Validadores de documentos/contato brasileiros (cadastro / lead)."""
from __future__ import annotations

import re
from typing import Optional


def only_digits(value: Optional[str]) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def is_valid_email(value: Optional[str]) -> bool:
    email = (value or "").strip()
    if not email or len(email) > 254:
        return False
    # RFC-lite: local@domínio.tld
    return bool(
        re.match(
            r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$",
            email,
        )
    )


def is_valid_br_phone(value: Optional[str], *, required: bool = False) -> bool:
    digits = only_digits(value)
    if not digits:
        return not required
    # DDD (2) + fixo (8) ou celular (9)
    if len(digits) not in (10, 11):
        return False
    ddd = int(digits[:2])
    if ddd < 11 or ddd > 99:
        return False
    if len(digits) == 11 and digits[2] != "9":
        return False
    return True


def is_valid_cep(value: Optional[str], *, required: bool = False) -> bool:
    digits = only_digits(value)
    if not digits:
        return not required
    return len(digits) == 8


def is_valid_cnpj(value: Optional[str], *, required: bool = False) -> bool:
    digits = only_digits(value)
    if not digits:
        return not required
    if len(digits) != 14:
        return False
    if digits == digits[0] * 14:
        return False

    def _check(base: str, weights: list[int]) -> str:
        total = sum(int(d) * w for d, w in zip(base, weights))
        rest = total % 11
        return "0" if rest < 2 else str(11 - rest)

    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = _check(digits[:12], w1)
    d2 = _check(digits[:12] + d1, w2)
    return digits.endswith(d1 + d2)


def format_cnpj(value: Optional[str]) -> str:
    d = only_digits(value)
    if len(d) != 14:
        return (value or "").strip()
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def format_cep(value: Optional[str]) -> str:
    d = only_digits(value)
    if len(d) != 8:
        return (value or "").strip()
    return f"{d[:5]}-{d[5:]}"


def format_br_phone(value: Optional[str]) -> str:
    d = only_digits(value)
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return (value or "").strip()


def validate_lead_signup(payload: dict, *, is_solo: bool) -> list[str]:
    """Retorna lista de mensagens de erro (vazia = ok)."""
    errors: list[str] = []

    email = (payload.get("mail_clie") or "").strip()
    if not email:
        errors.append("Informe o e-mail.")
    elif not is_valid_email(email):
        errors.append("E-mail inválido. Use o formato nome@dominio.com")

    phone = payload.get("fone_clie")
    if not is_valid_br_phone(phone, required=True):
        errors.append("Telefone inválido. Use DDD + número (10 ou 11 dígitos). Ex: (85) 99180-0606")

    if not is_solo:
        cnpj = payload.get("docu_clie")
        if not is_valid_cnpj(cnpj, required=True):
            errors.append("CNPJ inválido. Verifique os 14 dígitos e os dígitos verificadores.")
        cep = payload.get("zipn_clie")
        if not is_valid_cep(cep, required=True):
            errors.append("CEP inválido. Informe 8 dígitos. Ex: 60135-410")

    return errors
