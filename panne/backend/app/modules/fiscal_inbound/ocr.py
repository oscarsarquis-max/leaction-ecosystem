"""OCR de DANFE/foto. Demo usa fixtures sintéticas; Textract fica encapsulado e desligado."""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.modules.fiscal_inbound.constants import (
    DEMO_ACCESS_KEY_PREFIX,
    DEMO_EMITTER_TAX_ID,
    DEMO_LABEL,
    DEMO_RECIPIENT_TAX_ID,
    OCR_LIVE_FLAG,
)
from app.modules.production_planning.errors import InvalidStateError


@dataclass(frozen=True)
class OcrField:
    name: str
    value: str
    confidence: Decimal
    confirmed: bool = False


@dataclass(frozen=True)
class OcrResult:
    provider: str
    provider_version: str
    confidence: Decimal
    fields: tuple[OcrField, ...]
    raw_label: str


class OcrProvider(Protocol):
    def extract(self, payload: bytes, *, content_type: str) -> OcrResult: ...


def ocr_live_enabled() -> bool:
    return os.environ.get(OCR_LIVE_FLAG, "0").strip() == "1"


class SyntheticOcrProvider:
    """Fixtures sintéticas claramente rotuladas DEMONSTRACAO."""

    def extract(self, payload: bytes, *, content_type: str) -> OcrResult:
        _ = payload, content_type
        key = f"{DEMO_ACCESS_KEY_PREFIX}{'4' * 40}"
        fields = (
            OcrField("access_key", key, Decimal("0.91")),
            OcrField("emitter_name", f"FORNECEDOR {DEMO_LABEL} LTDA", Decimal("0.88")),
            OcrField("emitter_tax_id", DEMO_EMITTER_TAX_ID, Decimal("0.93")),
            OcrField("recipient_tax_id", DEMO_RECIPIENT_TAX_ID, Decimal("0.90")),
            OcrField("number", "99010", Decimal("0.95")),
            OcrField("series", "1", Decimal("0.97")),
            OcrField("issued_on", "2026-08-21", Decimal("0.86")),
            OcrField("item_1_description", f"Farinha — {DEMO_LABEL}", Decimal("0.80")),
            OcrField("item_1_quantity", "25", Decimal("0.84")),
            OcrField("item_1_unit", "KG", Decimal("0.92")),
        )
        avg = sum((f.confidence for f in fields), Decimal("0")) / Decimal(len(fields))
        return OcrResult(
            provider="synthetic",
            provider_version="1",
            confidence=avg.quantize(Decimal("0.0001")),
            fields=fields,
            raw_label=DEMO_LABEL,
        )


class TextractOcrProvider:
    """Stub encapsulado. Só executa se PANNE_OCR_LIVE=1 — nesta fase sempre bloqueado."""

    def extract(self, payload: bytes, *, content_type: str) -> OcrResult:
        _ = payload, content_type
        if not ocr_live_enabled():
            raise InvalidStateError("ocr_live_desativado")
        raise InvalidStateError("ocr_textract_ainda_nao_ativado")


def default_ocr_provider() -> OcrProvider:
    return SyntheticOcrProvider()
