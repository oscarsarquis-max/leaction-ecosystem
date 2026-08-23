"""Catálogo de porção para panificação. IN 75/2020 Anexo I, acesso 2026-08-23."""

from decimal import Decimal

PORTION_CATALOG = (
    {
        "code": "pao",
        "label": "Pães",
        "reference_g": Decimal("50"),
        "household_measure": "1 unidade",
        "presentation": "peça ou fatia",
        "ready_or_prepared": "pronto",
        "source": "IN 75/2020 Anexo I",
    },
    {
        "code": "bolo",
        "label": "Bolos e similares",
        "reference_g": Decimal("60"),
        "household_measure": "1 fatia",
        "presentation": "fatia",
        "ready_or_prepared": "pronto",
        "source": "IN 75/2020 Anexo I",
    },
    {
        "code": "biscoito",
        "label": "Biscoitos e cookies",
        "reference_g": Decimal("30"),
        "household_measure": "unidade ou porção",
        "presentation": "unidade",
        "ready_or_prepared": "pronto",
        "source": "IN 75/2020 Anexo I",
    },
    {
        "code": "massa",
        "label": "Massas e similares",
        "reference_g": Decimal("80"),
        "household_measure": "1 porção crua",
        "presentation": "massa",
        "ready_or_prepared": "preparar",
        "source": "IN 75/2020 Anexo I",
    },
)


def get_portion(code: str | None) -> dict | None:
    if not code:
        return None
    return next((row for row in PORTION_CATALOG if row["code"] == code), None)


def serialize_portions() -> list[dict]:
    return [
        {
            **row,
            "reference_g": format(row["reference_g"], "f"),
            "confirmation_required": True,
        }
        for row in PORTION_CATALOG
    ]
