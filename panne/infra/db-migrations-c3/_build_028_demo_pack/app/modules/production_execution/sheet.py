from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_SHEET_ISSUE,
    Principal,
)
from app.modules.production_execution.access import now, org_id, permit
from app.modules.production_execution.constants import (
    COMMAND_ISSUE_SHEET,
    EVENT_SHEET_ISSUED,
    SHEET_PURPOSES,
    SHEET_TEMPLATE_VERSION,
)
from app.modules.production_execution.models import ProductionExecutionPolicy, ProductionSheetIssue
from app.modules.production_execution.policy import policy_canonical, require_policy
from app.modules.production_planning.constants import CODE_KIND_SHEET, ORDER_STATUS_CANCELLED
from app.modules.production_planning.errors import InvalidStateError, ValidationError
from app.modules.production_planning.events import append_event, existing_idempotent
from app.modules.identity_organization.models import AppUser, Establishment, Organization
from app.modules.production_planning.models import (
    ProductionBatch,
    ProductionCodeCounter,
    ProductionOrder,
    ProductionOrderMaterial,
    ProductionOrderStep,
)
from app.modules.production_planning.support import digest


def _next_issue_number(session: Session, organization_id: UUID) -> int:
    counter = session.scalar(
        select(ProductionCodeCounter)
        .where(
            ProductionCodeCounter.organization_id == organization_id,
            ProductionCodeCounter.kind == CODE_KIND_SHEET,
            ProductionCodeCounter.period == "all",
        )
        .with_for_update()
    )
    if counter is None:
        counter = ProductionCodeCounter(
            organization_id=organization_id,
            kind=CODE_KIND_SHEET,
            period="all",
            last_value=0,
        )
        session.add(counter)
        session.flush()
        counter = session.scalar(
            select(ProductionCodeCounter)
            .where(ProductionCodeCounter.id == counter.id)
            .with_for_update()
        )
        assert counter is not None
    counter.last_value += 1
    session.flush()
    return counter.last_value


def _canonical_sheet(
    session: Session,
    order: ProductionOrder,
    policy: ProductionExecutionPolicy,
    *,
    issuer_user_id,
    issuer_display_name: str,
    issued_at,
) -> dict:
    materials = [
        {
            "sequence": row.presentation_sequence,
            "name": row.operational_name,
            "unit": row.unit_code,
            "gross": format(row.gross_quantity, "f"),
            "net": format(row.net_quantity, "f"),
        }
        for row in session.scalars(
            select(ProductionOrderMaterial)
            .where(ProductionOrderMaterial.production_order_id == order.id)
            .order_by(ProductionOrderMaterial.presentation_sequence)
        )
    ]
    steps = [
        {
            "sequence": row.sequence,
            "title": row.title,
            "instructions": row.instructions,
        }
        for row in session.scalars(
            select(ProductionOrderStep)
            .where(ProductionOrderStep.production_order_id == order.id)
            .order_by(ProductionOrderStep.sequence)
        )
    ]
    batches = [
        {
            "sequence": row.sequence,
            "operational_code": row.operational_code,
            "target": format(row.target_quantity, "f"),
            "status": row.status,
        }
        for row in session.scalars(
            select(ProductionBatch)
            .where(ProductionBatch.production_order_id == order.id)
            .order_by(ProductionBatch.sequence)
        )
    ]
    establishment = session.get(Establishment, order.establishment_id)
    organization = session.get(Organization, order.organization_id)
    return {
        "schema_version": SHEET_TEMPLATE_VERSION,
        "order": {
            "id": str(order.id),
            "public_code": order.public_code,
            "status": order.status,
            "target_mode": order.target_mode,
            "target_quantity": format(order.target_quantity, "f"),
            "materials_hash": order.materials_hash,
            "steps_hash": order.steps_hash,
            "snapshot_hash": order.snapshot_hash,
            "policy_hash": policy.policy_hash,
        },
        "establishment": {
            "id": str(establishment.id) if establishment else None,
            "code": establishment.code if establishment else None,
            "display_name": establishment.display_name if establishment else None,
        },
        "organization": {
            "id": str(organization.id) if organization else None,
            "slug": organization.slug if organization else None,
            "display_name": organization.display_name if organization else None,
        },
        "issuer": {
            "user_id": str(issuer_user_id),
            "display_name": issuer_display_name,
            "issued_at": issued_at.isoformat(),
        },
        "policy": policy_canonical(policy),
        "materials": materials,
        "steps": steps,
        "batches": batches,
    }


def issue_sheet(
    session: Session,
    principal: Principal,
    *,
    order_id: UUID,
    purpose: str,
    idempotency_key: UUID,
    batch_id: UUID | None = None,
) -> ProductionSheetIssue:
    permit(principal, PERMISSION_PRODUCTION_SHEET_ISSUE)
    organization_id = org_id(principal)
    replay = existing_idempotent(session, organization_id, idempotency_key, COMMAND_ISSUE_SHEET)
    if replay is not None:
        found = session.scalar(
            select(ProductionSheetIssue).where(
                ProductionSheetIssue.organization_id == organization_id,
                ProductionSheetIssue.idempotency_key == idempotency_key,
            )
        )
        if found is not None:
            return found
    if purpose not in SHEET_PURPOSES:
        raise ValidationError("finalidade inválida")
    order = session.get(ProductionOrder, order_id)
    if order is None or order.organization_id != organization_id:
        raise ValidationError("ordem inválida")
    if order.status == ORDER_STATUS_CANCELLED:
        raise InvalidStateError("emissao_bloqueada")
    if batch_id is not None:
        batch = session.get(ProductionBatch, batch_id)
        if batch is None or batch.production_order_id != order.id:
            raise ValidationError("batelada inválida")
    policy = require_policy(session, order.id)
    issuer = session.get(AppUser, principal.user_id)
    issued_at = now()
    payload = _canonical_sheet(
        session,
        order,
        policy,
        issuer_user_id=principal.user_id,
        issuer_display_name=issuer.display_name if issuer else principal.display_name,
        issued_at=issued_at,
    )
    payload_hash = digest(payload)
    previous = session.scalar(
        select(ProductionSheetIssue)
        .where(ProductionSheetIssue.production_order_id == order.id)
        .order_by(ProductionSheetIssue.issue_number.desc())
    )
    number = _next_issue_number(session, organization_id)
    row = ProductionSheetIssue(
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        production_order_id=order.id,
        production_batch_id=batch_id,
        issue_number=number,
        template_version=SHEET_TEMPLATE_VERSION,
        canonical_payload=payload,
        payload_sha256=payload_hash,
        issued_by_user_id=principal.user_id,
        issued_at=issued_at,
        purpose=purpose,
        order_status_at_issue=order.status,
        previous_issue_id=previous.id if previous is not None else None,
        idempotency_key=idempotency_key,
    )
    session.add(row)
    session.flush()
    append_event(
        session,
        organization_id=organization_id,
        establishment_id=order.establishment_id,
        event_type=EVENT_SHEET_ISSUED,
        command=COMMAND_ISSUE_SHEET,
        actor_user_id=principal.user_id,
        idempotency_key=idempotency_key,
        payload={
            "issue_id": str(row.id),
            "issue_number": str(number),
            "payload_sha256": payload_hash,
        },
        plan_id=order.plan_id,
        order_id=order.id,
        batch_id=batch_id,
    )
    return row
