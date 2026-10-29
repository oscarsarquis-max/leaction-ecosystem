from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_BOARD_READ,
    PERMISSION_PRODUCTION_ORDER_READ,
    PERMISSION_PRODUCTION_PLAN_READ,
    Principal,
    require_permission,
)
from app.modules.identity_organization.models import Establishment
from app.modules.production_execution.models import (
    ProductionMaterialConsumption,
    ProductionOccurrence,
    ProductionSheetIssue,
    ProductionStepExecution,
    ProductionWeighingEntry,
    ProductionWeighingVerification,
    ProductionYieldMeasurement,
)
from app.modules.production_execution.projections import (
    effective_weighed_quantity,
    project_consumption,
)
from app.modules.production_http.board import project_board
from app.modules.production_http.execution import build_execution
from app.modules.production_http.deps import DEFAULT_PAGE, MAX_PAGE, get_runtime_principal
from app.modules.production_http.errors import raise_domain
from app.modules.production_http.schemas import decimal_str, envelope
from app.modules.production_http.serialize import (
    batch_out,
    conversion_out,
    decode_cursor,
    decode_plan_list_cursor,
    encode_cursor,
    encode_plan_list_cursor,
    iso,
    order_out,
    page,
    plan_item_out,
    plan_items_summary,
    plan_out,
)
from app.modules.production_http.traceability import build_traceability
from app.modules.production_planning.constants import SHIFTS
from app.modules.production_planning.errors import ValidationError
from app.modules.formula_lab.models import TechnicalProduct
from app.modules.production_planning.models import (
    ProductionBatch,
    ProductionBatchMaterial,
    ProductionEvent,
    ProductionOrder,
    ProductionOrderDependency,
    ProductionOrderMaterial,
    ProductionOrderStep,
    ProductionPlan,
    ProductionPlanItem,
)

router = APIRouter()


def _visible(session: Session, model, item_id: UUID, organization_id: UUID):
    row = session.get(model, item_id)
    if row is None or getattr(row, "organization_id", None) != organization_id:
        raise_domain(ValidationError("recurso inválido"))
    return row


def _paginate(rows, created_attr, cursor: str | None, limit: int):
    after_ts, after_id = decode_cursor(cursor)
    filtered = []
    for row in rows:
        stamp = getattr(row, created_attr)
        if after_ts is not None and (stamp, row.id) <= (after_ts, after_id):
            continue
        filtered.append(row)
    sliced = filtered[:limit]
    nxt = None
    if len(filtered) > limit:
        last = sliced[-1]
        nxt = encode_cursor(getattr(last, created_attr), last.id)
    elif sliced:
        last = sliced[-1]
        if len(filtered) == limit:
            nxt = encode_cursor(getattr(last, created_attr), last.id)
    return sliced, nxt


_SHIFT_RANK = {name: index for index, name in enumerate(SHIFTS)}


def _plan_list_sort_key(row: ProductionPlan) -> tuple[str, int, str, str]:
    return (
        row.operational_date.isoformat(),
        _SHIFT_RANK.get(row.shift or "", 99),
        row.public_code or "",
        str(row.id),
    )


def _enrich_plan_summaries(
    session: Session, plans: list[ProductionPlan]
) -> dict[UUID, tuple[int, str]]:
    """Uma query em lote para itens+produtos da página (sem N+1)."""
    if not plans:
        return {}
    plan_ids = [plan.id for plan in plans]
    rows = session.execute(
        select(
            ProductionPlanItem.production_plan_id,
            TechnicalProduct.display_name,
        )
        .outerjoin(
            TechnicalProduct,
            (TechnicalProduct.id == ProductionPlanItem.technical_product_id)
            & (TechnicalProduct.organization_id == ProductionPlanItem.organization_id),
        )
        .where(ProductionPlanItem.production_plan_id.in_(plan_ids))
        .order_by(
            ProductionPlanItem.production_plan_id,
            ProductionPlanItem.sort_order,
            ProductionPlanItem.id,
        )
    ).all()
    names_by_plan: dict[UUID, list[str | None]] = {plan_id: [] for plan_id in plan_ids}
    for plan_id, display_name in rows:
        names_by_plan.setdefault(plan_id, []).append(display_name)
    return {plan_id: plan_items_summary(names) for plan_id, names in names_by_plan.items()}


@router.get("/plans")
def list_plans(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    cursor: str | None = None,
    limit: int = Query(default=DEFAULT_PAGE, ge=1, le=MAX_PAGE),
    status: str | None = None,
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_PLAN_READ)
    except Exception as exc:
        raise_domain(exc)
    query = select(ProductionPlan).where(ProductionPlan.organization_id == organization_id)
    if status:
        query = query.where(ProductionPlan.status == status)
    rows = list(session.scalars(query).all())
    rows.sort(key=_plan_list_sort_key)
    decoded = decode_plan_list_cursor(cursor)
    if decoded is not None:
        date_part, shift_part, code_part, last_id = decoded
        cursor_key = (date_part, _SHIFT_RANK.get(shift_part, 99), code_part, str(last_id))
        rows = [row for row in rows if _plan_list_sort_key(row) > cursor_key]
    page_rows = rows[:limit]
    summaries = _enrich_plan_summaries(session, page_rows)
    items = []
    for row in page_rows:
        count, summary = summaries.get(row.id, (0, "Nenhum item planejado"))
        items.append(plan_out(row, item_count=count, items_summary=summary))
    next_cursor = None
    if len(rows) > limit and page_rows:
        last = page_rows[-1]
        next_cursor = encode_plan_list_cursor(
            last.operational_date,
            last.shift,
            last.public_code or "",
            last.id,
        )
    return page(items, next_cursor)


@router.get("/plans/{plan_id}")
def get_plan(
    organization_id: UUID,
    plan_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_PLAN_READ)
    except Exception as exc:
        raise_domain(exc)
    plan = _visible(session, ProductionPlan, plan_id, organization_id)
    joined = list(
        session.execute(
            select(ProductionPlanItem, TechnicalProduct)
            .outerjoin(
                TechnicalProduct,
                (TechnicalProduct.id == ProductionPlanItem.technical_product_id)
                & (TechnicalProduct.organization_id == organization_id),
            )
            .where(ProductionPlanItem.production_plan_id == plan.id)
            .order_by(ProductionPlanItem.sort_order, ProductionPlanItem.id)
        ).all()
    )
    return envelope(
        {
            **plan_out(plan),
            "items": [plan_item_out(item, product=product) for item, product in joined],
        },
        plan.row_version,
    )


@router.get("/orders")
def list_orders(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    cursor: str | None = None,
    limit: int = Query(default=DEFAULT_PAGE, ge=1, le=MAX_PAGE),
    status: str | None = None,
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    query = (
        select(ProductionOrder, ProductionPlan, TechnicalProduct)
        .outerjoin(
            ProductionPlan,
            (ProductionPlan.id == ProductionOrder.plan_id)
            & (ProductionPlan.organization_id == organization_id),
        )
        .outerjoin(
            TechnicalProduct,
            (TechnicalProduct.id == ProductionOrder.technical_product_id)
            & (TechnicalProduct.organization_id == organization_id),
        )
        .where(ProductionOrder.organization_id == organization_id)
    )
    if status:
        query = query.where(ProductionOrder.status == status)
    joined = list(session.execute(query.order_by(ProductionOrder.created_at, ProductionOrder.id)).all())
    by_id = {order.id: (order, plan, product) for order, plan, product in joined}
    orders = [order for order, _plan, _product in joined]
    items, nxt = _paginate(orders, "created_at", cursor, limit)
    return page(
        [
            order_out(order, product=by_id[order.id][2], plan=by_id[order.id][1])
            for order in items
        ],
        nxt,
    )


@router.get("/orders/{order_id}")
def get_order(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    order = _visible(session, ProductionOrder, order_id, organization_id)
    product = session.get(TechnicalProduct, order.technical_product_id)
    if product is not None and product.organization_id != organization_id:
        product = None
    plan = None
    if order.plan_id is not None:
        plan = session.get(ProductionPlan, order.plan_id)
        if plan is not None and plan.organization_id != organization_id:
            plan = None
    return envelope(order_out(order, product=product, plan=plan), order.row_version)


@router.get("/batches/{batch_id}")
def get_batch(
    organization_id: UUID,
    batch_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    batch = _visible(session, ProductionBatch, batch_id, organization_id)
    return envelope(batch_out(batch), batch.row_version)


@router.get("/orders/{order_id}/materials")
def get_materials(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    order = _visible(session, ProductionOrder, order_id, organization_id)
    planned = list(
        session.scalars(
            select(ProductionOrderMaterial).where(
                ProductionOrderMaterial.production_order_id == order.id
            )
        )
    )
    batches = list(
        session.scalars(
            select(ProductionBatch).where(ProductionBatch.production_order_id == order.id)
        )
    )
    actual = []
    if batches:
        for material in session.scalars(
            select(ProductionBatchMaterial).where(
                ProductionBatchMaterial.production_batch_id.in_([row.id for row in batches])
            )
        ):
            actual.append(
                {
                    "id": str(material.id),
                    "planned_gross": decimal_str(material.planned_gross_quantity),
                    "weighed_canonical": decimal_str(
                        effective_weighed_quantity(session, material.id)
                    ),
                    "consumption": {
                        key: decimal_str(value)
                        for key, value in project_consumption(session, material.id).items()
                    },
                }
            )
    return envelope(
        {
            "planned": [
                {
                    "id": str(row.id),
                    "name": row.operational_name,
                    "gross": decimal_str(row.gross_quantity),
                    "unit": row.unit_code,
                }
                for row in planned
            ],
            "actual": actual,
        }
    )


@router.get("/orders/{order_id}/steps")
def get_steps(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    order = _visible(session, ProductionOrder, order_id, organization_id)
    planned = list(
        session.scalars(
            select(ProductionOrderStep).where(ProductionOrderStep.production_order_id == order.id)
        )
    )
    actual = list(
        session.scalars(
            select(ProductionStepExecution).where(
                ProductionStepExecution.production_order_id == order.id
            )
        )
    )
    return envelope(
        {
            "planned": [
                {"id": str(row.id), "title": row.title, "sequence": row.sequence}
                for row in planned
            ],
            "actual": [{"id": str(row.id), "status": row.status} for row in actual],
        }
    )


@router.get("/orders/{order_id}/dependencies")
def get_dependencies(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    order = _visible(session, ProductionOrder, order_id, organization_id)
    rows = list(
        session.scalars(
            select(ProductionOrderDependency).where(
                ProductionOrderDependency.dependent_order_id == order.id
            )
        )
    )
    return envelope(
        [
            {
                "id": str(row.id),
                "predecessor_order_id": str(row.predecessor_order_id),
                "dependency_type": row.dependency_type,
            }
            for row in rows
        ]
    )


@router.get("/orders/{order_id}/events")
def get_events(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    cursor: str | None = None,
    limit: int = Query(default=DEFAULT_PAGE, ge=1, le=MAX_PAGE),
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    order = _visible(session, ProductionOrder, order_id, organization_id)
    rows = list(
        session.scalars(
            select(ProductionEvent)
            .where(ProductionEvent.order_id == order.id)
            .order_by(ProductionEvent.occurred_at, ProductionEvent.id)
        )
    )
    items, nxt = _paginate(rows, "occurred_at", cursor, limit)
    return page(
        [
            {
                "id": str(row.id),
                "type": row.event_type,
                "command": row.command,
                "occurred_at": iso(row.occurred_at),
            }
            for row in items
        ],
        nxt,
    )


@router.get("/orders/{order_id}/weighings")
def get_weighings(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    order = _visible(session, ProductionOrder, order_id, organization_id)
    batches = list(
        session.scalars(
            select(ProductionBatch).where(ProductionBatch.production_order_id == order.id)
        )
    )
    materials = []
    if batches:
        materials = list(
            session.scalars(
                select(ProductionBatchMaterial).where(
                    ProductionBatchMaterial.production_batch_id.in_([row.id for row in batches])
                )
            )
        )
    material_ids = {row.id for row in materials}
    entries = []
    if material_ids:
        entries = list(
            session.scalars(
                select(ProductionWeighingEntry).where(
                    ProductionWeighingEntry.production_batch_material_id.in_(material_ids)
                )
            )
        )
    verifications = []
    if entries:
        verifications = list(
            session.scalars(
                select(ProductionWeighingVerification).where(
                    ProductionWeighingVerification.entry_id.in_([row.id for row in entries])
                )
            )
        )
    return envelope(
        {
            "entries": [{"id": str(row.id), **conversion_out(row)} for row in entries],
            "verifications": [
                {"id": str(row.id), "entry_id": str(row.entry_id), "decision": row.decision}
                for row in verifications
            ],
        }
    )


@router.get("/orders/{order_id}/consumptions")
def get_consumptions(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    order = _visible(session, ProductionOrder, order_id, organization_id)
    rows = list(
        session.scalars(
            select(ProductionMaterialConsumption).where(
                ProductionMaterialConsumption.production_order_id == order.id
            )
        )
    )
    return envelope(
        [{"id": str(row.id), "type": row.consumption_type, **conversion_out(row)} for row in rows]
    )


@router.get("/orders/{order_id}/step-runs")
def get_step_runs(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    order = _visible(session, ProductionOrder, order_id, organization_id)
    rows = list(
        session.scalars(
            select(ProductionStepExecution).where(
                ProductionStepExecution.production_order_id == order.id
            )
        )
    )
    return envelope([{"id": str(row.id), "status": row.status} for row in rows])


@router.get("/orders/{order_id}/yields")
def get_yields(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    order = _visible(session, ProductionOrder, order_id, organization_id)
    rows = list(
        session.scalars(
            select(ProductionYieldMeasurement).where(
                ProductionYieldMeasurement.production_order_id == order.id
            )
        )
    )
    return envelope(
        [
            {
                "id": str(row.id),
                "type": row.measurement_type,
                "quantity": decimal_str(row.quantity),
            }
            for row in rows
        ]
    )


@router.get("/orders/{order_id}/occurrences")
def get_occurrences(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    order = _visible(session, ProductionOrder, order_id, organization_id)
    rows = list(
        session.scalars(
            select(ProductionOccurrence).where(ProductionOccurrence.production_order_id == order.id)
        )
    )
    return envelope(
        [{"id": str(row.id), "category": row.category, "status": row.status} for row in rows]
    )


@router.get("/orders/{order_id}/sheets")
def get_sheets(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    order = _visible(session, ProductionOrder, order_id, organization_id)
    rows = list(
        session.scalars(
            select(ProductionSheetIssue).where(ProductionSheetIssue.production_order_id == order.id)
        )
    )
    return envelope(
        [
            {
                "id": str(row.id),
                "issue_number": row.issue_number,
                "payload_sha256": row.payload_sha256,
                "purpose": row.purpose,
            }
            for row in rows
        ]
    )


@router.get("/orders/{order_id}/sheets/{issue_id}")
def get_sheet_payload(
    organization_id: UUID,
    order_id: UUID,
    issue_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    order = _visible(session, ProductionOrder, order_id, organization_id)
    issue = _visible(session, ProductionSheetIssue, issue_id, organization_id)
    if issue.production_order_id != order.id:
        raise_domain(ValidationError("emissão inválida"))
    return envelope(
        {
            "id": str(issue.id),
            "issue_number": issue.issue_number,
            "purpose": issue.purpose,
            "order_status_at_issue": issue.order_status_at_issue,
            "previous_issue_id": (
                None if issue.previous_issue_id is None else str(issue.previous_issue_id)
            ),
            "payload_sha256": issue.payload_sha256,
            "canonical_payload": issue.canonical_payload,
        }
    )


@router.get("/orders/{order_id}/execution")
def get_execution(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    return envelope(build_execution(session, principal, organization_id, order_id))


@router.get("/orders/{order_id}/traceability")
def get_traceability(
    organization_id: UUID,
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    return envelope(build_traceability(session, principal, organization_id, order_id))


_SHIFT_LABEL = {"morning": "Manhã", "afternoon": "Tarde", "night": "Noite"}
_AREAS = (
    ("fornos", "Fornos"),
    ("masseira", "Masseira"),
    ("bancada", "Bancada"),
    ("embalagem", "Embalagem"),
)


@router.get("/board/context")
def get_board_context(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_BOARD_READ)
    except Exception as exc:
        raise_domain(exc)
    places = list(
        session.scalars(
            select(Establishment)
            .where(
                Establishment.organization_id == organization_id,
                Establishment.status == "active",
            )
            .order_by(Establishment.display_name)
        )
    )
    return envelope(
        {
            "establishments": [
                {"id": str(row.id), "code": row.code, "display_name": row.display_name} for row in places
            ],
            "shifts": [{"code": code, "label": _SHIFT_LABEL[code]} for code in SHIFTS],
            "areas": [{"code": code, "label": label} for code, label in _AREAS],
        }
    )


@router.get("/board")
def get_board(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    operational_date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    establishment_id: UUID | None = None,
    shift: str | None = None,
    area: str | None = Query(default=None, max_length=64),
    product_id: UUID | None = None,
    status: str | None = None,
    priority: int | None = None,
    q: str | None = Query(default=None, max_length=64),
):
    from datetime import date as date_cls

    def _date(value: str | None):
        if value is None:
            return None
        try:
            return date_cls.fromisoformat(value)
        except ValueError:
            raise_domain(ValidationError("contrato_invalido"))

    return envelope(
        project_board(
            session,
            principal,
            organization_id,
            operational_date=_date(operational_date),
            date_from=_date(date_from),
            date_to=_date(date_to),
            establishment_id=establishment_id,
            shift=shift,
            area=area,
            product_id=product_id,
            status=status,
            priority=priority,
            q=q,
        )
    )
