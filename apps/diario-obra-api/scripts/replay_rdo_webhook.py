#!/usr/bin/env python3
"""Reenvia webhook de RDO assinado para o Chamelleon (correção pontual)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from app import create_app
from app.models import DailyLog, DailyLogStatus
from app.services.rdo_service import RdoService

LOG_ID = os.getenv("REPLAY_LOG_ID", "29e269c6-deb5-494d-9327-e2c27315c605")


def main() -> int:
    app = create_app()
    with app.app_context():
        log = DailyLog.query.get(LOG_ID)
        if not log:
            print(f"RDO {LOG_ID} não encontrado")
            return 1
        if log.status != DailyLogStatus.ASSINADO and not log.is_signed:
            print(f"RDO {LOG_ID} não está assinado (status={log.status})")
            return 1
        RdoService()._emit_hub_webhook(log)
        print(f"Webhook reenviado para RDO {LOG_ID} ({log.log_date})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
