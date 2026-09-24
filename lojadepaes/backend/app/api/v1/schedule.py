from datetime import date

from fastapi import APIRouter, Query, Response

from app.api.deps import AppSettings, ClientHost, DbSession, PreviewGate
from app.domain.date_requests import create_date_request
from app.domain.operations import assert_date_requests_enabled
from app.domain.schedule import ProposedLine, preview_calendar
from app.domain.suggestions import suggest_fornada
from app.schemas.schedule import CalendarQuery
from app.schemas.suggestions import (
    DateRequestCreateIn,
    DateRequestPublicOut,
    SuggestionsOut,
    SuggestionsQuery,
)

router = APIRouter(prefix="/schedule", tags=["schedule"])


def _preview(db, settings, payload: CalendarQuery) -> dict:
    result = preview_calendar(
        db,
        settings,
        start=payload.start,
        end=payload.end,
        selected=payload.selected,
        lines=[
            ProposedLine(
                kind=line.kind,
                quantity=line.quantity,
                variant_id=line.variant_id,
                dough_type_id=line.dough_type_id,
            )
            for line in payload.lines
        ],
    )
    return {
        "occupancy_enabled": result.occupancy_enabled,
        "reservation_policy": result.reservation_policy,
        "timezone": result.timezone,
        "selected_date": result.selected_date.isoformat() if result.selected_date else None,
        "selected_status": result.selected_status,
        "full_message": result.full_message,
        "alternatives": result.alternatives,
        "notice": result.notice,
        "review_message": result.review_message,
        "days": [
            {
                "date": item.local_date.isoformat(),
                "status": item.status,
                "origin": item.origin,
                "daily_physical_limit": item.daily_physical_limit,
                "daily_base_limit": item.daily_base_limit,
                "committed_physical": item.committed_physical,
                "remaining_physical": item.remaining_physical,
                "committed_base_ids": item.committed_base_ids,
                "remaining_new_bases": item.remaining_new_bases,
                "reason": item.reason,
                "accessible_label": item.accessible_label,
                "weekday_name": item.weekday_name,
                "eligible": item.eligible_for_selection,
                "awaiting_review": item.awaiting_review,
                "windows": item.windows,
            }
            for item in result.days
        ],
    }


@router.get("/calendar")
def get_calendar(
    db: DbSession,
    settings: AppSettings,
    response: Response,
    _: PreviewGate,
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    selected: date | None = Query(default=None),
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return _preview(db, settings, CalendarQuery(start=start, end=end, selected=selected))


@router.post("/preview")
def post_preview(
    payload: CalendarQuery, db: DbSession, settings: AppSettings, response: Response, _: PreviewGate
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return _preview(db, settings, payload)


@router.post("/suggestions", response_model=SuggestionsOut)
def post_suggestions(
    payload: SuggestionsQuery,
    db: DbSession,
    settings: AppSettings,
    response: Response,
    _: PreviewGate,
) -> SuggestionsOut:
    response.headers["Cache-Control"] = "no-store"
    return suggest_fornada(db, settings, payload)


@router.post("/date-requests", response_model=DateRequestPublicOut)
def post_date_request(
    payload: DateRequestCreateIn,
    db: DbSession,
    settings: AppSettings,
    host: ClientHost,
    response: Response,
    _: PreviewGate,
) -> DateRequestPublicOut:
    assert_date_requests_enabled(settings)
    response.headers["Cache-Control"] = "no-store"
    row = create_date_request(db, settings, payload, client_host=host)
    return DateRequestPublicOut(
        id=row.id,
        status=row.status,
        desired_date=row.desired_date,
        message=(
            "Registramos sua solicitação de data. A padaria vai avaliar e responder por e-mail. "
            "Isso ainda não confirma a fornada."
        ),
    )
