from __future__ import annotations

import logging
import os
import threading

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.email_outbox import process_due_outbox

LOG = logging.getLogger("lojadepaes.email")
_INTERVAL_SECONDS = 15


def start_email_outbox_worker() -> threading.Event | None:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return None
    settings = get_settings()
    if settings.mail_backend.strip().lower() != "ses" or not settings.mail_transport_ready:
        return None
    stop = threading.Event()

    def loop() -> None:
        while not stop.wait(_INTERVAL_SECONDS):
            try:
                with Session(get_engine()) as session:
                    process_due_outbox(session, get_settings())
                    session.commit()
            except Exception:
                LOG.exception("falha ao processar outbox de e-mail")

    thread = threading.Thread(target=loop, name="loja-email-outbox", daemon=True)
    thread.start()
    return stop
