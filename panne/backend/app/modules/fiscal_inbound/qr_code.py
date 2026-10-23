"""Leitura do QR Code da NFC-e.

A URL identifica a consulta. Ela não traz os itens e esta leitura não grava nota,
anexo, ingrediente, lote, movimento ou custo. Não há chamada de rede: a consulta
pública das UFs não foi comprovada como fonte automática e barreiras da Fazenda
não são contornadas.

Formatos reconhecidos a partir do Manual do DANFE NFC-e / QR Code (versão 2 e
versão 3, NT 2025.001): parâmetro `p` com chave, versão e ambiente. A tabela
nacional de URL por UF (Portal NFC-e / ENCAT) não foi obtida nesta entrega, então
o domínio aceito é HTTPS em host público `.gov.br` de Fazenda/SEFAZ/NFC-e/SVRS/SEFIN.
Isso não é cobertura comprovada de cada UF.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

from app.modules.identity_organization.authorization import (
    PERMISSION_FISCAL_DOCUMENT_CAPTURE,
    Principal,
    require_permission,
)

_KEY_RE = re.compile(r"^\d{44}$")
_HOST_MARK = ("sefaz", "fazenda", "nfce", "svrs", "sefin")
_CUF = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
    "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}
IMPORT_UNAVAILABLE = "Consulta disponível; importação automática indisponível nesta origem."


def access_key_valid(key: str) -> bool:
    if not _KEY_RE.fullmatch(key):
        return False
    total = 0
    weight = 2
    for char in reversed(key[:43]):
        total += int(char) * weight
        weight = 2 if weight == 9 else weight + 1
    mod = total % 11
    expected = "0" if mod < 2 else str(11 - mod)
    return key[43] == expected


def _rejected(reason: str) -> dict:
    return {
        "recognized": False,
        "import_available": False,
        "items": [],
        "reason": reason,
        "consultation_url": None,
    }


def _host_allowed(host: str) -> bool:
    name = host.lower().rstrip(".")
    if not name or name in {"localhost", "localhost.localdomain"} or name.endswith(".local"):
        return False
    try:
        ipaddress.ip_address(name)
        return False
    except ValueError:
        pass
    if not name.endswith(".gov.br"):
        return False
    return any(mark in name for mark in _HOST_MARK)


def read_nfce_qr(principal: Principal, raw_url: str) -> dict:
    """Decodifica a URL. Não consulta a rede e não persiste."""
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_CAPTURE)
    text = (raw_url or "").strip()
    if not text or len(text) > 2000:
        return _rejected("codigo_invalido")
    parts = urlsplit(text)
    if parts.scheme != "https" or parts.username or parts.password:
        return _rejected("endereco_nao_permitido")
    if parts.port not in {None, 443}:
        return _rejected("endereco_nao_permitido")
    if not _host_allowed(parts.hostname or ""):
        return _rejected("origem_nao_reconhecida")
    query = parts.query
    if not query.startswith("p=") or "&" in query:
        return _rejected("codigo_invalido")
    payload = query[2:]
    fields = payload.split("|")
    if len(fields) < 3:
        return _rejected("codigo_invalido")
    key = "".join(ch for ch in fields[0] if ch.isdigit())
    if not access_key_valid(key):
        return _rejected("chave_invalida")
    version = fields[1]
    environment = fields[2]
    if version not in {"2", "3"} or environment not in {"1", "2"}:
        return _rejected("codigo_invalido")
    model = key[20:22]
    cuf = key[0:2]
    if model != "65":
        return {
            **_rejected("modelo_nao_e_nfce"),
            "model": model,
            "uf": _CUF.get(cuf),
            "access_key": key,
        }
    online = (version == "2" and len(fields) == 5) or (version == "3" and len(fields) == 3)
    return {
        "recognized": True,
        "import_available": False,
        "items": [],
        "model": "65",
        "model_label": "NFC-e",
        "uf": _CUF.get(cuf),
        "cuf": cuf,
        "environment": "producao" if environment == "1" else "homologacao",
        "qr_version": version,
        "emission": "online" if online else "contingencia",
        "access_key": key,
        "series": str(int(key[22:25])),
        "number": str(int(key[25:34])),
        "signature_checked": False,
        "message": IMPORT_UNAVAILABLE,
        "consultation_url": text,
    }
