"""Automação Andon — converte anomalias de GembaEvent em Restriction ou KaizenTicket."""

from __future__ import annotations

import uuid
from typing import Any

from app.database.models import db
from app.models.kaizen_models import (
    DEFAULT_ROOT_CAUSE_ANALYSIS,
    STAGE_ALERTA,
    GembaEvent,
    KaizenTicket,
    Restriction,
)
from app.services.restriction_escalation_service import RestrictionEscalationService
from app.services.rdo_andon_parser import AndonAnomaly, RdoAndonParser


class AndonTriageResult:
    def __init__(
        self,
        tickets: list[KaizenTicket],
        restrictions: list[Restriction],
        escalated_tickets: list[KaizenTicket] | None = None,
    ):
        self.tickets = tickets
        self.restrictions = restrictions
        self.escalated_tickets = escalated_tickets or []


class AndonTriageService:
    def create_records_from_event(
        self,
        event: GembaEvent,
        *,
        operational_site_id: uuid.UUID | None,
        daily_execution_report_id: uuid.UUID | None,
    ) -> AndonTriageResult:
        anomalies = RdoAndonParser().detect_anomalies(event.raw_payload or {})
        tickets: list[KaizenTicket] = []
        restrictions: list[Restriction] = []

        for anomaly in anomalies:
            if anomaly.category:
                restriction = Restriction(
                    tenant_id=event.tenant_id,
                    category=anomaly.category,
                    title=anomaly.title[:255],
                    description=anomaly.description,
                    origin_event_id=event.id,
                    operational_site_id=operational_site_id,
                    daily_execution_report_id=daily_execution_report_id,
                    occurrence_date=event.event_date,
                )
                db.session.add(restriction)
                restrictions.append(restriction)
            else:
                ticket = self._build_ticket(event, anomaly, operational_site_id=operational_site_id)
                db.session.add(ticket)
                tickets.append(ticket)

        db.session.flush()

        from app.services.compliance_service import ComplianceService

        for ticket in tickets:
            ComplianceService().sync_ticket_best_effort(ticket)

        escalated_tickets: list[KaizenTicket] = []
        seen_categories = {r.category for r in restrictions}
        for category in seen_categories:
            escalated = RestrictionEscalationService().check_and_escalate(
                tenant_id=event.tenant_id,
                operational_site_id=operational_site_id,
                category=category,
                reference_date=event.event_date,
            )
            if escalated:
                escalated_tickets.append(escalated)

        return AndonTriageResult(
            tickets=tickets,
            restrictions=restrictions,
            escalated_tickets=escalated_tickets,
        )

    @staticmethod
    def _build_ticket(
        event: GembaEvent,
        anomaly: AndonAnomaly,
        *,
        operational_site_id: uuid.UUID | None = None,
    ) -> KaizenTicket:
        from app.models.operational_models import OperationalSite

        resolved_site_id = operational_site_id
        if resolved_site_id is None:
            satellite_site_id = str((event.raw_payload or {}).get("project_id") or "").strip()
            if not satellite_site_id:
                rdo = (event.raw_payload or {}).get("rdo")
                if isinstance(rdo, dict):
                    satellite_site_id = str(rdo.get("project_id") or "").strip()
            if satellite_site_id:
                site = OperationalSite.query.filter_by(
                    tenant_id=event.tenant_id, satellite_site_id=satellite_site_id
                ).first()
                if site:
                    resolved_site_id = site.id

        return KaizenTicket(
            tenant_id=event.tenant_id,
            origin_event_id=event.id,
            operational_site_id=resolved_site_id,
            title=anomaly.title[:255],
            description=anomaly.description,
            workflow_stage=STAGE_ALERTA,
            severity=anomaly.severity,
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

    @staticmethod
    def restrictions_summary(restrictions: list[Restriction]) -> list[dict[str, Any]]:
        return [
            {
                "id": str(row.id),
                "category": row.category,
                "title": row.title,
                "occurrence_date": row.occurrence_date.isoformat(),
            }
            for row in restrictions
        ]
