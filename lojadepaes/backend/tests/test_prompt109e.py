"""109E: a solicitação de data só vale para o que a vitrine não vende.

Servidor: `create_date_request` recusa (409) a data que o calendário vende, com a mesma avaliação
(`evaluate_day`). Fechado, completo e sem produção seguem aceitos. Sem e-mail real, sem Hub.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.domain.date_requests import DATE_AVAILABLE_MESSAGE
from app.domain.schedule import save_date_override
from app.models.date_requests import DateRequest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_prompt96 import _variant
from tests.test_schedule import _next_iso

pytestmark = pytest.mark.sellable_guard

MESSAGE = "Esta data está disponível. Finalize o pedido pelo carrinho."


def _payload(desired: str, **overrides):
    body = {
        "desired_date": desired,
        "customer_name": "Cliente 109E",
        "customer_email": f"{uuid4().hex[:8]}@example.test",
        "idempotency_key": f"109e-{uuid4().hex}",
        "intended_quantity": 2,
    }
    body.update(overrides)
    return body


def _calendar_day(client: TestClient, day: str) -> dict:
    response = client.get("/api/v1/schedule/calendar", params={"start": day, "end": day, "selected": day})
    assert response.status_code == 200, response.text
    return response.json()["days"][0]


def _count(db: Session) -> int:
    db.expire_all()
    return int(db.scalar(select(func.count()).select_from(DateRequest)) or 0)


def test_message_is_the_one_the_screen_shows() -> None:
    assert DATE_AVAILABLE_MESSAGE == MESSAGE


def test_sellable_date_is_refused_with_calendar_evaluation(client: TestClient, db: Session) -> None:
    wednesday = (_next_iso(3) + timedelta(days=7)).isoformat()
    day = _calendar_day(client, wednesday)
    assert day["status"] == "available" and day["eligible"] is True
    before = _count(db)
    refused = client.post("/api/v1/schedule/date-requests", json=_payload(wednesday))
    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"] == MESSAGE
    assert _count(db) == before


def test_sellable_date_is_refused_with_cart_lines_too(client: TestClient, db: Session) -> None:
    variant = _variant(db)
    db.commit()
    wednesday = (_next_iso(3) + timedelta(days=7)).isoformat()
    before = _count(db)
    refused = client.post(
        "/api/v1/schedule/date-requests",
        json=_payload(wednesday, lines=[{"variant_id": str(variant.id), "quantity": 1}]),
    )
    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"] == MESSAGE
    assert _count(db) == before


def test_closed_day_is_accepted(client: TestClient, db: Session) -> None:
    monday = _next_iso(1).isoformat()
    day = _calendar_day(client, monday)
    assert day["status"] == "closed" and day["eligible"] is False
    before = _count(db)
    accepted = client.post("/api/v1/schedule/date-requests", json=_payload(monday))
    assert accepted.status_code == 200, accepted.text
    assert _count(db) == before + 1


def test_full_day_is_accepted(client: TestClient, db: Session) -> None:
    wednesday = _next_iso(3) + timedelta(days=14)
    save_date_override(
        db,
        get_settings(),
        wednesday,
        open_state="open",
        daily_physical_limit=0,
        daily_base_limit=None,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    db.commit()
    day = _calendar_day(client, wednesday.isoformat())
    assert day["remaining_physical"] == 0
    before = _count(db)
    accepted = client.post("/api/v1/schedule/date-requests", json=_payload(wednesday.isoformat()))
    assert accepted.status_code == 200, accepted.text
    assert _count(db) == before + 1


def test_idempotent_replay_does_not_hit_the_guard(client: TestClient, db: Session) -> None:
    monday = _next_iso(1).isoformat()
    body = _payload(monday)
    first = client.post("/api/v1/schedule/date-requests", json=body)
    assert first.status_code == 200, first.text
    again = client.post("/api/v1/schedule/date-requests", json=body)
    assert again.status_code == 200
    assert again.json()["id"] == first.json()["id"]
