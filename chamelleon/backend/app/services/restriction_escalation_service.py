"""Escalonamento automático de Restrição recorrente para ticket Kaizen (IN 01)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from app.database.models import db
from app.models.kaizen_models import (
    DEFAULT_ROOT_CAUSE_ANALYSIS,
    RESTRICTION_CATEGORY_LABELS,
    RESTRICTION_RECURRENCE_THRESHOLD,
    RESTRICTION_RECURRENCE_WINDOW_DAYS,
    STAGE_ALERTA,
    KaizenTicket,
    Restriction,
)
from app.models.operational_models import OperationalSite


class RestrictionEscalationService:
    def check_and_escalate(
        self,
        *,
        tenant_id: uuid.UUID,
        operational_site_id: uuid.UUID | None,
        category: str,
        reference_date: date,
    ) -> KaizenTicket | None:
        if not operational_site_id:
            # Sem site resolvido não há "mesmo canteiro" para medir recorrência.
            return None

        window_start = reference_date - timedelta(days=RESTRICTION_RECURRENCE_WINDOW_DAYS)
        candidates = (
            Restriction.query.filter(
                Restriction.tenant_id == tenant_id,
                Restriction.operational_site_id == operational_site_id,
                Restriction.category == category,
                Restriction.escalated_ticket_id.is_(None),
                Restriction.occurrence_date >= window_start,
                Restriction.occurrence_date <= reference_date,
            )
            .order_by(Restriction.occurrence_date.asc())
            .all()
        )

        if len(candidates) < RESTRICTION_RECURRENCE_THRESHOLD:
            return None

        site = db.session.get(OperationalSite, operational_site_id)
        site_name = site.name if site else "Unidade"
        label = RESTRICTION_CATEGORY_LABELS.get(category, category)

        history_lines = "\n".join(
            f"- {c.occurrence_date.isoformat()}: {c.title}" for c in candidates
        )
        ticket = KaizenTicket(
            tenant_id=tenant_id,
            origin_event_id=candidates[-1].origin_event_id,
            title=(
                f"Recorrência: {label} em {site_name} "
                f"({len(candidates)}x em {RESTRICTION_RECURRENCE_WINDOW_DAYS} dias)"
            )[:255],
            description=(
                f"Escalonamento automático — {len(candidates)} ocorrências de restrição "
                f"'{label}' em {site_name} nos últimos {RESTRICTION_RECURRENCE_WINDOW_DAYS} dias.\n\n"
                f"Histórico:\n{history_lines}\n\n"
                "Padrão recorrente — considere os 5 Porquês sobre a causa sistêmica, "
                "não apenas o evento mais recente."
            ),
            workflow_stage=STAGE_ALERTA,
            root_cause_analysis=dict(DEFAULT_ROOT_CAUSE_ANALYSIS),
            is_operator_retrained=False,
        )
        db.session.add(ticket)
        db.session.flush()

        for candidate in candidates:
            candidate.escalated_ticket_id = ticket.id

        db.session.flush()
        return ticket
