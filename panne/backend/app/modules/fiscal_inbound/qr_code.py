"""Leitura da chave a partir do QR da NFC-e.

Isto não é importação. A URL oficial abre uma página para a pessoa. O XML dos
itens sai pelo webservice de download, que exige certificado digital e-CNPJ.
Não há chamada de rede, raspagem, CAPTCHA nem uso de certificado.

Os hosts vêm da tabela «URL por UF» publicada em
https://nfce.encat.org/desenvolvedor/qrcode/ e lida em 23/10/2026. A busca
direta dessa página não conectou; a lista abaixo é o conteúdo então obtido.
Host ausente ou ambíguo nessa leitura fica de fora. SVRS não constava nela.

Formatos: Manual do DANFE NFC-e / QR Code e NT 2025.001. Parâmetro `p`.
Versão 2 online tem 5 campos; versão 3 online tem 3. Campo a mais é
contingência. A assinatura e o hash do CSC não são conferidos.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.fiscal_inbound.models import FiscalInboundDocument
from app.modules.identity_organization.authorization import (
    PERMISSION_FISCAL_DOCUMENT_CAPTURE,
    Principal,
    require_permission,
)
from app.modules.inventory_procurement.services import _org

_KEY_RE = re.compile(r"^\d{44}$")
_CUF = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
    "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}
# Hosts literais da tabela ENCAT lida em 23/10/2026. Sem completar linha cortada.
_OFFICIAL_HOSTS = frozenset({
    "www.sefaznet.ac.gov.br",
    "www.hml.sefaznet.ac.gov.br",
    "nfce.sefaz.al.gov.br",
    "www.sefaz.ap.gov.br",
    "sistemas.sefaz.am.gov.br",
    "homnfce.sefaz.am.gov.br",
    "nfe.sefaz.ba.gov.br",
    "hnfe.sefaz.ba.gov.br",
    "nfce.sefaz.ce.gov.br",
    "nfceh.sefaz.ce.gov.br",
    "www.fazenda.df.gov.br",
    "app.sefaz.es.gov.br",
    "homologacao.sefaz.es.gov.br",
    "nfe.sefaz.go.gov.br",
    "nfeweb.sefaz.go.gov.br",
    "homolog.sefaz.go.gov.br",
    "nfewebhomolog.sefaz.go.gov.br",
    "nfce.sefaz.ma.gov.br",
    "www.sefaz.mt.gov.br",
    "homologacao.sefaz.mt.gov.br",
    "www.dfe.ms.gov.br",
    "nfce.fazenda.mg.gov.br",
    "portalsped.fazenda.mg.gov.br",
    "appnfc.sefa.pa.gov.br",
    "www.sefaz.pb.gov.br",
    "www.receita.pb.gov.br",
    "www.fazenda.pr.gov.br",
    "nfce.sefaz.pe.gov.br",
    "www.sefaz.pi.gov.br",
    "www4.fazenda.rj.gov.br",
    "consultadfe.fazenda.rj.gov.br",
    "nfce.set.rn.gov.br",
    "www.sefaz.rs.gov.br",
    "www.nfce.sefin.ro.gov.br",
    "www.sefaz.rr.gov.br",
    "sat.sef.sc.gov.br",
    "www.nfce.fazenda.sp.gov.br",
    "www.nfce.se.gov.br",
    "www.sefaz.to.gov.br",
})

IMPORT_UNAVAILABLE = "Consulta disponível; importação automática indisponível nesta origem."
IMPORT_DEPENDENCY = (
    "Os itens dependem do webservice oficial de download do XML da NFC-e, "
    "que exige certificado digital e-CNPJ do contribuinte. A página do QR não é um contrato de dados. "
    "A Panne não a raspa e não contorna CAPTCHA nem certificado."
)


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
        "modality": None,
        "import_available": False,
        "items": [],
        "network_request": False,
        "reason": reason,
        "consultation_url": None,
        "existing_document_id": None,
    }


def _host_official(host: str) -> bool:
    name = host.lower().rstrip(".")
    if not name or name in {"localhost", "localhost.localdomain"} or name.endswith(".local"):
        return False
    try:
        ipaddress.ip_address(name)
        return False
    except ValueError:
        pass
    return name in _OFFICIAL_HOSTS


def same_organization_document_id(session: Session, principal: Principal, access_key: str) -> str | None:
    """Só o id da nota desta organização. Não cria, não altera e não lê outra organização."""
    org = _org(principal)
    found = session.scalar(
        select(FiscalInboundDocument.id).where(
            FiscalInboundDocument.organization_id == org,
            FiscalInboundDocument.access_key == access_key,
        )
    )
    return None if found is None else str(found)


def read_nfce_qr(principal: Principal, raw_url: str) -> dict:
    """Decodifica a URL. Não consulta a rede e não persiste."""
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_CAPTURE)
    text = (raw_url or "").strip()
    if not text or len(text) > 2000:
        return _rejected("codigo_invalido")
    parts = urlsplit(text)
    if parts.scheme not in {"https", "http"} or parts.username or parts.password:
        return _rejected("endereco_nao_permitido")
    allowed_port = {None, 443} if parts.scheme == "https" else {None, 80}
    if parts.port not in allowed_port:
        return _rejected("endereco_nao_permitido")
    host = parts.hostname or ""
    if not _host_official(host):
        return _rejected("origem_nao_reconhecida")
    query = parts.query
    if not query.startswith("p=") or "&" in query:
        return _rejected("codigo_invalido")
    fields = query[2:].split("|")
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
    online_layout = (version == "2" and len(fields) == 5) or (version == "3" and len(fields) == 3)
    tp_emis = key[34:35]
    key_emission = "online" if tp_emis == "1" else "contingencia"
    layout_emission = "online" if online_layout else "contingencia"
    https = parts.scheme == "https"
    return {
        "recognized": True,
        "modality": "leitura_chave",
        "import_available": False,
        "items": [],
        "network_request": False,
        "model": "65",
        "model_label": "NFC-e",
        "uf": _CUF.get(cuf),
        "cuf": cuf,
        "environment": "producao" if environment == "1" else "homologacao",
        "environment_label": "produção" if environment == "1" else "homologação",
        "qr_version": version,
        "emission": key_emission,
        "emission_label": "online" if key_emission == "online" else "contingência",
        "qr_layout": layout_emission,
        "emission_matches_layout": key_emission == layout_emission,
        "access_key": key,
        "series": str(int(key[22:25])),
        "number": str(int(key[25:34])),
        "signature_checked": False,
        "message": IMPORT_UNAVAILABLE,
        "dependency": IMPORT_DEPENDENCY,
        "consultation_url": text if https else None,
        "existing_document_id": None,
    }


def attach_existing_document(session: Session, principal: Principal, reading: dict) -> dict:
    """Completa a leitura com a nota já gravada nesta organização. Não grava."""
    if reading.get("recognized") and reading.get("access_key"):
        reading["existing_document_id"] = same_organization_document_id(
            session, principal, str(reading["access_key"])
        )
    return reading
