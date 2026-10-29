"""Processa push sem bloquear o pedido. Não roda durante os testes."""

from __future__ import annotations

import logging
import os
import threading

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.web_push import process_due_pushes, vapid_configured

LOG = logging.getLogger("lojadepaes.push")
_INTERVAL_SECONDS = 15


def start_push_worker() -> threading.Event | None:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return None
    settings = get_settings()
    if not vapid_configured(settings):
        return None
    stop = threading.Event()

    def loop() -> None:
        while not stop.wait(_INTERVAL_SECONDS):
            try:
                with Session(get_engine()) as session:
                    process_due_pushes(session, get_settings())
                    session.commit()
            except Exception:
                LOG.exception("falha ao processar fila de push")

    thread = threading.Thread(target=loop, name="loja-push", daemon=True)
    thread.start()
    return stop
