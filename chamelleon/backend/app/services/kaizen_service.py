"""Regras de negócio do módulo Gemba-Kaizen."""

from __future__ import annotations

import uuid
from typing import Any

from flask import g

from app.database.models import db
from app.models.kaizen_models import (
    DEFAULT_ROOT_CAUSE_ANALYSIS,
    KAIZEN_WORKFLOW_STAGES,
    STAGE_ALERTA,
    STAGE_CINCO_PORQUES,
    STAGE_CONCLUIDO,
    STAGE_CONTENCAO,
    STAGE_PADRONIZACAO,
    KaizenTicket,
    GembaEvent,
)


class KaizenService:
    def list_tickets(self, *, workflow_stage: str | None = None) -> list[dict[str, Any]]:
        tenant_id = self._tenant_id()
        query = KaizenTicket.query.filter_by(tenant_id=tenant_id)
        if workflow_stage:
            self._validate_workflow_stage(workflow_stage)
            query = query.filter_by(workflow_stage=workflow_stage)
        tickets = query.order_by(
            KaizenTicket.workflow_stage.asc(),
            KaizenTicket.updated_at.desc(),
        ).all()
        return [ticket.to_dict() for ticket in tickets]

    def list_tickets_kanban(self) -> dict[str, list[dict[str, Any]]]:
        tenant_id = self._tenant_id()
        tickets = (
            KaizenTicket.query.filter_by(tenant_id=tenant_id)
            .order_by(KaizenTicket.updated_at.desc())
            .all()
        )
        board: dict[str, list[dict[str, Any]]] = {
            stage: [] for stage in KAIZEN_WORKFLOW_STAGES
        }
        for ticket in tickets:
            stage = ticket.workflow_stage
            if stage not in board:
                board[stage] = []
            board[stage].append(ticket.to_dict())
        return board

    def get_ticket(self, ticket_id: str) -> dict[str, Any]:
        ticket = self._get_ticket_or_404(ticket_id)
        return ticket.to_dict()

    def create_ticket(self, payload: dict[str, Any]) -> KaizenTicket:
        tenant_id = self._tenant_id()
        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("Campo obrigatório: title.")

        origin_event_id = self._parse_optional_uuid(
            payload.get("origin_event_id"), "origin_event_id"
        )
        if origin_event_id:
            event = db.session.get(GembaEvent, origin_event_id)
            if not event or event.tenant_id != tenant_id:
                raise ValueError("origin_event_id inválido ou de outro tenant.")

        workflow_stage = str(payload.get("workflow_stage") or STAGE_ALERTA).strip()
        self._validate_workflow_stage(workflow_stage)

        ticket = KaizenTicket(
            tenant_id=tenant_id,
            origin_event_id=origin_event_id,
            title=title,
            description=self._optional_text(payload.get("description")),
            workflow_stage=workflow_stage,
            temporary_containment_action=self._optional_text(
                payload.get("temporary_containment_action")
            ),
            root_cause_analysis=self._merge_root_cause(payload.get("root_cause_analysis")),
            standardization_action=self._optional_text(payload.get("standardization_action")),
            is_operator_retrained=bool(payload.get("is_operator_retrained", False)),
        )
        db.session.add(ticket)
        db.session.commit()
        return ticket

    def update_ticket(self, ticket_id: str, payload: dict[str, Any]) -> KaizenTicket:
        ticket = self._get_ticket_or_404(ticket_id)

        if "title" in payload:
            title = str(payload.get("title") or "").strip()
            if not title:
                raise ValueError("title não pode ser vazio.")
            ticket.title = title

        if "description" in payload:
            ticket.description = self._optional_text(payload.get("description"))

        if "workflow_stage" in payload:
            stage = str(payload.get("workflow_stage") or "").strip()
            self._validate_workflow_stage(stage)
            self._validate_stage_transition_requirements(ticket, stage, payload)
            ticket.workflow_stage = stage

        if "temporary_containment_action" in payload:
            ticket.temporary_containment_action = self._optional_text(
                payload.get("temporary_containment_action")
            )

        if "root_cause_analysis" in payload:
            ticket.root_cause_analysis = self._merge_root_cause(
                payload.get("root_cause_analysis"),
                ticket.root_cause_analysis,
            )

        if "standardization_action" in payload:
            ticket.standardization_action = self._optional_text(
                payload.get("standardization_action")
            )

        if "is_operator_retrained" in payload:
            ticket.is_operator_retrained = bool(payload.get("is_operator_retrained"))

        if "origin_event_id" in payload:
            origin_event_id = self._parse_optional_uuid(
                payload.get("origin_event_id"), "origin_event_id"
            )
            if origin_event_id:
                event = db.session.get(GembaEvent, origin_event_id)
                if not event or event.tenant_id != ticket.tenant_id:
                    raise ValueError("origin_event_id inválido ou de outro tenant.")
            ticket.origin_event_id = origin_event_id

        db.session.commit()
        return ticket

    def save_five_whys(self, ticket_id: str, payload: dict[str, Any]) -> KaizenTicket:
        ticket = self._get_ticket_or_404(ticket_id)
        ticket.root_cause_analysis = self._merge_root_cause(
            payload, ticket.root_cause_analysis
        )
        db.session.commit()
        return ticket

    def escalate_to_sprint(self, ticket_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Escala ticket Kaizen para uma Sprint no plano TD ativo do Chamelleon."""
        from app.core.td_constants import TD_OFFICIAL_DOMAINS_SET
        from app.models.td_models import TdKanbanStage, TdOriginType, TdSprint
        from app.services.td_service import TdService

        ticket = self._get_ticket_or_404(ticket_id)
        if ticket.escalated_to_sprint_id:
            raise ValueError("Este ticket Kaizen já foi escalado para uma Sprint.")

        if isinstance(payload.get("root_cause_analysis"), dict):
            ticket.root_cause_analysis = self._merge_root_cause(
                payload["root_cause_analysis"],
                ticket.root_cause_analysis,
            )

        rca = ticket.root_cause_analysis or dict(DEFAULT_ROOT_CAUSE_ANALYSIS)
        root_cause = (rca.get("root_cause") or rca.get("why_5") or rca.get("why_1") or "").strip()
        if not root_cause:
            raise ValueError(
                "Preencha a causa raiz (5 Porquês) antes de escalar para o plano organizacional."
            )

        domain = str(payload.get("paneldx_domain") or payload.get("domain") or "").strip()
        if domain not in TD_OFFICIAL_DOMAINS_SET:
            allowed = ", ".join(sorted(TD_OFFICIAL_DOMAINS_SET))
            raise ValueError(f"Domínio inválido. Escolha um de: {allowed}.")

        td_service = TdService()
        plan = td_service._resolve_plan_for_write(payload.get("plan_id"))

        description_parts = []
        if ticket.temporary_containment_action:
            description_parts.append(f"Contenção: {ticket.temporary_containment_action}")
        if ticket.description:
            description_parts.append(ticket.description)
        description = "\n\n".join(description_parts) or None

        sprint = TdSprint(
            tenant_id=ticket.tenant_id,
            plan_id=plan.id,
            title=f"Kaizen Escalado: {ticket.title}",
            description=description,
            paneldx_domain=domain,
            origin_type=TdOriginType.KAIZEN_EMERGENT.value,
            kanban_stage=TdKanbanStage.KAIZEN_ENTRADA.value,
            origin_ref_id=ticket.id,
            current_state_gap=root_cause,
            goals_payload={
                "name_sprn": f"Kaizen Escalado: {ticket.title}",
                "objetivo": root_cause,
                "paneldx_domain": domain,
                "origin_type": TdOriginType.KAIZEN_EMERGENT.value,
                "kaizen_ticket_id": str(ticket.id),
                "stat_sprn": "em_analise",
                "gemba_driven": True,
            },
        )
        db.session.add(sprint)
        db.session.flush()

        ticket.workflow_stage = STAGE_CONCLUIDO
        ticket.escalated_to_sprint_id = sprint.id
        db.session.commit()
        db.session.refresh(sprint)
        db.session.refresh(ticket)

        return {
            "ticket": ticket.to_dict(),
            "sprint": sprint.to_dict(),
        }

    def delete_ticket(self, ticket_id: str) -> None:
        ticket = self._get_ticket_or_404(ticket_id)
        db.session.delete(ticket)
        db.session.commit()

    def _get_ticket_or_404(self, ticket_id: str) -> KaizenTicket:
        ticket_uuid = self._parse_uuid(ticket_id, "ticket_id")
        ticket = db.session.get(KaizenTicket, ticket_uuid)
        if not ticket or ticket.tenant_id != self._tenant_id():
            raise ValueError("Ticket Kaizen não encontrado.")
        return ticket

    @staticmethod
    def _tenant_id() -> uuid.UUID:
        tenant_id = getattr(g, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("Contexto de tenant ausente.")
        return tenant_id

    @staticmethod
    def _validate_workflow_stage(stage: str) -> None:
        if stage not in KAIZEN_WORKFLOW_STAGES:
            allowed = ", ".join(KAIZEN_WORKFLOW_STAGES)
            raise ValueError(f"workflow_stage inválido. Use: {allowed}.")

    def _validate_stage_transition_requirements(
        self,
        ticket: KaizenTicket,
        target_stage: str,
        payload: dict[str, Any],
    ) -> None:
        if target_stage == ticket.workflow_stage:
            return

        if target_stage == STAGE_CONTENCAO:
            action = self._optional_text(payload.get("temporary_containment_action"))
            if action is None:
                action = ticket.temporary_containment_action
            if not action:
                raise ValueError("Informe a ação de contenção adotada para avançar para Contenção.")

        if target_stage == STAGE_CINCO_PORQUES:
            rca = self._merge_root_cause(
                payload.get("root_cause_analysis"),
                ticket.root_cause_analysis,
            )
            if not (rca.get("why_1") or rca.get("root_cause")):
                raise ValueError("Preencha a análise dos 5 Porquês antes de avançar para esta fase.")

        if target_stage == STAGE_PADRONIZACAO:
            action = self._optional_text(payload.get("standardization_action"))
            if action is None:
                action = ticket.standardization_action
            if not action:
                raise ValueError(
                    "Informe o novo padrão ou plano de ação definitivo para avançar para Padronização."
                )

        if target_stage == STAGE_CONCLUIDO:
            if "is_operator_retrained" not in payload:
                raise ValueError("Confirme se o operador foi retreinado antes de concluir o ticket.")

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _parse_uuid(value: Any, field: str) -> uuid.UUID:
        try:
            return uuid.UUID(str(value).strip())
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"{field} inválido (UUID esperado).") from exc

    @staticmethod
    def _parse_optional_uuid(value: Any, field: str) -> uuid.UUID | None:
        if value is None or str(value).strip() == "":
            return None
        return KaizenService._parse_uuid(value, field)

    @staticmethod
    def _merge_root_cause(
        incoming: Any,
        existing: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        base = dict(DEFAULT_ROOT_CAUSE_ANALYSIS)
        if existing:
            base.update({k: str(v) for k, v in existing.items() if k in base})
        if isinstance(incoming, dict):
            for key in base:
                if key in incoming and incoming[key] is not None:
                    base[key] = str(incoming[key]).strip()
        return base
