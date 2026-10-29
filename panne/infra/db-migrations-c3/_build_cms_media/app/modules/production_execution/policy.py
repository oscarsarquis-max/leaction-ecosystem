from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.calculation_engine.precision import quantize_percent, quantize_quantity
from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_ORDER_MANAGE,
    PERMISSION_PRODUCTION_ORDER_POLICY_ADOPT,
    Principal,
)
from app.modules.production_execution.access import now, org_id, permit
from app.modules.production_execution.constants import (
    COMMAND_ADOPT_EXECUTION_POLICY,
    COMMAND_SET_EXECUTION_POLICY,
    EVENT_POLICY_ADOPTED,
    EVENT_POLICY_SET,
    POLICY_ALGORITHM,
    POLICY_ALGORITHM_VERSION,
    VERIFICATION_POLICIES,
    WEIGHING_POLICIES,
)
from app.modules.production_execution.guards import has_execution_facts
from app.modules.production_execution.models import ProductionExecutionPolicy
from app.modules.production_planning.constants import (
    ORDER_EDITABLE,
    ORDER_STATUS_ON_HOLD,
    ORDER_STATUS_RELEASED,
)
from app.modules.production_planning.errors import (
    ImmutableError,
    InvalidStateError,
    ValidationError,
)
from app.modules.production_planning.events import append_event, existing_idempotent
from app.modules.production_planning.models import ProductionOrder
from app.modules.production_planning.support import as_decimal, digest


def policy_canonical(policy: ProductionExecutionPolicy) -> dict:
    return {
        "weighing_policy": policy.weighing_policy,
        "verification_policy": policy.verification_policy,
        "absolute_tolerance": (
            None if policy.absolute_tolerance is None else format(policy.absolute_tolerance, "f")
        ),
        "percent_tolerance": (
            None if policy.percent_tolerance is None else format(policy.percent_tolerance, "f")
        ),
        "completion_tolerance": format(policy.completion_tolerance, "f"),
        "allow_short_close": policy.allow_short_close,
        "require_manual_lot": policy.require_manual_lot,
        "algorithm_code": policy.algorithm_code,
        "algorithm_version": policy.algorithm_version,
    }


def policy_hash_of(policy: ProductionExecutionPolicy) -> str:
    return digest(policy_canonical(policy))


def require_policy(session: Session, order_id: UUID) -> ProductionExecutionPolicy:
    policy = session.scalar(
        select(ProductionExecutionPolicy).where(
            ProductionExecutionPolicy.production_order_id == order_id
        )
    )
    if policy is None:
        raise ValidationError("politica_execucao_obrigatoria")
    return policy


def freeze_policy_for_release(
    session: Session, order: ProductionOrder, principal: Principal
) -> str:
    policy = require_policy(session, order.id)
    if policy.frozen_at is not None and policy.policy_hash:
        return policy.policy_hash
    digest_value = policy_hash_of(policy)
    policy.frozen_at = now()
    policy.frozen_by_user_id = principal.user_id
    policy.policy_hash = digest_value
    return digest_value


def set_execution_policy(
    session: Session,
    principal: Principal,
    *,
    order_id: UUID,
    weighing_policy: str,
    verification_policy: str,
    completion_tolerance: Decimal | int | str,
    allow_short_close: bool,
    require_manual_lot: bool = False,
    absolute_tolerance: Decimal | int | str | None = None,
    percent_tolerance: Decimal | int | str | None = None,
    idempotency_key: UUID,
) -> ProductionExecutionPolicy:
    permit(principal, PERMISSION_PRODUCTION_ORDER_MANAGE)
    organization_id = org_id(principal)
    order = session.get(ProductionOrder, order_id)
    if order is None or order.organization_id != organization_id:
        raise ValidationError("ordem inválida")
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_SET_EXECUTION_POLICY
    )
    if replay is not None:
        return require_policy(session, order.id)
    if order.status not in ORDER_EDITABLE:
        raise ImmutableError("politica_imutavel")
    if weighing_policy not in WEIGHING_POLICIES:
        raise ValidationError("politica de pesagem inválida")
    if verification_policy not in VERIFICATION_POLICIES:
        raise ValidationError("politica de conferência inválida")
    completion = quantize_percent(as_decimal(completion_tolerance, "tolerância de conclusão"))
    if completion < 0:
        raise ValidationError("tolerância de conclusão inválida")
    abs_tol = None
    if absolute_tolerance is not None:
        abs_tol = quantize_quantity(as_decimal(absolute_tolerance, "tolerância absoluta"))
        if abs_tol < 0:
            raise ValidationError("tolerância absoluta inválida")
    pct_tol = None
    if percent_tolerance is not None:
        pct_tol = quantize_percent(as_decimal(percent_tolerance, "tolerância percentual"))
        if pct_tol < 0:
            raise ValidationError("tolerância percentual inválida")
    policy = session.scalar(
        select(ProductionExecutionPolicy).where(
            ProductionExecutionPolicy.production_order_id == order.id
        )
    )
    if policy is not None and policy.frozen_at is not None:
        raise ImmutableError("politica_imutavel")
    if policy is None:
        policy = ProductionExecutionPolicy(
            organization_id=organization_id,
            establishment_id=order.establishment_id,
            production_order_id=order.id,
            created_by_user_id=principal.user_id,
        )
        session.add(policy)
    policy.weighing_policy = weighing_policy
    policy.verification_policy = verification_policy
    policy.absolute_tolerance = abs_tol
    policy.percent_tolerance = pct_tol
    policy.completion_tolerance = completion
    policy.allow_short_close = allow_short_close
    policy.require_manual_lot = require_manual_lot
    policy.algorithm_code = POLICY_ALGORITHM
    policy.algorithm_version = POLICY_ALGORITHM_VERSION
    session.flush()
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_POLICY_SET,
        command=COMMAND_SET_EXECUTION_POLICY,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={
            "policy_id": str(policy.id),
            "weighing_policy": weighing_policy,
            "verification_policy": verification_policy,
        },
        plan_id=order.plan_id,
        order_id=order.id,
    )
    return policy


def _apply_policy_fields(
    policy: ProductionExecutionPolicy,
    *,
    weighing_policy: str,
    verification_policy: str,
    completion: Decimal,
    allow_short_close: bool,
    require_manual_lot: bool,
    abs_tol: Decimal | None,
    pct_tol: Decimal | None,
) -> None:
    policy.weighing_policy = weighing_policy
    policy.verification_policy = verification_policy
    policy.absolute_tolerance = abs_tol
    policy.percent_tolerance = pct_tol
    policy.completion_tolerance = completion
    policy.allow_short_close = allow_short_close
    policy.require_manual_lot = require_manual_lot
    policy.algorithm_code = POLICY_ALGORITHM
    policy.algorithm_version = POLICY_ALGORITHM_VERSION


def _validated_policy_values(
    *,
    weighing_policy: str,
    verification_policy: str,
    completion_tolerance: Decimal | int | str,
    absolute_tolerance: Decimal | int | str | None,
    percent_tolerance: Decimal | int | str | None,
) -> tuple[Decimal, Decimal | None, Decimal | None]:
    if weighing_policy not in WEIGHING_POLICIES:
        raise ValidationError("politica de pesagem inválida")
    if verification_policy not in VERIFICATION_POLICIES:
        raise ValidationError("politica de conferência inválida")
    completion = quantize_percent(as_decimal(completion_tolerance, "tolerância de conclusão"))
    if completion < 0:
        raise ValidationError("tolerância de conclusão inválida")
    abs_tol = None
    if absolute_tolerance is not None:
        abs_tol = quantize_quantity(as_decimal(absolute_tolerance, "tolerância absoluta"))
        if abs_tol < 0:
            raise ValidationError("tolerância absoluta inválida")
    pct_tol = None
    if percent_tolerance is not None:
        pct_tol = quantize_percent(as_decimal(percent_tolerance, "tolerância percentual"))
        if pct_tol < 0:
            raise ValidationError("tolerância percentual inválida")
    return completion, abs_tol, pct_tol


def adopt_execution_policy(
    session: Session,
    principal: Principal,
    *,
    order_id: UUID,
    weighing_policy: str,
    verification_policy: str,
    completion_tolerance: Decimal | int | str,
    allow_short_close: bool,
    reason: str,
    idempotency_key: UUID,
    require_manual_lot: bool = False,
    absolute_tolerance: Decimal | int | str | None = None,
    percent_tolerance: Decimal | int | str | None = None,
    expected_row_version: int | None = None,
) -> ProductionExecutionPolicy:
    permit(principal, PERMISSION_PRODUCTION_ORDER_POLICY_ADOPT)
    organization_id = org_id(principal)
    if not reason or not reason.strip():
        raise ValidationError("motivo obrigatório")
    order = session.get(ProductionOrder, order_id)
    if order is None or order.organization_id != organization_id:
        raise ValidationError("ordem inválida")
    if expected_row_version is not None and order.row_version != expected_row_version:
        from app.modules.production_planning.errors import ConcurrencyError

        raise ConcurrencyError("versao_conflito")
    replay = existing_idempotent(
        session, organization_id, idempotency_key, COMMAND_ADOPT_EXECUTION_POLICY
    )
    if replay is not None:
        return require_policy(session, order.id)
    if order.status not in {ORDER_STATUS_RELEASED, ORDER_STATUS_ON_HOLD}:
        raise InvalidStateError("transicao_invalida")
    if has_execution_facts(session, order):
        raise InvalidStateError("adocao_bloqueada_por_fatos")
    policy = session.scalar(
        select(ProductionExecutionPolicy).where(
            ProductionExecutionPolicy.production_order_id == order.id
        )
    )
    if policy is not None and policy.frozen_at is not None and policy.policy_hash:
        raise ImmutableError("politica_ja_adotada")
    completion, abs_tol, pct_tol = _validated_policy_values(
        weighing_policy=weighing_policy,
        verification_policy=verification_policy,
        completion_tolerance=completion_tolerance,
        absolute_tolerance=absolute_tolerance,
        percent_tolerance=percent_tolerance,
    )
    if policy is None:
        policy = ProductionExecutionPolicy(
            organization_id=organization_id,
            establishment_id=order.establishment_id,
            production_order_id=order.id,
            created_by_user_id=principal.user_id,
        )
        session.add(policy)
    _apply_policy_fields(
        policy,
        weighing_policy=weighing_policy,
        verification_policy=verification_policy,
        completion=completion,
        allow_short_close=allow_short_close,
        require_manual_lot=require_manual_lot,
        abs_tol=abs_tol,
        pct_tol=pct_tol,
    )
    session.flush()
    digest_value = freeze_policy_for_release(session, order, principal)
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_POLICY_ADOPTED,
        command=COMMAND_ADOPT_EXECUTION_POLICY,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={
            "policy_id": str(policy.id),
            "reason": reason.strip(),
            "policy_hash": digest_value,
        },
        plan_id=order.plan_id,
        order_id=order.id,
    )
    return policy
