"""Automação Andon — converte anomalias de GembaEvent em KaizenTicket."""

from __future__ import annotations

import uuid
from typing import Any

from app.database.models import db
from app.models.kaizen_models import DEFAULT_ROOT_CAUSE_ANALYSIS, STAGE_ALERTA, GembaEvent, KaizenTicket
from app.services.rdo_andon_parser import AndonAnomaly, RdoAndonParser


class AndonTriageService:
    def create_tickets_from_event(self, event: GembaEvent) -> list[KaizenTicket]:
        anomalies = RdoAndonParser().detect_anomalies(event.raw_payload or {})
        if not anomalies:
            return []

        tickets: list[KaizenTicket] = []
        for anomaly in anomalies:
            ticket = self._build_ticket(event, anomaly)
            db.session.add(ticket)
            tickets.append(ticket)

        db.session.flush()
        return tickets

    @staticmethod
    def _build_ticket(event: GembaEvent, anomaly: AndonAnomaly) -> KaizenTicket:
        return KaizenTicket(
            tenant_id=event.tenant_id,
            origin_event_id=event.id,
            title=anomaly.title[:255],
            description=anomaly.description,
            workflow_stage=STAGE_ALERTA,
            root_cause_analysis=dict(DEFAULT_ROOT_CAUSE_ANALYSIS),
            is_operator_retrained=False,
        )

    @staticmethod
    def tickets_summary(tickets: list[KaizenTicket]) -> list[dict[str, Any]]:
        return [
            {
                "id": str(ticket.id),
                "title": ticket.title,
                "workflow_stage": ticket.workflow_stage,
                "origin_event_id": str(ticket.origin_event_id) if ticket.origin_event_id else None,
            }
            for ticket in tickets
        ]
