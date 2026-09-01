"""Casos de uso HTTP. Backend é a autoridade das fórmulas."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.costing_pricing.compare import compare_calculations, composition
from app.modules.costing_pricing.constants import (
    ALGORITHM_NAME,
    ALGORITHM_VERSION,
    CATEGORIES,
    CHANNELS,
    FISCAL_DISCLAIMER,
    PRICE_CRITERIA,
    SIMULATION_KINDS,
)
from app.modules.costing_pricing.engine import calculate
from app.modules.costing_pricing.formulas import (
    price_from_contribution,
    price_from_gross_margin,
    price_from_markup_factor,
    price_from_markup_percent,
    reverse_metrics,
)
from app.modules.costing_pricing.models import (
    CostingAssumption,
    CostingCalculation,
    CostingCommand,
    CostingComponent,
    CostingGap,
    CostingInvalidation,
    CostingPolicy,
    CostingPolicyVersion,
    PracticedPrice,
    PricingDecision,
    PricingEconomicAudit,
    PricingMarkupPolicy,
    PricingSimulation,
    PricingSimulationComponent,
)
from app.modules.identity_organization.authorization import (
    PERMISSION_COSTING_ASSUMPTION_MANAGE,
    PERMISSION_COSTING_CALCULATE_ACTUAL,
    PERMISSION_COSTING_CALCULATE_PLANNED,
    PERMISSION_COSTING_POLICY_MANAGE,
    PERMISSION_COSTING_READ,
    PERMISSION_PRICING_AUDIT_READ,
    PERMISSION_PRICING_POLICY_MANAGE,
    PERMISSION_PRICING_PUBLISH,
    PERMISSION_PRICING_REVIEW,
    PERMISSION_PRICING_SIMULATION_MANAGE,
    Principal,
    require_permission,
)
from app.modules.identity_organization.models import AuditEvent
from app.modules.production_planning.errors import (
    ConcurrencyError,
    IdempotencyConflictError,
    InvalidStateError,
    ValidationError,
)


def _org(principal: Principal) -> UUID:
    if principal.selected is None:
        raise ValidationError("organizacao_nao_selecionada")
    return principal.selected.organization_id


def _digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _replay(session: Session, organization_id, key, command: str, payload: dict):
    if key is None:
        return None
    row = session.scalar(
        select(CostingCommand).where(
            CostingCommand.organization_id == organization_id,
            CostingCommand.idempotency_key == key,
        )
    )
    if row is None:
        return None
    if row.command != command or row.payload_digest != _digest(payload):
        raise IdempotencyConflictError("idempotencia_conflito")
    return row


def _store_command(session, organization_id, key, command, payload, resource_type, resource_id, actor_user_id):
    if key is None:
        return
    session.add(
        CostingCommand(
            organization_id=organization_id,
            idempotency_key=key,
            command=command,
            payload_digest=_digest(payload),
            resource_type=resource_type,
            resource_id=resource_id,
            actor_user_id=actor_user_id,
        )
    )


def _policy(session, organization_id, policy_id) -> CostingPolicy:
    row = session.get(CostingPolicy, policy_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError("recurso_nao_encontrado")
    return row


def _version(session, organization_id, version_id) -> CostingPolicyVersion:
    row = session.get(CostingPolicyVersion, version_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError("recurso_nao_encontrado")
    return row


def _calc(session, organization_id, calc_id) -> CostingCalculation:
    row = session.get(CostingCalculation, calc_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError("recurso_nao_encontrado")
    return row


def latest_version(session: Session, policy_id) -> CostingPolicyVersion | None:
    return session.scalar(
        select(CostingPolicyVersion)
        .where(CostingPolicyVersion.costing_policy_id == policy_id)
        .order_by(CostingPolicyVersion.version_number.desc())
    )


def create_policy(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_COSTING_POLICY_MANAGE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "costing.policy.create", body)
    if replay is not None:
        return _policy(session, org, replay.resource_id)
    criterion = body.get("price_criterion") or "latest_observed"
    if criterion not in PRICE_CRITERIA:
        raise ValidationError("contrato_invalido")
    categories = body.get("enabled_categories") or list(CATEGORIES)
    policy = CostingPolicy(
        organization_id=org,
        code=body["code"],
        display_name=body.get("display_name") or body["code"],
        created_by_user_id=principal.user_id,
    )
    session.add(policy)
    session.flush()
    version = CostingPolicyVersion(
        organization_id=org,
        costing_policy_id=policy.id,
        version_number=1,
        status="draft",
        currency=body.get("currency") or "BRL",
        timezone=body.get("timezone") or "America/Sao_Paulo",
        price_criterion=criterion,
        use_gross_quantity=bool(body.get("use_gross_quantity", True)),
        include_return=bool(body.get("include_return", True)),
        include_waste=bool(body.get("include_waste", True)),
        include_leftover=bool(body.get("include_leftover", False)),
        include_scrap=bool(body.get("include_scrap", True)),
        use_sellable_yield=bool(body.get("use_sellable_yield", True)),
        enabled_categories=categories,
        allocation_notes=body.get("allocation_notes"),
        presentation_decimals=int(body.get("presentation_decimals") or 2),
        justification=body.get("justification"),
        algorithm_name=ALGORITHM_NAME,
        algorithm_version=ALGORITHM_VERSION,
        effective_from=_parse_time(body["effective_from"]),
        created_by_user_id=principal.user_id,
    )
    session.add(version)
    session.flush()
    _store_command(
        session, org, idempotency_key, "costing.policy.create", body, "costing_policy", policy.id, principal.user_id
    )
    session.add(
        AuditEvent(
            organization_id=org,
            actor_user_id=principal.user_id,
            event_type="costing.policy.created",
            aggregate_type="costing_policy",
            aggregate_id=policy.id,
            payload={"policy_id": str(policy.id)},
        )
    )
    return policy


def publish_policy(session: Session, principal: Principal, policy_id, *, expected_version, idempotency_key):
    require_permission(principal, PERMISSION_COSTING_POLICY_MANAGE)
    org = _org(principal)
    payload = {"policy_id": str(policy_id)}
    replay = _replay(session, org, idempotency_key, "costing.policy.publish", payload)
    if replay is not None:
        return _policy(session, org, replay.resource_id)
    policy = _policy(session, org, policy_id)
    if expected_version is not None and int(policy.row_version or 1) != expected_version:
        raise ConcurrencyError("versao_conflito")
    version = latest_version(session, policy.id)
    if version is None or version.status != "draft":
        raise InvalidStateError("transicao_invalida")
    version.status = "published"
    policy.status = "published"
    policy.row_version = int(policy.row_version or 1) + 1
    _store_command(
        session, org, idempotency_key, "costing.policy.publish", payload, "costing_policy", policy.id, principal.user_id
    )
    return policy


def add_assumption(session: Session, principal: Principal, version_id, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_COSTING_ASSUMPTION_MANAGE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "costing.assumption.create", body)
    if replay is not None:
        return session.get(CostingAssumption, replay.resource_id)
    version = _version(session, org, version_id)
    if version.status == "published":
        raise InvalidStateError("published_frozen")
    row = CostingAssumption(
        organization_id=org,
        costing_policy_version_id=version.id,
        category=body["category"],
        code=body["code"],
        amount=Decimal(str(body["amount"])),
        unit_code=body.get("unit_code") or "BRL",
        currency=body.get("currency") or version.currency,
        channel=body.get("channel"),
        nature=body.get("nature") or "indirect",
        behavior=body.get("behavior") or "fixed",
        quality="manual_assumption",
        reason=body["reason"],
        effective_from=_parse_time(body["effective_from"]),
        effective_to=None if not body.get("effective_to") else _parse_time(body["effective_to"]),
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    _store_command(
        session, org, idempotency_key, "costing.assumption.create", body, "costing_assumption", row.id, principal.user_id
    )
    return row


def run_calculation(session: Session, principal: Principal, body: dict, *, idempotency_key):
    kind = body["kind"]
    permission = (
        PERMISSION_COSTING_CALCULATE_ACTUAL if kind == "actual" else PERMISSION_COSTING_CALCULATE_PLANNED
    )
    require_permission(principal, permission)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "costing.calculate", body)
    if replay is not None:
        return _calc(session, org, replay.resource_id)
    version = _version(session, org, UUID(body["policy_version_id"]))
    calc = calculate(
        session,
        policy=version,
        kind=kind,
        actor_user_id=principal.user_id,
        valuation_at=_parse_time(body["valuation_at"]),
        formulation_version_id=None if not body.get("formulation_version_id") else UUID(body["formulation_version_id"]),
        scale_calculation_id=None if not body.get("scale_calculation_id") else UUID(body["scale_calculation_id"]),
        production_order_id=None if not body.get("production_order_id") else UUID(body["production_order_id"]),
        production_batch_id=None if not body.get("production_batch_id") else UUID(body["production_batch_id"]),
        explicit_item_id=None if not body.get("supplier_item_id") else UUID(body["supplier_item_id"]),
        planned_batches=body.get("planned_batches"),
    )
    _store_command(
        session, org, idempotency_key, "costing.calculate", body, "costing_calculation", calc.id, principal.user_id
    )
    return calc


def invalidate_calculation(session: Session, principal: Principal, calc_id, reason: str, *, idempotency_key):
    require_permission(principal, PERMISSION_COSTING_CALCULATE_PLANNED)
    org = _org(principal)
    payload = {"id": str(calc_id), "reason": reason}
    replay = _replay(session, org, idempotency_key, "costing.invalidate", payload)
    if replay is not None:
        return _calc(session, org, replay.resource_id)
    calc = _calc(session, org, calc_id)
    session.add(
        CostingInvalidation(
            organization_id=org,
            costing_calculation_id=calc.id,
            reason=reason,
            created_by_user_id=principal.user_id,
        )
    )
    _store_command(
        session, org, idempotency_key, "costing.invalidate", payload, "costing_calculation", calc.id, principal.user_id
    )
    return calc


def simulate_price(session: Session, principal: Principal, calc_id, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_PRICING_SIMULATION_MANAGE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "pricing.simulate", body)
    if replay is not None:
        return session.get(PricingSimulation, replay.resource_id)
    calc = _calc(session, org, calc_id)
    if calc.total_amount is None:
        raise ValidationError("contrato_invalido")
    kind = body["kind"]
    if kind not in SIMULATION_KINDS:
        raise ValidationError("contrato_invalido")
    channel = body.get("channel") or "own_counter"
    if channel not in CHANNELS:
        raise ValidationError("contrato_invalido")
    warning = None
    if calc.completeness != "complete":
        warning = "Simulação sobre cálculo parcial. Publicação exige confirmação reforçada."
    cost_base = calc.sellable_unit_amount or calc.total_amount
    var_rate = Decimal(str(body.get("variable_expense_rate") or "0"))
    suggested = None
    extras = {}
    if kind == "markup_factor":
        suggested = price_from_markup_factor(cost_base, body["factor"])
    elif kind == "markup_percent":
        suggested = price_from_markup_percent(cost_base, body["percent"])
    elif kind == "gross_margin":
        suggested = price_from_gross_margin(cost_base, body["target_rate"])
    elif kind == "contribution_margin":
        suggested = price_from_contribution(cost_base, var_rate, body["target_rate"])
    elif kind == "reverse":
        extras = reverse_metrics(
            Decimal(str(body["price"])),
            cost_base,
            variable_product=body.get("variable_product"),
            variable_selling=body.get("variable_selling"),
            fixed_allocated=body.get("fixed_allocated"),
        )
        extras = {
            key: format(value, "f") if isinstance(value, Decimal) else value
            for key, value in extras.items()
        }
        suggested = Decimal(str(body["price"]))
    snapshot = {
        "kind": kind,
        "cost_base": format(cost_base, "f"),
        "channel": channel,
        "disclaimer": FISCAL_DISCLAIMER,
        **extras,
    }
    row = PricingSimulation(
        organization_id=org,
        costing_calculation_id=calc.id,
        kind=kind,
        channel=channel,
        suggested_price=suggested,
        warning=warning,
        snapshot=snapshot,
        content_hash=_digest(snapshot),
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    for code, amount in (
        ("suggested_price", suggested),
        ("variable_expense_rate", var_rate),
    ):
        session.add(
            PricingSimulationComponent(
                organization_id=org,
                pricing_simulation_id=row.id,
                code=code,
                amount=amount if code == "suggested_price" else None,
                rate=amount if code != "suggested_price" else None,
                note=FISCAL_DISCLAIMER if "tax" in body or body.get("called_tax") else None,
            )
        )
    _store_command(
        session, org, idempotency_key, "pricing.simulate", body, "pricing_simulation", row.id, principal.user_id
    )
    return row


def create_practiced_price(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_PRICING_REVIEW)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "pricing.practiced.create", body)
    if replay is not None:
        return session.get(PracticedPrice, replay.resource_id)
    qty = body.get("sale_basis_quantity")
    unit = body.get("sale_basis_unit_id")
    if (qty is None) ^ (unit is None):
        raise ValidationError("contrato_invalido")
    if qty is not None and Decimal(str(qty)) <= 0:
        raise ValidationError("contrato_invalido")
    row = PracticedPrice(
        organization_id=org,
        establishment_id=None if not body.get("establishment_id") else UUID(body["establishment_id"]),
        technical_product_id=UUID(body["technical_product_id"]),
        channel=body["channel"],
        currency=body.get("currency") or "BRL",
        amount=Decimal(str(body["amount"])),
        sale_basis_quantity=None if qty is None else Decimal(str(qty)),
        sale_basis_unit_id=None if unit is None else UUID(str(unit)),
        valid_from=_parse_time(body["valid_from"]),
        valid_to=None if not body.get("valid_to") else _parse_time(body["valid_to"]),
        pricing_simulation_id=None if not body.get("simulation_id") else UUID(body["simulation_id"]),
        status="draft",
        justification=body.get("justification"),
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    _store_command(
        session, org, idempotency_key, "pricing.practiced.create", body, "practiced_price", row.id, principal.user_id
    )
    return row


def decide_price(session: Session, principal: Principal, price_id, body: dict, *, expected_version, idempotency_key):
    org = _org(principal)
    payload = {"id": str(price_id), **body}
    replay = _replay(session, org, idempotency_key, "pricing.decide", payload)
    if replay is not None:
        return session.get(PracticedPrice, replay.resource_id)
    row = session.get(PracticedPrice, price_id)
    if row is None or row.organization_id != org:
        raise ValidationError("recurso_nao_encontrado")
    if expected_version is not None and int(row.row_version or 1) != expected_version:
        raise ConcurrencyError("versao_conflito")
    decision = body["decision"]
    before = {
        "status": row.status,
        "amount": format(row.amount, "f"),
        "sale_basis_quantity": None if row.sale_basis_quantity is None else format(row.sale_basis_quantity, "f"),
        "sale_basis_unit_id": None if row.sale_basis_unit_id is None else str(row.sale_basis_unit_id),
        "valid_from": row.valid_from.isoformat() if row.valid_from else None,
        "valid_to": row.valid_to.isoformat() if row.valid_to else None,
    }
    superseded_ids: list[str] = []
    if decision == "publish":
        require_permission(principal, PERMISSION_PRICING_PUBLISH)
        if row.status not in {"draft", "approved"}:
            raise InvalidStateError("transicao_invalida")
        if row.sale_basis_quantity is None or row.sale_basis_unit_id is None:
            raise ValidationError("sale_basis_obrigatoria")
        if row.pricing_simulation_id:
            simulation = session.get(PricingSimulation, row.pricing_simulation_id)
            if simulation is not None and simulation.warning and not body.get("reinforced_confirmation"):
                raise ValidationError("confirmacao_reforcada_obrigatoria")
        # Append-only succession: close other active prices same context
        siblings = list(
            session.scalars(
                select(PracticedPrice).where(
                    PracticedPrice.organization_id == org,
                    PracticedPrice.technical_product_id == row.technical_product_id,
                    PracticedPrice.channel == row.channel,
                    PracticedPrice.id != row.id,
                    PracticedPrice.status.in_(("active", "published", "approved")),
                )
            )
        )
        active_siblings = [
            sib
            for sib in siblings
            if sib.establishment_id == row.establishment_id and sib.status in {"active", "published"}
        ]
        # Optimistic concurrency: UI passa o vigente conhecido ao abrir o modal.
        if "expected_active_price_id" in body or "expected_active_row_version" in body:
            expected_id = body.get("expected_active_price_id")
            expected_rv = body.get("expected_active_row_version")
            if expected_id in (None, ""):
                if active_siblings:
                    raise ConcurrencyError("versao_conflito")
            else:
                match = next((s for s in active_siblings if str(s.id) == str(expected_id)), None)
                if match is None:
                    raise ConcurrencyError("versao_conflito")
                if expected_rv is not None and int(match.row_version or 1) != int(expected_rv):
                    raise ConcurrencyError("versao_conflito")
        for sib in siblings:
            if sib.establishment_id != row.establishment_id:
                continue
            if sib.valid_to is None or sib.valid_to > row.valid_from:
                sib.valid_to = row.valid_from
            if sib.status in {"active", "published"}:
                sib.status = "retired"
                sib.row_version = int(sib.row_version or 1) + 1
                superseded_ids.append(str(sib.id))
        row.status = "active"
    elif decision == "approve":
        require_permission(principal, PERMISSION_PRICING_REVIEW)
        row.status = "approved"
    elif decision == "retire":
        require_permission(principal, PERMISSION_PRICING_PUBLISH)
        row.status = "retired"
    elif decision == "cancel":
        require_permission(principal, PERMISSION_PRICING_REVIEW)
        row.status = "cancelled"
    else:
        raise ValidationError("contrato_invalido")
    row.row_version = int(row.row_version or 1) + 1
    after = {
        "status": row.status,
        "amount": format(row.amount, "f"),
        "sale_basis_quantity": None if row.sale_basis_quantity is None else format(row.sale_basis_quantity, "f"),
        "sale_basis_unit_id": None if row.sale_basis_unit_id is None else str(row.sale_basis_unit_id),
        "valid_from": row.valid_from.isoformat() if row.valid_from else None,
        "valid_to": row.valid_to.isoformat() if row.valid_to else None,
        "superseded_ids": superseded_ids,
    }
    memory = {
        "decision": decision,
        "currency": row.currency,
        "channel": row.channel,
        "technical_product_id": str(row.technical_product_id),
    }
    session.add(
        PricingDecision(
            organization_id=org,
            practiced_price_id=row.id,
            decision=decision,
            notes=body.get("notes"),
            snapshot={"before": before, "after": after, "memory": memory},
            idempotency_key=idempotency_key,
            created_by_user_id=principal.user_id,
        )
    )
    session.add(
        PricingEconomicAudit(
            organization_id=org,
            operation=f"pricing.decide.{decision}",
            resource_type="practiced_price",
            resource_id=row.id,
            actor_user_id=principal.user_id,
            idempotency_key=idempotency_key,
            before_state=before,
            after_state=after,
            memory=memory,
            justification=body.get("notes"),
        )
    )
    _store_command(
        session, org, idempotency_key, "pricing.decide", payload, "practiced_price", row.id, principal.user_id
    )
    return row


def list_policies(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_COSTING_READ)
    return list(session.scalars(select(CostingPolicy).where(CostingPolicy.organization_id == _org(principal))))


def invalidated_ids(session: Session, organization_id) -> set:
    return set(
        session.scalars(
            select(CostingInvalidation.costing_calculation_id).where(
                CostingInvalidation.organization_id == organization_id
            )
        )
    )


def list_calculations(session: Session, principal: Principal, kind: str | None = None):
    require_permission(principal, PERMISSION_COSTING_READ)
    stmt = select(CostingCalculation).where(CostingCalculation.organization_id == _org(principal))
    if kind:
        stmt = stmt.where(CostingCalculation.kind == kind)
    return list(session.scalars(stmt.order_by(CostingCalculation.created_at.desc())))


def list_simulations(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_COSTING_READ)
    return list(
        session.scalars(select(PricingSimulation).where(PricingSimulation.organization_id == _org(principal)))
    )


def list_prices(session: Session, principal: Principal):
    require_permission(principal, PERMISSION_COSTING_READ)
    return list(session.scalars(select(PracticedPrice).where(PracticedPrice.organization_id == _org(principal))))


def list_prices_enriched(session: Session, principal: Principal) -> list[dict]:
    """Authoritative practiced list with sale_basis + comparison + effective policy."""
    from app.modules.costing_http.serialize import price_out
    from app.modules.costing_pricing.comparison import build_comparison, sale_basis_payload
    from app.modules.costing_pricing.policy_resolve import derive_from_policy, resolve_markup_policy
    from app.modules.formula_lab.models import TechnicalProduct
    from app.modules.ingredient_catalog.models import MeasurementUnit

    require_permission(principal, PERMISSION_COSTING_READ)
    org = _org(principal)
    rows = list(session.scalars(select(PracticedPrice).where(PracticedPrice.organization_id == org)))
    product_ids = {r.technical_product_id for r in rows}
    products = {
        p.id: p
        for p in session.scalars(
            select(TechnicalProduct).where(
                TechnicalProduct.organization_id == org,
                TechnicalProduct.id.in_(product_ids),
            )
        )
    } if product_ids else {}
    unit_ids = {r.sale_basis_unit_id for r in rows if r.sale_basis_unit_id}
    unit_ids |= {p.sale_unit_id for p in products.values() if p.sale_unit_id}
    unit_ids |= {p.net_content_unit_id for p in products.values() if p.net_content_unit_id}
    units = {}
    if unit_ids:
        units = {
            u.id: u
            for u in session.scalars(select(MeasurementUnit).where(MeasurementUnit.id.in_(unit_ids)))
        }
    calcs = list(
        session.scalars(
            select(CostingCalculation).where(
                CostingCalculation.organization_id == org,
                CostingCalculation.kind == "planned",
            )
        )
    )
    calc_by_product: dict = {}
    for calc in calcs:
        if calc.technical_product_id is None:
            continue
        prev = calc_by_product.get(calc.technical_product_id)
        if prev is None or str(calc.created_at or "") > str(prev.created_at or ""):
            calc_by_product[calc.technical_product_id] = calc

    items: list[dict] = []
    for row in rows:
        unit = units.get(row.sale_basis_unit_id) if row.sale_basis_unit_id else None
        basis = sale_basis_payload(
            quantity=row.sale_basis_quantity,
            unit_id=row.sale_basis_unit_id,
            unit_code=None if unit is None else unit.code,
            unit_display_name=None if unit is None else unit.name,
        )
        calc = calc_by_product.get(row.technical_product_id)
        product = products.get(row.technical_product_id)
        cost_unit_id = None if product is None else product.sale_unit_id
        cost_unit = units.get(cost_unit_id) if cost_unit_id else None
        cost_qty = Decimal("1") if cost_unit_id is not None and calc and calc.sellable_unit_amount is not None else None
        pkg_unit = None
        if product and product.net_content_unit_id:
            pkg_unit = units.get(product.net_content_unit_id)
        comparison = build_comparison(
            price_amount=row.amount,
            price_currency=row.currency,
            sale_basis=basis,
            cost_amount=None if calc is None else calc.sellable_unit_amount,
            cost_currency=None if calc is None else calc.currency,
            cost_basis_quantity=cost_qty,
            cost_basis_unit_id=cost_unit_id,
            cost_partial=False if calc is None else calc.completeness != "complete",
            price_definitive_allowed=False if calc is None else calc.completeness == "complete",
            sale_unit_dimension=None if unit is None else unit.dimension,
            sale_unit_si_factor=None if unit is None else unit.si_factor,
            cost_unit_dimension=None if cost_unit is None else cost_unit.dimension,
            cost_unit_si_factor=None if cost_unit is None else cost_unit.si_factor,
            package_content_quantity=None if product is None else product.net_content,
            package_content_unit_id=None if product is None else product.net_content_unit_id,
            package_content_dimension=None if pkg_unit is None else pkg_unit.dimension,
            package_content_si_factor=None if pkg_unit is None else pkg_unit.si_factor,
        )
        resolved = resolve_markup_policy(
            session,
            organization_id=org,
            technical_product_id=row.technical_product_id,
            at=row.valid_from,
        )
        policy_calc = None
        eff = resolved.get("effective")
        if (
            eff
            and comparison.get("allowed")
            and calc
            and calc.sellable_unit_amount is not None
            and calc.completeness == "complete"
        ):
            try:
                policy_calc = derive_from_policy(
                    kind=eff["kind"],
                    value=Decimal(str(eff["value"])),
                    cost=Decimal(str(calc.sellable_unit_amount)),
                    places=int(eff.get("commercial_rounding_places") or 2),
                )
            except ValueError:
                policy_calc = None
        payload = price_out(row, unit_row=unit, comparison=comparison)
        payload["effective_markup_policy"] = eff
        payload["effective_markup_policy_resolution"] = {
            "origin_level": resolved.get("origin_level"),
            "replaced": resolved.get("replaced") or [],
            "reason": resolved.get("reason"),
            "reason_label": resolved.get("reason_label"),
            "deferred_scopes": resolved.get("deferred_scopes"),
            "from_policy_calculation": policy_calc,
        }
        if eff is None:
            payload["effective_markup_policy_note"] = resolved.get("reason_label") or (
                "Nenhuma política de markup/margem ativa resolvida para este preço."
            )
        else:
            payload["effective_markup_policy_note"] = (
                f"Política efetiva no nível {resolved.get('origin_level')} ({eff.get('code')})."
            )
        items.append(payload)
    return items


def list_markup_policies(session: Session, principal: Principal) -> list[dict]:
    from app.modules.costing_pricing.policy_resolve import policy_out

    require_permission(principal, PERMISSION_COSTING_READ)
    rows = list(
        session.scalars(
            select(PricingMarkupPolicy)
            .where(PricingMarkupPolicy.organization_id == _org(principal))
            .order_by(PricingMarkupPolicy.scope_level, PricingMarkupPolicy.code)
        )
    )
    return [policy_out(r) for r in rows]


def create_markup_policy(session: Session, principal: Principal, body: dict, *, idempotency_key):
    from app.modules.costing_pricing.policy_resolve import policy_out

    require_permission(principal, PERMISSION_PRICING_POLICY_MANAGE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "pricing.markup_policy.create", body)
    if replay is not None:
        return policy_out(session.get(PricingMarkupPolicy, replay.resource_id))
    kind = body["kind"]
    if kind not in {"markup_factor", "margin_rate"}:
        raise ValidationError("contrato_invalido")
    scope = body["scope_level"]
    if scope not in {"organization", "family", "product"}:
        raise ValidationError("contrato_invalido")
    if scope == "channel":
        raise ValidationError("escopo_canal_nao_suportado")
    family_id = None if not body.get("product_family_id") else UUID(str(body["product_family_id"]))
    product_id = None if not body.get("technical_product_id") else UUID(str(body["technical_product_id"]))
    if scope == "organization" and (family_id or product_id):
        raise ValidationError("contrato_invalido")
    if scope == "family" and family_id is None:
        raise ValidationError("contrato_invalido")
    if scope == "product" and product_id is None:
        raise ValidationError("contrato_invalido")
    value = Decimal(str(body["value"]))
    if value <= 0:
        raise ValidationError("contrato_invalido")
    if kind == "margin_rate" and value >= 1:
        raise ValidationError("contrato_invalido")
    row = PricingMarkupPolicy(
        organization_id=org,
        code=body["code"],
        display_name=body.get("display_name") or body["code"],
        kind=kind,
        value=value,
        scope_level=scope,
        product_family_id=family_id,
        technical_product_id=product_id,
        channel=None,
        establishment_id=None,
        priority=int(body.get("priority") or 100),
        status="draft",
        currency=body.get("currency") or "BRL",
        commercial_rounding_places=int(body.get("commercial_rounding_places") or 2),
        valid_from=_parse_time(body["valid_from"]),
        valid_to=None if not body.get("valid_to") else _parse_time(body["valid_to"]),
        justification=body.get("justification"),
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    session.add(
        PricingEconomicAudit(
            organization_id=org,
            operation="pricing.markup_policy.create",
            resource_type="pricing_markup_policy",
            resource_id=row.id,
            actor_user_id=principal.user_id,
            idempotency_key=idempotency_key,
            before_state={},
            after_state=policy_out(row),
            memory={"kind": kind, "scope_level": scope},
            justification=body.get("justification"),
        )
    )
    _store_command(
        session,
        org,
        idempotency_key,
        "pricing.markup_policy.create",
        body,
        "pricing_markup_policy",
        row.id,
        principal.user_id,
    )
    return policy_out(row)


def activate_markup_policy(
    session: Session, principal: Principal, policy_id, *, expected_version, idempotency_key, notes: str | None = None
):
    from app.modules.costing_pricing.policy_resolve import policy_out

    require_permission(principal, PERMISSION_PRICING_POLICY_MANAGE)
    org = _org(principal)
    payload = {"id": str(policy_id), "decision": "activate", "notes": notes}
    replay = _replay(session, org, idempotency_key, "pricing.markup_policy.activate", payload)
    if replay is not None:
        return policy_out(session.get(PricingMarkupPolicy, replay.resource_id))
    row = session.get(PricingMarkupPolicy, policy_id)
    if row is None or row.organization_id != org:
        raise ValidationError("recurso_nao_encontrado")
    if expected_version is not None and int(row.row_version or 1) != expected_version:
        raise ConcurrencyError("versao_conflito")
    if row.status not in {"draft", "retired"}:
        raise InvalidStateError("transicao_invalida")
    # Application-level overlap check for same scope key
    rivals = list(
        session.scalars(
            select(PricingMarkupPolicy).where(
                PricingMarkupPolicy.organization_id == org,
                PricingMarkupPolicy.status == "active",
                PricingMarkupPolicy.scope_level == row.scope_level,
                PricingMarkupPolicy.id != row.id,
            )
        )
    )
    for rival in rivals:
        same_key = False
        if row.scope_level == "organization":
            same_key = True
        elif row.scope_level == "family":
            same_key = rival.product_family_id == row.product_family_id
        elif row.scope_level == "product":
            same_key = rival.technical_product_id == row.technical_product_id
        if not same_key:
            continue
        # overlap if open-ended or intervals intersect
        r_from, r_to = rival.valid_from, rival.valid_to
        n_from, n_to = row.valid_from, row.valid_to
        ends_before = r_to is not None and r_to <= n_from
        starts_after = n_to is not None and n_to <= r_from
        if not ends_before and not starts_after:
            raise ValidationError("politica_vigencia_conflito")
    before = policy_out(row)
    row.status = "active"
    row.row_version = int(row.row_version or 1) + 1
    session.add(
        PricingEconomicAudit(
            organization_id=org,
            operation="pricing.markup_policy.activate",
            resource_type="pricing_markup_policy",
            resource_id=row.id,
            actor_user_id=principal.user_id,
            idempotency_key=idempotency_key,
            before_state=before,
            after_state=policy_out(row),
            memory={},
            justification=notes,
        )
    )
    _store_command(
        session,
        org,
        idempotency_key,
        "pricing.markup_policy.activate",
        payload,
        "pricing_markup_policy",
        row.id,
        principal.user_id,
    )
    return policy_out(row)


def retire_markup_policy(
    session: Session,
    principal: Principal,
    policy_id,
    *,
    expected_version,
    idempotency_key,
    notes: str | None = None,
    valid_to: str | None = None,
):
    from app.modules.costing_pricing.policy_resolve import policy_out

    require_permission(principal, PERMISSION_PRICING_POLICY_MANAGE)
    org = _org(principal)
    payload = {"id": str(policy_id), "decision": "retire", "notes": notes, "valid_to": valid_to}
    replay = _replay(session, org, idempotency_key, "pricing.markup_policy.retire", payload)
    if replay is not None:
        return policy_out(session.get(PricingMarkupPolicy, replay.resource_id))
    row = session.get(PricingMarkupPolicy, policy_id)
    if row is None or row.organization_id != org:
        raise ValidationError("recurso_nao_encontrado")
    if expected_version is not None and int(row.row_version or 1) != expected_version:
        raise ConcurrencyError("versao_conflito")
    if row.status not in {"active", "draft"}:
        raise InvalidStateError("transicao_invalida")
    before = policy_out(row)
    end = _parse_time(valid_to) if valid_to else datetime.now(tz=row.valid_from.tzinfo)
    if end <= row.valid_from:
        raise ValidationError("contrato_invalido")
    row.valid_to = end
    row.status = "retired"
    row.row_version = int(row.row_version or 1) + 1
    session.add(
        PricingEconomicAudit(
            organization_id=org,
            operation="pricing.markup_policy.retire",
            resource_type="pricing_markup_policy",
            resource_id=row.id,
            actor_user_id=principal.user_id,
            idempotency_key=idempotency_key,
            before_state=before,
            after_state=policy_out(row),
            memory={},
            justification=notes,
        )
    )
    _store_command(
        session,
        org,
        idempotency_key,
        "pricing.markup_policy.retire",
        payload,
        "pricing_markup_policy",
        row.id,
        principal.user_id,
    )
    return policy_out(row)


def resolve_product_markup_policy(session: Session, principal: Principal, technical_product_id) -> dict:
    require_permission(principal, PERMISSION_COSTING_READ)
    from app.modules.costing_pricing.policy_resolve import resolve_markup_policy

    return resolve_markup_policy(
        session,
        organization_id=_org(principal),
        technical_product_id=UUID(str(technical_product_id)),
    )


def list_economic_audit(session: Session, principal: Principal, *, limit: int = 50) -> list[dict]:
    require_permission(principal, PERMISSION_PRICING_AUDIT_READ)
    rows = list(
        session.scalars(
            select(PricingEconomicAudit)
            .where(PricingEconomicAudit.organization_id == _org(principal))
            .order_by(PricingEconomicAudit.created_at.desc())
            .limit(min(limit, 200))
        )
    )
    return [
        {
            "id": str(r.id),
            "operation": r.operation,
            "resource_type": r.resource_type,
            "resource_id": str(r.resource_id),
            "actor_user_id": str(r.actor_user_id),
            "idempotency_key": None if r.idempotency_key is None else str(r.idempotency_key),
            "before_state": r.before_state,
            "after_state": r.after_state,
            "memory": r.memory,
            "justification": r.justification,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def calculation_detail(session: Session, principal: Principal, calc_id) -> dict:
    require_permission(principal, PERMISSION_COSTING_READ)
    calc = _calc(session, _org(principal), calc_id)
    gaps = list(session.scalars(select(CostingGap).where(CostingGap.costing_calculation_id == calc.id)))
    from app.modules.costing_pricing.models import CostingPolicyVersion
    from app.modules.costing_pricing.presentation import (
        analytics_from_components,
        calculation_subject,
        cost_base_for_pricing,
        cost_scope_report,
        markup_policy_contract,
        price_basis_contract,
        sellable_absence_reason,
    )

    policy = session.get(CostingPolicyVersion, calc.costing_policy_version_id)
    subject = calculation_subject(session, calc)
    supply_mode = subject.get("supply_mode") or "produced"
    components = composition(session, calc)
    if supply_mode == "purchased":
        for row in components:
            if row.get("category") == "ingredient":
                row["category_label"] = "Valor de compra"
    analytics = analytics_from_components(
        components, completeness=calc.completeness, supply_mode=supply_mode
    )
    scope = cost_scope_report(
        components,
        policy=policy,
        completeness=calc.completeness,
        supply_mode=supply_mode,
    )
    cost_base = cost_base_for_pricing(calc, scope)
    return {
        "calculation": calc,
        "components": components,
        "gaps": gaps,
        "enrich": {
            "subject": subject,
            "cost_base": cost_base,
            "cost_scope": scope,
            "sellable_absence_reason": sellable_absence_reason(calc, policy),
            "markup_policy": markup_policy_contract(),
            "price_basis": price_basis_contract(),
            "analytics": analytics,
            "policy": None
            if policy is None
            else {
                "price_criterion": policy.price_criterion,
                "currency": policy.currency,
                "use_sellable_yield": policy.use_sellable_yield,
                "use_gross_quantity": policy.use_gross_quantity,
                "include_return": policy.include_return,
                "include_waste": policy.include_waste,
                "enabled_categories": list(policy.enabled_categories or []),
                "algorithm_name": policy.algorithm_name,
                "algorithm_version": policy.algorithm_version,
                "presentation_decimals": policy.presentation_decimals,
            },
            "total_is_partial": not scope.get("price_definitive_allowed", False),
        },
    }


def compare(session: Session, principal: Principal, left_id, right_id) -> dict:
    require_permission(principal, PERMISSION_COSTING_READ)
    org = _org(principal)
    return compare_calculations(_calc(session, org, left_id), _calc(session, org, right_id))
