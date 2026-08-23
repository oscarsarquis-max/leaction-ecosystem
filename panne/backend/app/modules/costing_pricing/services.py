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
    PricingSimulation,
    PricingSimulationComponent,
)
from app.modules.identity_organization.authorization import (
    PERMISSION_COSTING_ASSUMPTION_MANAGE,
    PERMISSION_COSTING_CALCULATE_ACTUAL,
    PERMISSION_COSTING_CALCULATE_PLANNED,
    PERMISSION_COSTING_POLICY_MANAGE,
    PERMISSION_COSTING_READ,
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
    row = PracticedPrice(
        organization_id=org,
        establishment_id=None if not body.get("establishment_id") else UUID(body["establishment_id"]),
        technical_product_id=UUID(body["technical_product_id"]),
        channel=body["channel"],
        currency=body.get("currency") or "BRL",
        amount=Decimal(str(body["amount"])),
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
    if decision == "publish":
        require_permission(principal, PERMISSION_PRICING_PUBLISH)
        if row.status not in {"draft", "approved"}:
            raise InvalidStateError("transicao_invalida")
        if row.pricing_simulation_id:
            simulation = session.get(PricingSimulation, row.pricing_simulation_id)
            if simulation is not None and simulation.warning and not body.get("reinforced_confirmation"):
                raise ValidationError("confirmacao_reforcada_obrigatoria")
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
    session.add(
        PricingDecision(
            organization_id=org,
            practiced_price_id=row.id,
            decision=decision,
            notes=body.get("notes"),
            created_by_user_id=principal.user_id,
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


def calculation_detail(session: Session, principal: Principal, calc_id) -> dict:
    require_permission(principal, PERMISSION_COSTING_READ)
    calc = _calc(session, _org(principal), calc_id)
    gaps = list(session.scalars(select(CostingGap).where(CostingGap.costing_calculation_id == calc.id)))
    return {
        "calculation": calc,
        "components": composition(session, calc),
        "gaps": gaps,
    }


def compare(session: Session, principal: Principal, left_id, right_id) -> dict:
    require_permission(principal, PERMISSION_COSTING_READ)
    org = _org(principal)
    return compare_calculations(_calc(session, org, left_id), _calc(session, org, right_id))
