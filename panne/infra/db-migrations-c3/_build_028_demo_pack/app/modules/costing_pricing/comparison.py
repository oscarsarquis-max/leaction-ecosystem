"""Praticed price sale basis + economic comparison (domain).

Legacy prices without quantity+catalog unit remain readable but not comparable.
No silent unit equivalence in the UI layer.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


MONEY_PLACES = Decimal("0.000001")
RATE_PLACES = Decimal("0.00000001")


def _d(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def formulas(*, price: Decimal, cost: Decimal) -> dict[str, Decimal]:
    """Canonical economic formulas. Caller must ensure same commercial basis."""
    if cost == 0:
        raise ValueError("denominador_invalido")
    if price < 0 or cost < 0:
        raise ValueError("contrato_invalido")
    markup = price / cost
    acrescimo = (price - cost) / cost
    margem_pct = (price - cost) / price if price != 0 else None
    margem_money = price - cost
    return {
        "markup_factor": markup,
        "acrescimo_rate": acrescimo,
        "margin_rate": margem_pct,
        "margin_amount": margem_money,
    }


def sale_basis_payload(
    *,
    quantity,
    unit_id,
    unit_code: str | None = None,
    unit_display_name: str | None = None,
) -> dict:
    qty = _d(quantity)
    if qty is None or unit_id is None:
        return {
            "informed": False,
            "quantity": None,
            "unit": None,
            "label": None,
            "status": "not_informed",
            "status_label": "Base comercial do preço não informada",
        }
    if qty <= 0:
        return {
            "informed": False,
            "quantity": str(qty),
            "unit": None,
            "status": "invalid",
            "status_label": "Quantidade-base inválida",
            "label": None,
        }
    unit = {
        "id": str(unit_id),
        "code": unit_code,
        "display_name": unit_display_name or unit_code,
    }
    label = f"{qty.normalize()} {unit['display_name']}"
    return {
        "informed": True,
        "quantity": format(qty, "f"),
        "unit": unit,
        "label": label,
        "status": "informed",
        "status_label": "Base comercial informada",
    }


def build_comparison(
    *,
    price_amount,
    price_currency: str,
    sale_basis: dict,
    cost_amount,
    cost_currency: str | None,
    cost_basis_quantity=None,
    cost_basis_unit_id=None,
    cost_partial: bool = False,
    price_definitive_allowed: bool = True,
    sale_unit_dimension: str | None = None,
    sale_unit_si_factor=None,
    cost_unit_dimension: str | None = None,
    cost_unit_si_factor=None,
    package_content_quantity=None,
    package_content_unit_id=None,
    package_content_dimension: str | None = None,
    package_content_si_factor=None,
) -> dict:
    """Compare price vs cost only when bases are explicitly compatible.

    Supported conversions in this cycle:
    - same unit id
    - mass ↔ mass via catalog si_factor (g/kg)
    - package (count) ↔ content mass when net content is persisted
    Count ↔ mass without declared relation → blocked.
    """
    base = {
        "allowed": False,
        "reason": None,
        "reason_label": None,
        "price_normalized": None,
        "cost_normalized": None,
        "currency": price_currency,
        "markup_factor": None,
        "acrescimo_rate": None,
        "margin_rate": None,
        "margin_amount": None,
        "scope_complete_for_margin": False,
        "conversion": None,
    }
    if not sale_basis.get("informed"):
        base["reason"] = "sale_basis_not_informed"
        base["reason_label"] = sale_basis.get("status_label") or "Base comercial do preço não informada"
        return base
    price = _d(price_amount)
    cost = _d(cost_amount)
    if price is None:
        base["reason"] = "price_absent"
        base["reason_label"] = "Preço ausente"
        return base
    if cost is None:
        base["reason"] = "cost_absent"
        base["reason_label"] = "Custo ausente"
        return base
    if cost_currency and cost_currency != price_currency:
        base["reason"] = "currency_mismatch"
        base["reason_label"] = "Moedas incompatíveis"
        return base
    cost_qty = _d(cost_basis_quantity)
    cost_unit = cost_basis_unit_id
    sale_qty = _d(sale_basis.get("quantity"))
    sale_unit = (sale_basis.get("unit") or {}).get("id")
    if cost_unit is None or cost_qty is None or cost_qty <= 0 or sale_qty is None or sale_qty <= 0:
        base["reason"] = "cost_basis_not_informed"
        base["reason_label"] = "Base comercial do custo não informada para comparação"
        return base

    # Normalize both to "amount per 1 catalog unit" then convert units if needed.
    price_per_sale_unit = price / sale_qty
    cost_per_cost_unit = cost / cost_qty
    conversion_note = "same_unit"

    if str(cost_unit) == str(sale_unit):
        price_norm = price_per_sale_unit
        cost_norm = cost_per_cost_unit
    else:
        sale_dim = sale_unit_dimension
        cost_dim = cost_unit_dimension
        sale_si = _d(sale_unit_si_factor)
        cost_si = _d(cost_unit_si_factor)
        # mass ↔ mass via SI
        if sale_dim == "mass" and cost_dim == "mass" and sale_si and cost_si and sale_si > 0 and cost_si > 0:
            # normalize both to per kg (si_factor is kg-equivalent of 1 unit)
            price_norm = price_per_sale_unit / sale_si
            cost_norm = cost_per_cost_unit / cost_si
            conversion_note = "mass_si"
        # package count with declared net content matching cost mass unit
        elif (
            sale_dim == "count"
            and cost_dim == "mass"
            and package_content_quantity is not None
            and package_content_unit_id is not None
        ):
            pkg_qty = _d(package_content_quantity)
            pkg_si = _d(package_content_si_factor)
            cost_si = _d(cost_unit_si_factor)
            if pkg_qty is None or pkg_qty <= 0 or not pkg_si or not cost_si:
                base["reason"] = "unit_dimension_mismatch"
                base["reason_label"] = "Pacote sem conteúdo convertido para a base do custo"
                return base
            if str(package_content_unit_id) == str(cost_unit):
                # price is for 1 package containing pkg_qty of cost unit
                price_norm = price_per_sale_unit / pkg_qty
                cost_norm = cost_per_cost_unit
                conversion_note = "package_to_content"
            elif package_content_dimension == "mass" and cost_dim == "mass":
                content_kg = pkg_qty * pkg_si
                cost_kg = cost_si
                price_norm = price_per_sale_unit / content_kg
                cost_norm = cost_per_cost_unit / cost_kg
                conversion_note = "package_mass_si"
            else:
                base["reason"] = "unit_dimension_mismatch"
                base["reason_label"] = "Unidades comerciais incompatíveis"
                return base
        else:
            base["reason"] = "unit_dimension_mismatch"
            base["reason_label"] = "Unidades comerciais incompatíveis"
            return base

    try:
        calc = formulas(price=price_norm, cost=cost_norm)
    except ValueError as exc:
        code = str(exc)
        base["reason"] = code
        base["reason_label"] = (
            "Custo zero — markup indefinido" if code == "denominador_invalido" else "Valores inválidos"
        )
        return base
    definitive = bool(price_definitive_allowed) and not cost_partial
    base.update(
        {
            "allowed": True,
            "reason": None if definitive else "cost_partial",
            "reason_label": None
            if definitive
            else "Custo parcial — margem indicativa sobre o conhecido, não definitiva",
            "price_normalized": format(quantize_money(price_norm), "f"),
            "cost_normalized": format(quantize_money(cost_norm), "f"),
            "markup_factor": format(calc["markup_factor"].quantize(RATE_PLACES), "f"),
            "acrescimo_rate": format(calc["acrescimo_rate"].quantize(RATE_PLACES), "f"),
            "margin_rate": None
            if calc["margin_rate"] is None
            else format(calc["margin_rate"].quantize(RATE_PLACES), "f"),
            "margin_amount": format(quantize_money(calc["margin_amount"]), "f"),
            "scope_complete_for_margin": definitive,
            "conversion": conversion_note,
        }
    )
    return base
