"""Serialização de custos. Sem fórmula soberana no cliente."""

from decimal import Decimal


def _dec(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def _iso(value) -> str | None:
    return None if value is None else value.isoformat()


def policy_out(row, version=None) -> dict:
    data = {
        "id": str(row.id),
        "code": row.code,
        "display_name": row.display_name,
        "status": row.status,
        "row_version": row.row_version,
        "created_at": _iso(row.created_at),
    }
    if version is not None:
        data["version"] = {
            "id": str(version.id),
            "version_number": version.version_number,
            "status": version.status,
            "currency": version.currency,
            "price_criterion": version.price_criterion,
            "enabled_categories": version.enabled_categories,
            "use_gross_quantity": version.use_gross_quantity,
            "include_return": version.include_return,
            "include_waste": version.include_waste,
            "use_sellable_yield": version.use_sellable_yield,
            "algorithm_name": version.algorithm_name,
            "algorithm_version": version.algorithm_version,
        }
    return data


def calculation_out(row, *, invalidated: bool = False, enrich: dict | None = None) -> dict:
    data = {
        "id": str(row.id),
        "kind": row.kind,
        "completeness": "invalidated" if invalidated else row.completeness,
        "currency": row.currency,
        "total_amount": _dec(row.total_amount),
        "batch_amount": _dec(row.batch_amount),
        "mass_amount": _dec(row.mass_amount),
        "produced_unit_amount": _dec(row.produced_unit_amount),
        "sellable_unit_amount": _dec(row.sellable_unit_amount),
        "produced_quantity": _dec(row.produced_quantity),
        "sellable_quantity": _dec(row.sellable_quantity),
        "content_hash": row.content_hash,
        "valuation_at": _iso(row.valuation_at),
        "created_at": _iso(row.created_at),
        "algorithm_name": row.algorithm_name,
        "algorithm_version": row.algorithm_version,
        "auto_published": False,
        "technical_product_id": None
        if row.technical_product_id is None
        else str(row.technical_product_id),
        "formulation_id": None if row.formulation_id is None else str(row.formulation_id),
    }
    if enrich:
        data.update(enrich)
    return data


def simulation_out(row) -> dict:
    return {
        "id": str(row.id),
        "kind": row.kind,
        "channel": row.channel,
        "suggested_price": _dec(row.suggested_price),
        "warning": row.warning,
        "snapshot": row.snapshot,
        "content_hash": row.content_hash,
        "disclaimer": "Preço sugerido não é preço publicado.",
    }


def price_out(row, *, unit_row=None, comparison: dict | None = None) -> dict:
    from app.modules.costing_pricing.comparison import sale_basis_payload

    basis = sale_basis_payload(
        quantity=row.sale_basis_quantity,
        unit_id=row.sale_basis_unit_id,
        unit_code=None if unit_row is None else unit_row.code,
        unit_display_name=None if unit_row is None else getattr(unit_row, "name", None) or getattr(unit_row, "display_name", None),
    )
    data = {
        "id": str(row.id),
        "channel": row.channel,
        "currency": row.currency,
        "amount": _dec(row.amount),
        "status": row.status,
        "valid_from": _iso(row.valid_from),
        "valid_to": _iso(row.valid_to),
        "row_version": row.row_version,
        "justification": row.justification,
        "technical_product_id": str(row.technical_product_id),
        "establishment_id": None if row.establishment_id is None else str(row.establishment_id),
        "sale_basis": basis,
        "persisted": {
            "amount": _dec(row.amount),
            "currency": row.currency,
            "sale_basis_quantity": _dec(row.sale_basis_quantity),
            "sale_basis_unit_id": None
            if row.sale_basis_unit_id is None
            else str(row.sale_basis_unit_id),
        },
        "derived": {
            "markup_factor": None,
            "margin_rate": None,
            "margin_amount": None,
            "source": "none",
        },
        "effective_markup_policy": None,
        "effective_markup_policy_note": "Nenhuma política de markup/margem ativa resolvida para este preço.",
    }
    if comparison is not None:
        data["comparison"] = comparison
        if comparison.get("allowed"):
            data["derived"] = {
                "markup_factor": comparison.get("markup_factor"),
                "margin_rate": comparison.get("margin_rate"),
                "margin_amount": comparison.get("margin_amount"),
                "acrescimo_rate": comparison.get("acrescimo_rate"),
                "source": "backend_comparison",
                "scope_complete_for_margin": comparison.get("scope_complete_for_margin"),
            }
        else:
            data["derived"]["source"] = "blocked"
            data["derived"]["block_reason"] = comparison.get("reason")
            data["derived"]["block_reason_label"] = comparison.get("reason_label")
    else:
        data["comparison"] = {
            "allowed": False,
            "reason": "sale_basis_not_informed" if not basis["informed"] else "cost_not_provided",
            "reason_label": basis["status_label"]
            if not basis["informed"]
            else "Custo de referência não fornecido neste recorte",
            "markup_factor": None,
            "margin_rate": None,
            "margin_amount": None,
        }
    return data

