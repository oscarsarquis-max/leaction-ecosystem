"""Resolução determinística de política de markup/margem.

Precedência: produto → família → organização.
Canal/estabelecimento: extensão posterior (não resolvidos neste ciclo).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.costing_pricing.comparison import formulas
from app.modules.costing_pricing.models import PricingMarkupPolicy
from app.modules.formula_lab.models import ProductFamily, TechnicalProduct


SCOPE_RANK = {"product": 0, "family": 1, "organization": 2}
SCOPE_LABEL = {
    "product": "produto",
    "family": "família",
    "organization": "organização",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _overlaps(row: PricingMarkupPolicy, at: datetime) -> bool:
    if row.valid_from > at:
        return False
    if row.valid_to is not None and row.valid_to <= at:
        return False
    return True


def policy_out(row: PricingMarkupPolicy) -> dict:
    return {
        "id": str(row.id),
        "code": row.code,
        "display_name": row.display_name,
        "kind": row.kind,
        "value": format(row.value, "f"),
        "scope_level": row.scope_level,
        "product_family_id": None if row.product_family_id is None else str(row.product_family_id),
        "technical_product_id": None
        if row.technical_product_id is None
        else str(row.technical_product_id),
        "status": row.status,
        "currency": getattr(row, "currency", None) or "BRL",
        "commercial_rounding_places": int(getattr(row, "commercial_rounding_places", 2) or 2),
        "valid_from": row.valid_from.isoformat() if row.valid_from else None,
        "valid_to": row.valid_to.isoformat() if row.valid_to else None,
        "justification": row.justification,
        "row_version": row.row_version,
        "created_by_user_id": str(row.created_by_user_id),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def derive_from_policy(*, kind: str, value: Decimal, cost: Decimal, places: int = 2) -> dict:
    """Uma entrada de política; a outra métrica é derivada. Arredondamento comercial no preço."""
    quant = Decimal("1").scaleb(-places)
    if kind == "markup_factor":
        price = (cost * value).quantize(quant, rounding=ROUND_HALF_UP)
        calc = formulas(price=price, cost=cost)
        return {
            "policy_kind": kind,
            "policy_value": format(value, "f"),
            "suggested_price": format(price, "f"),
            "derived_markup_factor": format(calc["markup_factor"], "f"),
            "derived_acrescimo_rate": format(calc["acrescimo_rate"], "f"),
            "derived_margin_rate": None
            if calc["margin_rate"] is None
            else format(calc["margin_rate"], "f"),
            "rounding": {"mode": "half_up", "places": places},
        }
    if kind == "margin_rate":
        # margem = (P-C)/P ⇒ P = C / (1 - margem)
        if value >= 1:
            raise ValueError("contrato_invalido")
        price = (cost / (Decimal("1") - value)).quantize(quant, rounding=ROUND_HALF_UP)
        calc = formulas(price=price, cost=cost)
        return {
            "policy_kind": kind,
            "policy_value": format(value, "f"),
            "suggested_price": format(price, "f"),
            "derived_markup_factor": format(calc["markup_factor"], "f"),
            "derived_acrescimo_rate": format(calc["acrescimo_rate"], "f"),
            "derived_margin_rate": None
            if calc["margin_rate"] is None
            else format(calc["margin_rate"], "f"),
            "rounding": {"mode": "half_up", "places": places},
        }
    raise ValueError("contrato_invalido")


def resolve_markup_policy(
    session: Session,
    *,
    organization_id: UUID,
    technical_product_id: UUID,
    at: datetime | None = None,
) -> dict:
    """Retorna política efetiva + substituídas + motivo se ausente."""
    when = at or _now()
    product = session.get(TechnicalProduct, technical_product_id)
    if product is None or product.organization_id != organization_id:
        return {
            "effective": None,
            "origin_level": None,
            "replaced": [],
            "reason": "product_absent",
            "reason_label": "Produto não encontrado para resolução de política",
            "human_summary": "Não foi possível resolver política: produto ausente.",
            "supported_precedence": ["product", "family", "organization"],
            "deferred_scopes": ["channel", "establishment"],
        }

    rows = list(
        session.scalars(
            select(PricingMarkupPolicy).where(
                PricingMarkupPolicy.organization_id == organization_id,
                PricingMarkupPolicy.status == "active",
            )
        )
    )
    candidates: list[PricingMarkupPolicy] = []
    for row in rows:
        if not _overlaps(row, when):
            continue
        if row.scope_level == "product" and row.technical_product_id == technical_product_id:
            candidates.append(row)
        elif (
            row.scope_level == "family"
            and product.family_id is not None
            and row.product_family_id == product.family_id
        ):
            candidates.append(row)
        elif row.scope_level == "organization":
            candidates.append(row)

    if not candidates:
        return {
            "effective": None,
            "origin_level": None,
            "replaced": [],
            "reason": "no_active_policy",
            "reason_label": "Nenhuma política de markup/margem ativa vigente para este produto",
            "human_summary": "Nenhuma política de markup ou margem está vigente para este produto.",
            "supported_precedence": ["product", "family", "organization"],
            "deferred_scopes": ["channel", "establishment"],
        }

    candidates.sort(
        key=lambda r: (
            SCOPE_RANK.get(r.scope_level, 99),
            int(r.priority or 100),
            r.valid_from,
            str(r.id),
        )
    )
    winner = candidates[0]
    replaced = [policy_out(r) for r in candidates[1:]]
    return {
        "effective": policy_out(winner),
        "origin_level": winner.scope_level,
        "replaced": replaced,
        "reason": None,
        "reason_label": None,
        "human_summary": human_resolution_label(session, winner, replaced, product),
        "supported_precedence": ["product", "family", "organization"],
        "deferred_scopes": ["channel", "establishment"],
    }


def human_resolution_label(
    session: Session,
    winner: PricingMarkupPolicy,
    replaced: list[dict],
    product: TechnicalProduct,
) -> str:
    kind_label = "Markup" if winner.kind == "markup_factor" else "Margem"
    if winner.kind == "markup_factor":
        value_txt = f"{format(winner.value.normalize(), 'f')}×"
    else:
        pct = (winner.value * Decimal("100")).normalize()
        value_txt = f"{format(pct, 'f')}%"
    scope = SCOPE_LABEL.get(winner.scope_level, winner.scope_level)
    subject = product.display_name
    if winner.scope_level == "family" and winner.product_family_id:
        fam = session.get(ProductFamily, winner.product_family_id)
        if fam is not None:
            subject = fam.display_name
    elif winner.scope_level == "organization":
        subject = "a organização"
    base = f"{kind_label} de {value_txt} definida no nível de {scope} ({subject})."
    if replaced:
        top = replaced[0]
        repl_scope = SCOPE_LABEL.get(str(top.get("scope_level")), str(top.get("scope_level")))
        base += f" Ela prevalece sobre a política da {repl_scope}."
    return base
