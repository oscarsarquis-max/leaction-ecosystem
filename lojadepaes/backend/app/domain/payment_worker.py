"""Automatic financial recovery, independent of the order's operational stage."""

from __future__ import annotations

import logging
import os
import threading
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, case, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_engine
from app.domain.actionhub_client import HubUnavailableError
from app.domain.payment_alerts import review_sync_alert
from app.domain.storefront_orders import reconcile_payment_record
from app.models.orders import Order
from app.models.payments import PaymentRecord

LOG = logging.getLogger("lojadepaes.payments")
INTERVAL_SECONDS = 30
BATCH_SIZE = 10
# Falha persistente: 90 s após a ocorrência abrir. Pendente/desconhecido volta a cada 30 s.
# Registro já pago só entra de novo quando updated_at tem pelo menos 5 minutos.


def process_payment_checks(
    session: Session, settings: Settings, *, now: datetime | None = None
) -> dict:
    now = now or datetime.now(UTC)
    # The timestamps are persisted: restarting the worker does not lose pending work.
    priority = case(
        (PaymentRecord.financial_status.in_(("pending", "unknown")), 0),
        else_=1,
    )
    ids = list(
        session.scalars(
            select(PaymentRecord.id)
            .where(
                PaymentRecord.provider == "actionhub",
                PaymentRecord.external_reference.is_not(None),
                PaymentRecord.idempotency_key.is_not(None),
                or_(
                    and_(
                        PaymentRecord.financial_status.in_(["pending", "unknown"]),
                        PaymentRecord.updated_at <= now - timedelta(seconds=INTERVAL_SECONDS),
                    ),
                    and_(
                        PaymentRecord.financial_status == "paid",
                        PaymentRecord.updated_at <= now - timedelta(minutes=5),
                    ),
                ),
            )
            .order_by(priority, PaymentRecord.updated_at.asc(), PaymentRecord.id.asc())
            .limit(BATCH_SIZE)
            .with_for_update(skip_locked=True)
        )
    )
    if ids:
        session.execute(
            update(PaymentRecord).where(PaymentRecord.id.in_(ids)).values(updated_at=now)
        )
        session.commit()
    checked = failures = 0
    for record_id in ids:
        record = session.get(PaymentRecord, record_id)
        order = session.get(Order, record.order_id) if record is not None else None
        if record is None or order is None:
            session.commit()
            continue
        try:
            with session.begin_nested():
                reconcile_payment_record(session, settings, order, record)
            if record.sanitized_error:
                failures += 1
        except HubUnavailableError:
            failures += 1
            record.sanitized_error = (
                "Verificação do pagamento indisponível. Não refaça o pagamento."
            )
        except Exception:
            failures += 1
            LOG.exception("payment_reconciliation_failed record_id=%s", record.id)
            record.sanitized_error = (
                "Falha na verificação financeira; a operação precisa conferir o pagamento."
            )
        review_sync_alert(session, settings, order, record, now)
        # Release this record before the next network wait. Row locks survive a savepoint.
        session.commit()
        checked += 1
    return {"checked": checked, "failures": failures}


def start_payment_worker() -> threading.Event | None:
    if os.environ.get("PYTEST_CURRENT_TEST") or not get_settings().actionhub_app_secret.strip():
        return None
    stop = threading.Event()

    def loop() -> None:
        while not stop.wait(INTERVAL_SECONDS):
            try:
                with Session(get_engine()) as session:
                    result = process_payment_checks(session, get_settings())
                    session.commit()
                if result["failures"]:
                    LOG.warning(
                        "payment_reconciliation_attention checked=%s failures=%s",
                        result["checked"],
                        result["failures"],
                    )
            except Exception:
                LOG.exception("payment_reconciliation_batch_failed")

    threading.Thread(target=loop, name="loja-payment-recovery", daemon=True).start()
    return stop
