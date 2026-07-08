"""Ingestão de eventos operacionais Gemba a partir de micro-serviços satélites."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from app.database.models import Tenant, db
from app.models.kaizen_models import (
    EVENT_TYPE_RDO_FINALIZED,
    SOURCE_APP_DIARIO_OBRA,
    GembaEvent,
    KaizenTicket,
)
from app.services.andon_triage_service import AndonTriageService
from app.services.operational_service import OperationalService


class GembaIngestionResult:
    def __init__(self, event: GembaEvent, tickets: list[KaizenTicket]):
        self.event = event
        self.tickets = tickets


class GembaIngestionService:
    def ingest_rdo_event(self, payload: dict[str, Any]) -> GembaIngestionResult:
        if not isinstance(payload, dict):
            raise ValueError("Payload JSON inválido.")

        tenant_id = self._resolve_tenant_id(payload)
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant '{tenant_id}' não encontrado.")

        source_app = str(payload.get("source_app") or SOURCE_APP_DIARIO_OBRA).strip()
        event_type = str(payload.get("event_type") or EVENT_TYPE_RDO_FINALIZED).strip()
        event_date = self._parse_event_date(payload)

        event = GembaEvent(
            tenant_id=tenant_id,
            source_app=source_app,
            event_date=event_date,
            event_type=event_type,
            raw_payload=payload,
            processed_by_ai=False,
        )
        db.session.add(event)
        db.session.flush()

        tickets = AndonTriageService().create_tickets_from_event(event)
        OperationalService().upsert_execution_report_from_rdo(
            tenant_id=tenant_id,
            event_id=event.id,
            event_date=event_date,
            payload=payload,
        )
        db.session.commit()
        return GembaIngestionResult(event=event, tickets=tickets)

    @staticmethod
    def _resolve_tenant_id(payload: dict[str, Any]) -> uuid.UUID:
        raw = payload.get("tenant_id")
        if raw is None or str(raw).strip() == "":
            raise ValueError("Campo obrigatório: tenant_id.")
        try:
            return uuid.UUID(str(raw).strip())
        except ValueError as exc:
            raise ValueError("tenant_id inválido (UUID esperado).") from exc

    @staticmethod
    def _parse_event_date(payload: dict[str, Any]) -> date:
        raw = payload.get("event_date") or payload.get("log_date")
        if raw is None or str(raw).strip() == "":
            return date.today()

        text = str(raw).strip()
        try:
            if "T" in text:
                return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
            return date.fromisoformat(text[:10])
        except ValueError as exc:
            raise ValueError("event_date inválido (use ISO-8601, ex.: 2026-07-07).") from exc
