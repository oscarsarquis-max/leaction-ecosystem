"""CNPJ numérico e alfanumérico (formato da Receita a partir de julho de 2026).

Os 12 primeiros caracteres (raiz + ordem) podem ser dígitos ou letras maiúsculas; os 2 últimos
(dígitos verificadores) são sempre dígitos. Cada caractere vale `código ASCII - 48`
(0-9 valem 0-9; A vale 17, B vale 18, ...), e o cálculo é o módulo 11 de sempre.

Guarda-se sem máscara e em maiúsculas (14 caracteres); na tela aparece formatado.
"""

from __future__ import annotations

import re

_PESOS_1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_PESOS_2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_SEM_MASCARA = re.compile(r"^[0-9A-Z]{12}[0-9]{2}$")
_MASCARA = re.compile(r"[.\-/\s]")


class CnpjInvalido(ValueError):
    pass


def limpar(valor: str) -> str:
    return _MASCARA.sub("", valor or "").upper()


def _digito(caracteres: str, pesos: tuple[int, ...]) -> int:
    soma = sum((ord(c) - 48) * p for c, p in zip(caracteres, pesos, strict=True))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def digitos_verificadores(base12: str) -> str:
    d1 = _digito(base12, _PESOS_1)
    d2 = _digito(base12 + str(d1), _PESOS_2)
    return f"{d1}{d2}"


def validar(valor: str) -> bool:
    cnpj = limpar(valor)
    if not _SEM_MASCARA.match(cnpj):
        return False
    if len(set(cnpj)) == 1:  # 00000000000000, 11111111111111...
        return False
    return digitos_verificadores(cnpj[:12]) == cnpj[12:]


def normalizar(valor: str) -> str:
    """Devolve o CNPJ sem máscara, em maiúsculas, ou levanta `CnpjInvalido`."""
    cnpj = limpar(valor)
    if not validar(cnpj):
        raise CnpjInvalido("CNPJ inválido: confira os caracteres e os dois dígitos finais")
    return cnpj


def formatar(cnpj: str) -> str:
    c = limpar(cnpj)
    if len(c) != 14:
        return cnpj
    return f"{c[0:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:14]}"
