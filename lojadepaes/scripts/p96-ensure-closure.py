"""Configura o fechamento 10–18/10 com fornadas a partir de 21/10. Idempotente."""

from datetime import date

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.admin_auth import actor_ref_for
from app.domain.schedule_closures import (
    commitments_in_range,
    ensure_authorized_closure,
    serialize_closure,
)
from sqlalchemy.orm import sessionmaker


def main() -> None:
    settings = get_settings()
    actor = actor_ref_for(settings.admin_username.strip() or "desconhecido")
    factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    session = factory()
    try:
        row = ensure_authorized_closure(
            session,
            settings,
            start_date=date(2026, 10, 10),
            end_date=date(2026, 10, 18),
            first_eligible_date=date(2026, 10, 21),
            pause_intake=False,
            internal_reason="Viagem",
            actor_ref=actor,
        )
        session.commit()
        payload = serialize_closure(session, settings, row)
        extras = commitments_in_range(session, date(2026, 10, 10), date(2026, 10, 20))
        print("closure_id", payload["id"])
        print("status", payload["status"])
        print("blocked_until", payload["blocked_until"])
        print("pause_intake", payload["pause_intake"])
        print("actor", actor)
        print("orders", extras["order_count"])
        print("date_requests", extras["date_request_count"])
        for item in extras["orders"]:
            print("order", item["reference"], item["date"], item["status"])
        for item in extras["date_requests"]:
            print("request", item["id"], item["date"], item["status"])
    finally:
        session.close()


if __name__ == "__main__":
    main()
