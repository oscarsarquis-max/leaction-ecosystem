"""Leitura de XML tipo NF-e. Sem DTD, sem entidade externa e sem recalcular total."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.modules.fiscal_inbound.constants import CURRENCY
from app.modules.production_planning.errors import ValidationError

try:  # pragma: no cover - depende do ambiente
    from defusedxml.ElementTree import fromstring as _parse_xml

    PARSER_NAME = "defusedxml"
except ImportError:  # pragma: no cover - fallback quando o pacote não está instalado
    # A rejeição byte a byte de DOCTYPE/ENTITY abaixo é o que remove XXE; sem ela
    # o ElementTree padrão não deve receber XML de terceiro.
    from xml.etree.ElementTree import fromstring as _parse_xml

    PARSER_NAME = "elementtree_no_doctype"


PARSER_VERSION = "1"
_FORBIDDEN = (b"<!doctype", b"<!entity", b"<!notation")
_TAX_KEYS = frozenset(
    {
        "vICMS",
        "vICMSDeson",
        "vST",
        "vFCP",
        "vFCPST",
        "vFCPSTRet",
        "vIPI",
        "vIPIDevol",
        "vII",
        "vPIS",
        "vCOFINS",
        "vOutro",
        "vTotTrib",
    }
)
_ACCESS_KEY = re.compile(r"(\d{44})")
_MAX_XML_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class ParsedItem:
    line_number: int
    supplier_code: str | None
    gtin: str | None
    description: str
    ncm: str | None
    cfop: str | None
    cest: str | None
    unit_code: str | None
    quantity: Decimal
    unit_price: Decimal | None
    gross_amount: Decimal | None
    discount: Decimal | None
    freight: Decimal | None
    declared_total: Decimal | None
    taxes: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedDocument:
    access_key: str | None
    fiscal_model: str | None
    number: str | None
    series: str | None
    issued_at: datetime | None
    emitter_tax_id: str | None
    emitter_name: str | None
    recipient_tax_id: str | None
    recipient_name: str | None
    protocol: str | None
    fiscal_status: str | None
    currency: str
    totals: dict
    taxes: dict
    freight: Decimal | None
    discount: Decimal | None
    items: tuple[ParsedItem, ...]


def as_bytes(payload: str | bytes) -> bytes:
    return payload.encode("utf-8") if isinstance(payload, str) else payload


def _reject_unsafe(raw: bytes) -> bytes:
    if len(raw) > _MAX_XML_BYTES:
        raise ValidationError("anexo_excede_limite")
    head = raw[:4096].lower()
    for marker in _FORBIDDEN:
        if marker in head:
            raise ValidationError("xml_entidade_proibida")
    return raw


def _tag(element) -> str:
    name = element.tag
    return name.rsplit("}", 1)[-1] if isinstance(name, str) and "}" in name else str(name)


def _first(element, name: str):
    for child in element.iter():
        if _tag(child) == name:
            return child
    return None


def _children(element, name: str) -> list:
    return [child for child in element.iter() if _tag(child) == name]


def _text(element, name: str) -> str | None:
    found = _first(element, name) if element is not None else None
    if found is None or found.text is None:
        return None
    value = found.text.strip()
    return value or None


def _decimal(element, name: str) -> Decimal | None:
    raw = _text(element, name)
    if raw is None:
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError("contrato_invalido") from exc


def _timestamp(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("contrato_invalido") from exc


def _tax_snapshot(element) -> dict:
    snapshot: dict[str, str] = {}
    if element is None:
        return snapshot
    for child in element.iter():
        if child is element or child.text is None:
            continue
        value = child.text.strip()
        if value:
            snapshot[_tag(child)] = value
    return snapshot


def _access_key(root) -> str | None:
    info = _first(root, "infNFe")
    candidate = None
    if info is not None:
        candidate = info.attrib.get("Id") or info.attrib.get("id")
    if candidate is None:
        candidate = _text(root, "chNFe")
    if candidate is None:
        return None
    found = _ACCESS_KEY.search(candidate)
    return found.group(1) if found else None


def parse_document(payload: str | bytes) -> ParsedDocument:
    raw = _reject_unsafe(as_bytes(payload))
    try:
        root = _parse_xml(raw)
    except ValidationError:
        raise
    except Exception as exc:  # noqa: BLE001 - qualquer falha de parse é contrato inválido
        raise ValidationError("xml_invalido") from exc

    identification = _first(root, "ide")
    emitter = _first(root, "emit")
    recipient = _first(root, "dest")
    totals_node = _first(root, "ICMSTot")
    protocol_node = _first(root, "infProt")

    details = _children(root, "det")
    if not details:
        raise ValidationError("xml_sem_itens")

    items: list[ParsedItem] = []
    for index, detail in enumerate(details, start=1):
        product = _first(detail, "prod")
        if product is None:
            raise ValidationError("xml_sem_itens")
        description = _text(product, "xProd")
        quantity = _decimal(product, "qCom")
        if description is None or quantity is None or quantity <= 0:
            raise ValidationError("contrato_invalido")
        raw_number = detail.attrib.get("nItem")
        try:
            line_number = int(raw_number) if raw_number else index
        except ValueError as exc:
            raise ValidationError("contrato_invalido") from exc
        gtin = _text(product, "cEAN")
        items.append(
            ParsedItem(
                line_number=line_number,
                supplier_code=_text(product, "cProd"),
                gtin=None if gtin in {None, "SEM GTIN"} else gtin,
                description=description,
                ncm=_text(product, "NCM"),
                cfop=_text(product, "CFOP"),
                cest=_text(product, "CEST"),
                unit_code=_text(product, "uCom"),
                quantity=quantity,
                unit_price=_decimal(product, "vUnCom"),
                gross_amount=_decimal(product, "vProd"),
                discount=_decimal(product, "vDesc"),
                freight=_decimal(product, "vFrete"),
                declared_total=_decimal(product, "vProd"),
                taxes=_tax_snapshot(_first(detail, "imposto")),
            )
        )

    return ParsedDocument(
        access_key=_access_key(root),
        fiscal_model=_text(identification, "mod"),
        number=_text(identification, "nNF"),
        series=_text(identification, "serie"),
        issued_at=_timestamp(_text(identification, "dhEmi") or _text(identification, "dEmi")),
        emitter_tax_id=_text(emitter, "CNPJ") or _text(emitter, "CPF"),
        emitter_name=_text(emitter, "xNome"),
        recipient_tax_id=_text(recipient, "CNPJ") or _text(recipient, "CPF"),
        recipient_name=_text(recipient, "xNome"),
        protocol=_text(protocol_node, "nProt"),
        fiscal_status=_text(protocol_node, "xMotivo") or _text(protocol_node, "cStat"),
        currency=CURRENCY,
        totals=_tax_snapshot(totals_node),
        taxes={
            key: value
            for key, value in _tax_snapshot(totals_node).items()
            if key in _TAX_KEYS
        },
        freight=_decimal(totals_node, "vFrete"),
        discount=_decimal(totals_node, "vDesc"),
        items=tuple(items),
    )
