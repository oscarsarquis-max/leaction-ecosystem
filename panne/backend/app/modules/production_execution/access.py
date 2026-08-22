from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity_organization.authorization import (
    AuthorizationError,
    Principal,
    require_permission,
)
from app.modules.production_execution.models import ProductionWeighingSession
from app.modules.production_planning.errors import (
    ConcurrencyError,
    PermissionDeniedError,
    ValidationError,
)
from app.modules.production_planning.models import ProductionBatch, ProductionOrder


def permit(principal: Principal, code: str) -> None:
    try:
        require_permission(principal, code)
    except AuthorizationError as exc:
        raise PermissionDeniedError("permissao_negada") from exc


def org_id(principal: Principal) -> UUID:
    if principal.selected is None:
        raise PermissionDeniedError("organizacao_nao_selecionada")
    return principal.selected.organization_id


def now() -> datetime:
    return datetime.now(UTC)


def bump(row) -> None:
    row.row_version += 1
    if hasattr(row, "updated_at"):
        row.updated_at = now()


def lock_order(
    session: Session, order_id: UUID, organization_id: UUID, expected_row_version: int | None
) -> ProductionOrder:
    order = session.scalar(
        select(ProductionOrder).where(ProductionOrder.id == order_id).with_for_update()
    )
    if order is None or order.organization_id != organization_id:
        raise ValidationError("ordem inválida")
    if expected_row_version is not None and order.row_version != expected_row_version:
        raise ConcurrencyError("versao_conflito")
    return order


def lock_batch(
    session: Session, batch_id: UUID, organization_id: UUID, expected_row_version: int | None
) -> ProductionBatch:
    batch = session.scalar(
        select(ProductionBatch).where(ProductionBatch.id == batch_id).with_for_update()
    )
    if batch is None or batch.organization_id != organization_id:
        raise ValidationError("batelada inválida")
    if expected_row_version is not None and batch.row_version != expected_row_version:
        raise ConcurrencyError("versao_conflito")
    return batch


def lock_session(
    session: Session, session_id: UUID, organization_id: UUID, expected_row_version: int | None
) -> ProductionWeighingSession:
    row = session.scalar(
        select(ProductionWeighingSession)
        .where(ProductionWeighingSession.id == session_id)
        .with_for_update()
    )
    if row is None or row.organization_id != organization_id:
        raise ValidationError("sessão inválida")
    if expected_row_version is not None and row.row_version != expected_row_version:
        raise ConcurrencyError("versao_conflito")
    return row
