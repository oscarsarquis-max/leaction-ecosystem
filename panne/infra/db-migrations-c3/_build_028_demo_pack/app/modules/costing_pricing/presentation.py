"""Apresentação humana de custos. Sem inventar preço nem zerar ausência."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.costing_pricing.constants import ZERO
from app.modules.costing_pricing.formulas import quantize_percent
from app.modules.costing_pricing.models import (
    CostingCalculation,
    CostingComponent,
    CostingEvidence,
    CostingPolicyVersion,
)
from app.modules.formula_lab.models import Formulation, FormulationItem
from app.modules.ingredient_catalog.models import Ingredient, IngredientVersion
from app.modules.production_planning.models import ProductionOrderMaterial

CATEGORY_LABEL = {
    "ingredient": "Ingrediente",
    "packaging": "Embalagem",
    "labor": "Mão de obra",
    "waste": "Desperdício",
    "rework": "Retrabalho",
    "energy": "Energia",
    "other": "Outros",
}

QUALITY_LABEL = {
    "current_price": "Preço vigente",
    "standard_cost": "Custo padrão",
    "missing": "Preço ausente",
    "manual_assumption": "Premissa manual",
    "operational_fact": "Fato operacional",
}

KIND_LABEL = {
    "planned": "previsto",
    "standard": "padrão",
    "actual": "realizado",
}


def _dec(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def _uuid(value) -> UUID | None:
    if value is None:
        return None
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError):
        return None


def ingredient_display_name(session: Session, ingredient_version_id) -> str | None:
    version_id = _uuid(ingredient_version_id)
    if version_id is None:
        return None
    version = session.get(IngredientVersion, version_id)
    if version is None:
        return None
    ingredient = session.get(Ingredient, version.ingredient_id)
    return None if ingredient is None else ingredient.display_name


def resolve_component_name(session: Session, row: CostingComponent, evidence: dict) -> str:
    if row.origin_type == "formulation_item":
        item = session.get(FormulationItem, _uuid(row.origin_id))
        if item is not None:
            name = ingredient_display_name(session, item.ingredient_version_id)
            if name:
                return name
    if row.origin_type == "order_material":
        material = session.get(ProductionOrderMaterial, _uuid(row.origin_id))
        if material is not None:
            name = ingredient_display_name(session, material.ingredient_version_id)
            if name:
                return name
    if evidence.get("ingredient_version_id"):
        name = ingredient_display_name(session, evidence["ingredient_version_id"])
        if name:
            return name
    if evidence.get("code"):
        return str(evidence["code"])
    if row.origin_type == "leftover":
        return "Sobra (não é desperdício)"
    if row.origin_type == "scrap":
        return "Refugo"
    if row.origin_type == "waste":
        return "Desperdício"
    if row.origin_type == "assumption":
        return "Premissa de custeio"
    return CATEGORY_LABEL.get(row.category, "Componente")


def memory_lines(row: CostingComponent, evidence: dict, display_name: str) -> list[dict]:
    lines: list[dict] = []
    qty = None if row.quantity is None else format(row.quantity, "f")
    unit = row.unit_code
    lines.append(
        {
            "code": "formula",
            "label": "Fórmula",
            "value": (
                f"Custo de {display_name} = quantidade convertida ÷ quantidade da embalagem × preço unitário"
                if row.amount is not None
                else f"Custo de {display_name} permanece ausente — ausência não é zero"
            ),
        }
    )
    if qty is not None:
        lines.append(
            {
                "code": "quantity",
                "label": "Quantidade",
                "value": f"{qty} {unit}" if unit else qty,
            }
        )
    if evidence.get("converted_quantity"):
        pack_unit = evidence.get("package_unit_code") or ""
        lines.append(
            {
                "code": "converted_quantity",
                "label": "Quantidade convertida",
                "value": f"{evidence['converted_quantity']} {pack_unit}".strip(),
            }
        )
    if evidence.get("conversion_factor"):
        lines.append(
            {
                "code": "conversion",
                "label": "Conversão",
                "value": (
                    f"fator {evidence['conversion_factor']}"
                    f" ({evidence.get('conversion_source') or 'conversão'})"
                ),
            }
        )
    if evidence.get("unit_price") is not None:
        currency = evidence.get("currency") or "BRL"
        pack_qty = evidence.get("package_quantity")
        pack_unit = evidence.get("package_unit_code") or ""
        lines.append(
            {
                "code": "unit_price",
                "label": "Preço da embalagem",
                "value": f"{evidence['unit_price']} {currency} / {pack_qty} {pack_unit}".strip(),
            }
        )
    if evidence.get("observed_at"):
        lines.append(
            {
                "code": "observed_at",
                "label": "Vigência do preço",
                "value": str(evidence["observed_at"]),
            }
        )
    if evidence.get("supplier_code") or evidence.get("supplier_sku"):
        lines.append(
            {
                "code": "supplier",
                "label": "Origem do preço",
                "value": " · ".join(
                    part
                    for part in (
                        evidence.get("supplier_code"),
                        evidence.get("supplier_sku"),
                        evidence.get("criterion"),
                    )
                    if part
                ),
            }
        )
    if evidence.get("planned_batches"):
        lines.append(
            {
                "code": "batches",
                "label": "Lotes planejados",
                "value": str(evidence["planned_batches"]),
            }
        )
    if evidence.get("consume") is not None:
        lines.append(
            {
                "code": "consume",
                "label": "Consumo / retorno / desperdício",
                "value": (
                    f"consumo {evidence.get('consume')}; "
                    f"retorno {evidence.get('return')}; "
                    f"desperdício {evidence.get('waste')}"
                ),
            }
        )
    if row.amount is not None:
        lines.append(
            {
                "code": "result",
                "label": "Resultado do componente",
                "value": format(row.amount, "f"),
            }
        )
    else:
        lines.append(
            {
                "code": "result",
                "label": "Resultado do componente",
                "value": "ausente",
            }
        )
    lines.append(
        {
            "code": "rounding",
            "label": "Arredondamento",
            "value": "Dinheiro com ROUND_HALF_UP (até 6 casas no motor; apresentação em BRL).",
        }
    )
    return lines


def composition(session: Session, calculation: CostingCalculation) -> list[dict]:
    rows = list(
        session.scalars(
            select(CostingComponent).where(CostingComponent.costing_calculation_id == calculation.id)
        )
    )
    evidence_rows = list(
        session.scalars(
            select(CostingEvidence).where(
                CostingEvidence.costing_component_id.in_([row.id for row in rows] or [UUID(int=0)])
            )
        )
    )
    evidence_by_component = {row.costing_component_id: row.payload or {} for row in evidence_rows}
    total = calculation.total_amount
    items = []
    for row in rows:
        evidence = evidence_by_component.get(row.id, {})
        display_name = resolve_component_name(session, row, evidence)
        share = None
        if total and total > ZERO and row.amount is not None:
            share = quantize_percent(row.amount / total * Decimal("100"))
        items.append(
            {
                "id": str(row.id),
                "display_name": display_name,
                "category": row.category,
                "category_label": CATEGORY_LABEL.get(row.category, row.category),
                "amount": None if row.amount is None else format(row.amount, "f"),
                "quantity": None if row.quantity is None else format(row.quantity, "f"),
                "unit_code": row.unit_code,
                "quality": row.quality,
                "quality_label": QUALITY_LABEL.get(row.quality, row.quality),
                "share_percent": None if share is None else format(share, "f"),
                "price_missing": row.amount is None or row.quality == "missing",
                "memory": memory_lines(row, evidence, display_name),
            }
        )
    return items


def calculation_subject(session: Session, calc: CostingCalculation) -> dict:
    """Nomes públicos sem depender de colunas comerciais ainda ausentes no schema legado."""
    from sqlalchemy import text

    product_name = None
    product_code = None
    db_supply_mode = None
    if calc.technical_product_id:
        row = session.execute(
            text("SELECT display_name, code, supply_mode FROM technical_product WHERE id = :id"),
            {"id": calc.technical_product_id},
        ).first()
        if row is not None:
            product_name, product_code, db_supply_mode = row[0], row[1], row[2]
    # Preferir coluna canônica; fallback por nome/código (legado MANTEIGA-PT / "comprada").
    supply_mode = (
        db_supply_mode
        if db_supply_mode in {"purchased", "produced", "mixed", "intermediate", "combo"}
        else infer_supply_mode(product_name, product_code)
    )
    formulation_name = None
    if calc.formulation_id:
        formulation = session.get(Formulation, calc.formulation_id)
        if formulation is not None:
            formulation_name = formulation.display_name
    yield_units = None
    target_unit_weight_g = None
    if calc.formulation_version_id:
        row = session.execute(
            text(
                """
                SELECT yield_units, target_unit_weight_g
                FROM formulation_version WHERE id = :id
                """
            ),
            {"id": calc.formulation_version_id},
        ).first()
        if row is not None:
            yield_units = row[0]
            target_unit_weight_g = None if row[1] is None else format(row[1], "f")
    if supply_mode == "purchased":
        if yield_units is None and calc.sellable_quantity is not None:
            yield_units = calc.sellable_quantity
        has_commercial = True
    else:
        has_commercial = bool(yield_units) or bool(target_unit_weight_g)
    return {
        "product_display_name": product_name,
        "formulation_display_name": formulation_name,
        "supply_mode": supply_mode,
        "kind": calc.kind,
        "kind_label": KIND_LABEL.get(calc.kind, calc.kind),
        "commercial_presentation": {
            "defined": has_commercial,
            "yield_units": yield_units,
            "target_unit_weight_g": target_unit_weight_g,
            "action_label": None
            if has_commercial
            else "Definir apresentação/unidade de venda do produto",
            "action_hint": None
            if has_commercial
            else (
                "Sem rendimento em unidades ou peso-alvo por unidade na receita publicada, "
                "o custo por unidade vendável não pode ser calculado."
            ),
        },
    }


def cost_base_for_pricing(calc: CostingCalculation, scope: dict | None = None) -> dict:
    """Escolha determinística do custo-base para a calculadora (sem inventar valor)."""
    purchased = bool(scope and scope.get("mode") == "purchased")
    if scope is not None:
        if purchased:
            scope_incomplete = not scope.get("acquisition_complete", False)
        else:
            scope_incomplete = not scope.get("production_complete", False)
    else:
        scope_incomplete = calc.completeness != "complete"
    if calc.sellable_unit_amount is not None:
        if purchased:
            origin_label = "Custo de aquisição por unidade"
            unit_label = "R$ / unidade"
        elif scope and scope.get("ingredients_complete") and not scope.get("production_complete"):
            origin_label = "Custo de ingredientes por unidade vendável"
            unit_label = "R$ / unidade vendável"
        else:
            origin_label = "Custo por unidade vendável"
            unit_label = "R$ / unidade vendável"
        return {
            "amount": _dec(calc.sellable_unit_amount),
            "origin": "sellable_unit",
            "origin_label": origin_label,
            "unit_label": unit_label,
            "usable": True,
            "incomplete": scope_incomplete,
        }
    if calc.produced_unit_amount is not None:
        return {
            "amount": _dec(calc.produced_unit_amount),
            "origin": "produced_unit",
            "origin_label": "Custo por unidade produzida",
            "unit_label": "R$ / unidade produzida",
            "usable": True,
            "incomplete": scope_incomplete,
        }
    if calc.total_amount is not None:
        return {
            "amount": _dec(calc.total_amount),
            "origin": "batch_total",
            "origin_label": (
                "Custo de aquisição conhecido"
                if purchased
                else "Custo do recorte (não é custo unitário vendável)"
            ),
            "unit_label": "R$ / aquisição" if purchased else "R$ / recorte",
            "usable": True,
            "incomplete": scope_incomplete,
        }
    return {
        "amount": None,
        "origin": "absent",
        "origin_label": "Custo-base ausente",
        "unit_label": None,
        "usable": False,
        "incomplete": True,
    }



def sellable_absence_reason(calc: CostingCalculation, policy: CostingPolicyVersion | None) -> str | None:
    if calc.sellable_unit_amount is not None:
        return None
    if calc.kind in {"planned", "standard"}:
        return (
            "Custo por unidade vendável exige apresentação comercial definida "
            "(unidades de rendimento ou peso-alvo por unidade). "
            "A escala de massa não inventa unidade de venda."
        )
    if calc.kind == "actual":
        if policy is not None and policy.use_sellable_yield:
            return (
                "No realizado, o custo por unidade vendável exige rendimento vendável confiável "
                "persistido nos lotes. Sem esse rendimento, o valor permanece ausente."
            )
        return "Política sem uso de rendimento vendável; custo por unidade vendável não calculado."
    return "Custo por unidade vendável ausente."


def price_basis_contract() -> dict:
    """Contrato econômico do preço de fornecedor usado no motor."""
    return {
        "code": "package_price",
        "label": "Preço da embalagem",
        "formula": "custo = (quantidade convertida ÷ quantidade da embalagem) × preço da embalagem",
        "note": (
            "O campo unit_price do fornecedor é o valor da embalagem inteira "
            "(package_quantity na unidade da embalagem), não o preço por kg isolado "
            "nem por grama, salvo quando a embalagem for 1 kg ou 1 g."
        ),
        "flour_audit": {
            "sku": "SKU-FAR-25",
            "package": "25 kg",
            "finding": (
                "Contrato/motor = preço da embalagem. Os valores históricos 12,50 / 13,10 / 13,00 "
                "tinham magnitude típica de R$/kg e, aplicados como embalagem, geravam ~R$ 0,52/kg "
                "(inadequado). Normalizados ×25 → 312,50 / 327,50 / 325,00 por saco, "
                "preservando data e origem (seed-demo / receipt)."
            ),
            "normalized_package_prices_brl": ["312.50", "327.50", "325.00"],
        },
    }



def infer_supply_mode(product_name: str | None, product_code: str | None = None) -> str:
    """Detecta comprado sem exigir coluna supply_mode no schema legado."""
    blob = f"{product_name or ''} {product_code or ''}".lower()
    if "comprado" in blob or "comprada" in blob or "purchased" in blob:
        return "purchased"
    code = (product_code or "").upper()
    if code.endswith("-PT") or code.endswith("-COMP") or code.endswith("-BUY"):
        return "purchased"
    return "produced"


def evaluate_planned_actual(metric: str, planned, actual) -> dict:
    """Sinais por métrica: custo menor=favorável; rendimento maior=favorável; zero=neutro."""
    if planned is None or actual is None:
        return {"delta": None, "signal": None, "signal_label": None}
    p = Decimal(str(planned))
    a = Decimal(str(actual))
    delta = a - p
    if delta == 0:
        signal = "neutral"
        label = "neutro"
    elif metric == "yield":
        signal = "favorable" if delta > 0 else "unfavorable"
        label = "favorável" if delta > 0 else "desfavorável"
    else:  # cost and other cost-like metrics
        signal = "favorable" if delta < 0 else "unfavorable"
        label = "favorável" if delta < 0 else "desfavorável"
    return {"delta": format(delta, "f"), "signal": signal, "signal_label": label}


SCOPE_CATEGORY_META = {
    "ingredient": {"label": "Ingredientes", "required_for_ingredients": True},
    "packaging": {"label": "Embalagem", "absence_label": "Embalagem não configurada"},
    "labor": {"label": "Mão de obra", "absence_label": "Mão de obra não configurada"},
    "energy": {"label": "Energia/processo", "absence_label": "Energia/processo não configurado"},
    "outsourced": {"label": "Terceirização", "absence_label": "Terceirização não configurada"},
    "variable_indirect": {"label": "Indiretos variáveis", "absence_label": "Custos indiretos não configurados"},
    "fixed_allocation": {"label": "Rateio fixo", "absence_label": "Rateio fixo não configurado"},
    "waste": {"label": "Perdas/desperdício", "absence_label": "Perdas não configuradas"},
    "rework": {"label": "Retrabalho", "absence_label": "Retrabalho não configurado"},
    "other": {"label": "Outros", "absence_label": "Outros custos não configurados"},
}


def cost_scope_report(
    components: list[dict],
    *,
    policy: CostingPolicyVersion | None,
    completeness: str,
    supply_mode: str | None = None,
) -> dict:
    """Completude por escopo: produção ≠ aquisição; ingredientes ≠ custo total."""
    mode = supply_mode or "produced"
    purchased = mode == "purchased"
    enabled = list(policy.enabled_categories) if policy and policy.enabled_categories else ["ingredient"]
    by_cat: dict[str, list[dict]] = {}
    for c in components:
        by_cat.setdefault(c.get("category") or "other", []).append(c)

    # Categorias produtivas não se aplicam a mercadoria comprada.
    production_only = {
        "labor",
        "energy",
        "outsourced",
        "variable_indirect",
        "fixed_allocation",
        "waste",
        "rework",
    }
    # Embalagem só é "adicional de aquisição" se houver linhas; senão N/A no comprado.
    acquisition_labels = {
        "ingredient": "Valor de compra",
        "other": "Outros encargos de aquisição",
        "packaging": "Embalagem adicional",
    }

    categories = []
    for code in enabled:
        meta = SCOPE_CATEGORY_META.get(code, {"label": code, "absence_label": f"{code} não configurado"})
        rows = by_cat.get(code, [])
        valued = [r for r in rows if r.get("amount") is not None]
        missing = [r for r in rows if r.get("amount") is None or r.get("price_missing")]

        if purchased and (code in production_only or (code == "packaging" and not rows)):
            state = "not_applicable"
            state_label = "Não se aplica"
            label = meta["label"]
            amount = None
        elif purchased and code in acquisition_labels:
            label = acquisition_labels[code]
            if not rows:
                # Encargos de aquisição ainda não modelados: declarar ausência sem exigir produção.
                state = "not_configured"
                state_label = f"{label} não informado"
                amount = None
            elif missing and not valued:
                state = "absent"
                state_label = "Ausente (sem valor)"
                amount = None
            elif missing:
                state = "partial"
                state_label = "Parcial"
                amount = format(sum(Decimal(r["amount"]) for r in valued), "f")
            else:
                state = "valued"
                state_label = "Valorizado"
                amount = format(sum(Decimal(r["amount"]) for r in valued), "f")
        else:
            label = meta["label"]
            if not rows:
                state = "not_configured"
                state_label = meta.get("absence_label") or f"{label} não configurada"
                amount = None
            elif missing and not valued:
                state = "absent"
                state_label = "Ausente (sem valor)"
                amount = None
            elif missing:
                state = "partial"
                state_label = "Parcial"
                amount = format(sum(Decimal(r["amount"]) for r in valued), "f")
            else:
                state = "valued"
                state_label = "Valorizado"
                amount = format(sum(Decimal(r["amount"]) for r in valued), "f")

        categories.append(
            {
                "code": code,
                "label": label,
                "state": state,
                "state_label": state_label,
                "valued_count": len(valued),
                "missing_count": len(missing),
                "amount": amount,
            }
        )

    ingredient_rows = by_cat.get("ingredient", [])
    ingredient_valued = [r for r in ingredient_rows if r.get("amount") is not None]
    ingredient_missing = [r for r in ingredient_rows if r.get("amount") is None or r.get("price_missing")]
    ingredients_complete = bool(ingredient_rows) and not ingredient_missing

    if purchased:
        # Aquisição completa quando o valor de compra está valorizado e não há parcial entre aplicáveis.
        applicable = [c for c in categories if c["state"] != "not_applicable"]
        acquisition_complete = (
            ingredients_complete
            and all(c["state"] in {"valued", "not_configured"} for c in applicable)
            and completeness in {"complete", "partial"}
            and ingredients_complete
        )
        # Sem frete/impostos no banco: valor de compra completo basta para preço definitivo.
        acquisition_complete = ingredients_complete and not any(
            c["state"] in {"partial", "absent"} for c in applicable
        )
        production_complete = False
        if acquisition_complete:
            scope_label = "Custo de aquisição completo"
            margin_label = "Margem sobre o custo de aquisição"
            completeness_label = "Custo de aquisição completo"
            hint = (
                "Escopo de aquisição: valor de compra conhecido. "
                "Frete, impostos não recuperáveis e demais encargos entram quando configurados — "
                "não exigem receita, rendimento produtivo, mão de obra ou energia."
            )
        else:
            scope_label = "Custo de aquisição parcial"
            margin_label = "Margem sobre o custo de aquisição (parcial)"
            completeness_label = "Custo de aquisição parcial"
            hint = (
                "Há lacunas no valor de compra. Categorias produtivas não se aplicam a mercadoria comprada."
            )
        comparison_scope_label = "Mercadoria comprada"
    else:
        production_markers = {
            "packaging",
            "labor",
            "energy",
            "outsourced",
            "variable_indirect",
            "fixed_allocation",
        }
        has_production_scope = any(c["code"] in production_markers for c in categories)
        production_complete = (
            has_production_scope
            and all(c["state"] == "valued" for c in categories)
            and completeness == "complete"
        )
        acquisition_complete = False
        if production_complete:
            scope_label = "Custo total de produção completo"
            margin_label = "Margem bruta"
            completeness_label = "Custo total de produção completo"
            hint = "Todas as categorias exigidas pela política estão valorizadas."
            comparison_scope_label = "Produção completa"
        elif ingredients_complete:
            scope_label = "Custo de ingredientes completo"
            margin_label = "Margem sobre o custo conhecido (ingredientes)"
            completeness_label = "Custo de ingredientes completo"
            hint = (
                "O total monetário atual cobre apenas as categorias valorizadas. "
                "Embalagem, mão de obra, energia e indiretos da política só entram quando configurados."
            )
            comparison_scope_label = "Ingredientes — demais custos de produção não configurados"
        else:
            scope_label = "Custo de ingredientes parcial"
            margin_label = "Margem sobre o custo conhecido (parcial)"
            completeness_label = "Custo de ingredientes parcial"
            hint = (
                "O total monetário atual cobre apenas as categorias valorizadas. "
                "Embalagem, mão de obra, energia e indiretos da política só entram quando configurados."
            )
            comparison_scope_label = "Ingredientes parciais"

    excluded = [c for c in categories if c["state"] in {"not_configured", "absent", "partial"}]
    included = [c for c in categories if c["state"] == "valued"]

    return {
        "mode": "purchased" if purchased else "produced",
        "scope_label": scope_label,
        "completeness_label": completeness_label,
        "margin_label": margin_label,
        "comparison_scope_label": comparison_scope_label,
        "ingredients_complete": ingredients_complete,
        "acquisition_complete": acquisition_complete if purchased else False,
        "production_complete": production_complete,
        "price_definitive_allowed": (
            acquisition_complete if purchased else production_complete
        ),
        "included_categories": included,
        "excluded_categories": excluded,
        "categories": categories,
        "hint": hint,
    }



def analytics_from_components(components: list[dict], *, completeness: str, supply_mode: str | None = None) -> dict:
    """Agregados para gráficos gerenciais. Ausência não vira zero."""
    valued = [c for c in components if c.get("amount") is not None]
    missing = [c for c in components if c.get("price_missing") or c.get("amount") is None]
    known_total = sum(Decimal(c["amount"]) for c in valued) if valued else None
    by_category: dict[str, dict] = {}
    for c in components:
        key = c.get("category") or "other"
        bucket = by_category.setdefault(
            key,
            {
                "category": key,
                "category_label": c.get("category_label") or CATEGORY_LABEL.get(key, key),
                "amount": None,
                "missing_count": 0,
                "valued_count": 0,
                "items": [],
            },
        )
        bucket["items"].append(c["display_name"])
        if c.get("amount") is None:
            bucket["missing_count"] += 1
        else:
            bucket["valued_count"] += 1
            current = Decimal("0") if bucket["amount"] is None else Decimal(bucket["amount"])
            bucket["amount"] = format(current + Decimal(c["amount"]), "f")
    category_bars = []
    for bucket in by_category.values():
        share = None
        if known_total and known_total > ZERO and bucket["amount"] is not None:
            share = format(quantize_percent(Decimal(bucket["amount"]) / known_total * Decimal("100")), "f")
        category_bars.append(
            {
                **bucket,
                "share_of_known_percent": share,
                "state": "ausente"
                if bucket["valued_count"] == 0
                else ("parcial" if bucket["missing_count"] else "confirmado"),
            }
        )
    category_bars.sort(
        key=lambda row: Decimal(row["amount"]) if row["amount"] is not None else Decimal("-1"),
        reverse=True,
    )
    # Cascata só se houver progressão cumulativa real (mais de uma categoria valorizada)
    valued_cats = [b for b in category_bars if b["amount"] is not None]
    use_waterfall = len(valued_cats) > 1
    waterfall = []
    running = Decimal("0")
    for bar in category_bars:
        if bar["amount"] is None:
            waterfall.append(
                {
                    "label": bar["category_label"],
                    "amount": None,
                    "running_total": None if known_total is None else format(running, "f"),
                    "state": "ausente",
                }
            )
            continue
        delta = Decimal(bar["amount"])
        running += delta
        waterfall.append(
            {
                "label": bar["category_label"],
                "amount": bar["amount"],
                "running_total": format(running, "f"),
                "state": bar["state"],
            }
        )
    if known_total is not None:
        waterfall.append(
            {
                "label": "Custo conhecido" if completeness != "complete" or len(valued_cats) == 1 else "Custo total",
                "amount": format(known_total, "f"),
                "running_total": format(known_total, "f"),
                "state": "total",
            }
        )
    ingredient_only = set(by_category.keys()) <= {"ingredient"} or (
        len(valued_cats) == 1 and valued_cats[0]["category"] == "ingredient"
    )
    purchased = (supply_mode or "produced") == "purchased"
    if purchased:
        composition_title = (
            "Composição do custo de aquisição"
            if completeness == "complete"
            else "Composição conhecida do custo de aquisição (parcial)"
        )
        formation_title = "Formação do custo por categoria"
        share_complete = "Participação sobre o custo de aquisição conhecido"
    elif completeness != "complete":
        composition_title = "Composição conhecida do custo parcial"
        formation_title = "Formação do custo por categoria"
        share_complete = "Participação sobre o custo conhecido"
    elif ingredient_only:
        composition_title = "Formação do custo de ingredientes"
        formation_title = "Formação do custo por categoria"
        share_complete = "Participação sobre o custo de ingredientes conhecido"
    else:
        composition_title = "Composição do custo"
        formation_title = "Formação do custo" if not use_waterfall else "Cascata do custo"
        share_complete = "Participação sobre o custo total conhecido"
    return {
        "composition_title": composition_title,
        "formation_title": formation_title if use_waterfall else "Formação do custo por categoria",
        "use_waterfall": use_waterfall,
        "known_total": None if known_total is None else format(known_total, "f"),
        "missing_count": len(missing),
        "valued_count": len(valued),
        "missing_names": [c.get("display_name") for c in missing if c.get("display_name")],
        "share_basis": "known_partial" if completeness != "complete" else "ingredient_or_known_total",
        "share_basis_label": (
            "Participação sobre o custo conhecido (parcial) — não é 100% do custo verdadeiro"
            if completeness != "complete"
            else share_complete
        ),
        "category_bars": category_bars,
        "waterfall": waterfall,
        "component_bars": sorted(
            [
                {
                    "id": c.get("id"),
                    "label": c.get("display_name") or c.get("category_label"),
                    "amount": c.get("amount"),
                    "share_of_known_percent": c.get("share_percent")
                    if completeness == "complete"
                    else (
                        None
                        if c.get("amount") is None or known_total in (None, ZERO)
                        else format(
                            quantize_percent(Decimal(c["amount"]) / known_total * Decimal("100")),
                            "f",
                        )
                    ),
                    "state": "ausente" if c.get("price_missing") or c.get("amount") is None else "confirmado",
                    "quality_label": c.get("quality_label"),
                }
                for c in components
            ],
            key=lambda row: Decimal(row["amount"]) if row["amount"] is not None else Decimal("-1"),
            reverse=True,
        ),
    }


def markup_policy_contract() -> dict:
    return {
        "supported_precedence": True,
        "desired_precedence": ["product", "family", "organization"],
        "current_scope": "product_family_organization",
        "deferred_scopes": ["channel", "establishment"],
        "note": (
            "Resolução efetiva: produto → família → organização. "
            "Canal e estabelecimento ficam para extensão posterior. "
            "Política de markup e de margem são entradas exclusivas (uma por registro)."
        ),
    }
