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


def calculation_out(row, *, invalidated: bool = False) -> dict:
    return {
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
        "algorithm_name": row.algorithm_name,
        "algorithm_version": row.algorithm_version,
        "auto_published": False,
    }


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


def price_out(row) -> dict:
    return {
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
    }
