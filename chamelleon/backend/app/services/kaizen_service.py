"""Regras de negócio do módulo Gemba-Kaizen."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from flask import g

from app.database.models import db
from app.models.kaizen_models import (
    DEFAULT_ROOT_CAUSE_ANALYSIS,
    KAIZEN_SEVERITIES,
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
    def list_tickets(
        self,
        *,
        workflow_stage: str | None = None,
        operational_site_id: str | None = None,
    ) -> list[dict[str, Any]]:
        tenant_id = self._tenant_id()
        query = KaizenTicket.query.filter_by(tenant_id=tenant_id)
        if workflow_stage:
            self._validate_workflow_stage(workflow_stage)
            query = query.filter_by(workflow_stage=workflow_stage)
        if operational_site_id:
            query = query.filter_by(
                operational_site_id=self._parse_uuid(operational_site_id, "operational_site_id")
            )
        tickets = query.order_by(
            KaizenTicket.workflow_stage.asc(),
            KaizenTicket.updated_at.desc(),
        ).all()
        return self._enrich([ticket.to_dict() for ticket in tickets])

    def list_tickets_kanban(
        self, *, operational_site_id: str | None = None
    ) -> dict[str, list[dict[str, Any]]]:
        tenant_id = self._tenant_id()
        query = KaizenTicket.query.filter_by(tenant_id=tenant_id)
        if operational_site_id:
            query = query.filter_by(
                operational_site_id=self._parse_uuid(operational_site_id, "operational_site_id")
            )
        tickets = query.order_by(KaizenTicket.updated_at.desc()).all()
        board: dict[str, list[dict[str, Any]]] = {
            stage: [] for stage in KAIZEN_WORKFLOW_STAGES
        }
        for ticket in tickets:
            stage = ticket.workflow_stage
            if stage not in board:
                board[stage] = []
            board[stage].append(ticket.to_dict())
        for stage, items in board.items():
            board[stage] = self._enrich(items)
        return board

    def get_ticket(self, ticket_id: str) -> dict[str, Any]:
        ticket = self._get_ticket_or_404(ticket_id)
        return self._enrich([ticket.to_dict()])[0]

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
            operational_site_id=self._resolve_operational_site_id(
                payload.get("operational_site_id")
            ),
            severity=self._parse_optional_severity(payload.get("severity")),
            title=title,
            description=self._optional_text(payload.get("description")),
            workflow_stage=workflow_stage,
            temporary_containment_action=self._optional_text(
                payload.get("temporary_containment_action")
            ),
            root_cause_analysis=self._merge_root_cause(payload.get("root_cause_analysis")),
            standardization_action=self._optional_text(payload.get("standardization_action")),
            is_operator_retrained=bool(payload.get("is_operator_retrained", False)),
            owner_user_id=self._resolve_owner_user_id(payload.get("owner_user_id")),
            due_date=self._parse_optional_date(payload.get("due_date")),
        )
        db.session.add(ticket)
        db.session.flush()
        from app.services.compliance_service import ComplianceService

        ComplianceService().sync_ticket_best_effort(ticket)
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

        if "operational_site_id" in payload:
            ticket.operational_site_id = self._resolve_operational_site_id(
                payload.get("operational_site_id")
            )

        if "severity" in payload:
            ticket.severity = self._parse_optional_severity(payload.get("severity"))

        if "owner_user_id" in payload:
            ticket.owner_user_id = self._resolve_owner_user_id(payload.get("owner_user_id"))

        if "due_date" in payload:
            ticket.due_date = self._parse_optional_date(payload.get("due_date"))

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

        from app.services.compliance_service import ComplianceService

        ComplianceService().sync_ticket_best_effort(ticket)
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
        from app.services.compliance_service import ComplianceService

        ComplianceService().sync_ticket_best_effort(ticket)
        db.session.commit()
        db.session.refresh(sprint)
        db.session.refresh(ticket)

        return {
            "ticket": self._enrich([ticket.to_dict()])[0],
            "sprint": sprint.to_dict(),
        }

    def delete_ticket(self, ticket_id: str) -> None:
        ticket = self._get_ticket_or_404(ticket_id)
        db.session.delete(ticket)
        db.session.commit()

    def _enrich(self, tickets_dicts: list[dict]) -> list[dict]:
        from app.database.models import User
        from app.models.operational_models import OperationalSite

        site_ids = {t["operational_site_id"] for t in tickets_dicts if t.get("operational_site_id")}
        owner_ids = {t["owner_user_id"] for t in tickets_dicts if t.get("owner_user_id")}
        sites = (
            {
                str(s.id): s.name
                for s in OperationalSite.query.filter(OperationalSite.id.in_(site_ids)).all()
            }
            if site_ids
            else {}
        )
        owners = (
            {
                str(u.id): u.name
                for u in User.query.filter(User.id.in_(owner_ids)).all()
            }
            if owner_ids
            else {}
        )
        for t in tickets_dicts:
            t["operational_site_name"] = sites.get(t.get("operational_site_id"))
            t["owner_name"] = owners.get(t.get("owner_user_id"))
        return tickets_dicts

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

            owner_user_id = payload.get("owner_user_id") or (
                str(ticket.owner_user_id) if ticket.owner_user_id else None
            )
            if not owner_user_id:
                raise ValueError("Defina um responsável antes de avançar para Contenção.")

            due_date = payload.get("due_date") or (
                ticket.due_date.isoformat() if ticket.due_date else None
            )
            if not due_date:
                raise ValueError("Defina um prazo antes de avançar para Contenção.")

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

    def _resolve_operational_site_id(self, value: Any) -> uuid.UUID | None:
        site_id = self._parse_optional_uuid(value, "operational_site_id")
        if not site_id:
            return None
        from app.models.operational_models import OperationalSite

        site = OperationalSite.query.filter_by(
            id=site_id, tenant_id=self._tenant_id()
        ).first()
        if not site:
            raise ValueError("operational_site_id inválido ou de outro tenant.")
        return site_id

    def _resolve_owner_user_id(self, value: Any) -> uuid.UUID | None:
        user_id = self._parse_optional_uuid(value, "owner_user_id")
        if not user_id:
            return None
        from app.database.models import TenantUser

        membership = TenantUser.query.filter_by(
            tenant_id=self._tenant_id(), user_id=user_id
        ).first()
        if not membership:
            raise ValueError("owner_user_id inválido ou de outro tenant.")
        return user_id

    @staticmethod
    def _parse_optional_severity(value: Any) -> str | None:
        if value is None or str(value).strip() == "":
            return None
        severity = str(value).strip()
        if severity not in KAIZEN_SEVERITIES:
            allowed = ", ".join(KAIZEN_SEVERITIES)
            raise ValueError(f"severity inválida. Use: {allowed}.")
        return severity

    @staticmethod
    def _parse_optional_date(value: Any) -> date | None:
        if value is None or str(value).strip() == "":
            return None
        try:
            return date.fromisoformat(str(value).strip()[:10])
        except ValueError as exc:
            raise ValueError("due_date inválida (use YYYY-MM-DD).") from exc

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
