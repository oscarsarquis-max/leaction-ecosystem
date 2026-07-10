"""Regras de negócio do módulo Transformação Digital (TD)."""

from __future__ import annotations

import uuid
from typing import Any

from flask import g

from app.core.td_constants import TD_GENESE_MAX_SPRINTS
from app.database.models import db
from app.models.td_models import (
    TD_KANBAN_BOARD_STAGES,
    TD_KANBAN_STAGES,
    TD_ORIGIN_TYPES,
    TdKanbanStage,
    TdOriginType,
    TdPlan,
    TdSprint,
)


class TdService:
    def get_active_plan(self, *, include_sprints: bool = True) -> dict[str, Any] | None:
        plan = self._active_plan()
        if not plan:
            return None
        return plan.to_dict(include_sprints=include_sprints)

    def create_or_update_plan(self, payload: dict[str, Any]) -> TdPlan:
        tenant_id = self._tenant_id()
        survey_snapshot = payload.get("survey_snapshot")
        if survey_snapshot is not None and not isinstance(survey_snapshot, dict):
            raise ValueError("survey_snapshot deve ser um objeto JSON.")

        plan = self._active_plan()
        if plan:
            if survey_snapshot is not None:
                plan.survey_snapshot = survey_snapshot
            if "is_active" in payload:
                plan.is_active = bool(payload.get("is_active"))
        else:
            plan = TdPlan(
                tenant_id=tenant_id,
                survey_snapshot=survey_snapshot or {},
                is_active=True,
            )
            db.session.add(plan)

        # Opcional: substituir sprints do plano em uma única operação (pré-IA)
        if "sprints" in payload:
            if not isinstance(payload["sprints"], list):
                raise ValueError("sprints deve ser uma lista.")
            for existing in list(plan.sprints):
                db.session.delete(existing)
            db.session.flush()
            for item in payload["sprints"]:
                self._build_sprint(plan=plan, tenant_id=tenant_id, payload=item or {})

        db.session.commit()
        db.session.refresh(plan)
        return plan

    def list_sprints(
        self,
        *,
        kanban_stage: str | None = None,
        plan_id: str | None = None,
        board_only: bool = False,
    ) -> list[dict[str, Any]]:
        tenant_id = self._tenant_id()
        query = TdSprint.query.filter_by(tenant_id=tenant_id)

        if plan_id:
            query = query.filter_by(plan_id=self._as_uuid(plan_id, "plan_id"))
        else:
            active = self._active_plan()
            if active:
                query = query.filter_by(plan_id=active.id)

        if board_only:
            query = query.filter(TdSprint.kanban_stage.in_(TD_KANBAN_BOARD_STAGES))
        elif kanban_stage:
            self._validate_stage(kanban_stage)
            query = query.filter_by(kanban_stage=kanban_stage)

        sprints = query.order_by(
            TdSprint.paneldx_domain.asc(),
            TdSprint.updated_at.desc(),
        ).all()
        return [sprint.to_dict() for sprint in sprints]

    def list_kanban(self) -> dict[str, list[dict[str, Any]]]:
        board: dict[str, list[dict[str, Any]]] = {
            stage: [] for stage in TD_KANBAN_BOARD_STAGES
        }
        for sprint in self.list_sprints(board_only=True):
            stage = sprint["kanban_stage"]
            if stage not in board:
                board[stage] = []
            board[stage].append(sprint)
        return board

    def create_sprint(self, payload: dict[str, Any]) -> TdSprint:
        tenant_id = self._tenant_id()
        plan = self._resolve_plan_for_write(payload.get("plan_id"))
        sprint = self._build_sprint(plan=plan, tenant_id=tenant_id, payload=payload)
        db.session.add(sprint)
        db.session.commit()
        db.session.refresh(sprint)
        return sprint

    def update_sprint(self, sprint_id: str, payload: dict[str, Any]) -> TdSprint:
        sprint = self._get_sprint_or_404(sprint_id)

        if "title" in payload:
            title = str(payload.get("title") or "").strip()
            if not title:
                raise ValueError("title não pode ser vazio.")
            sprint.title = title

        if "description" in payload:
            sprint.description = self._optional_text(payload.get("description"))

        if "paneldx_domain" in payload:
            domain = str(payload.get("paneldx_domain") or "").strip()
            if not domain:
                raise ValueError("paneldx_domain não pode ser vazio.")
            sprint.paneldx_domain = domain

        if "origin_type" in payload:
            origin = str(payload.get("origin_type") or "").strip()
            self._validate_origin(origin)
            sprint.origin_type = origin

        if "kanban_stage" in payload:
            stage = str(payload.get("kanban_stage") or "").strip()
            self._validate_stage(stage)
            if (
                stage in TD_KANBAN_BOARD_STAGES
                and sprint.kanban_stage == TdKanbanStage.BACKLOG.value
                and stage != TdKanbanStage.BACKLOG.value
            ):
                if self._count_board_sprints(exclude_sprint_id=sprint.id) >= TD_GENESE_MAX_SPRINTS:
                    raise ValueError(
                        f"O Kanban já possui {TD_GENESE_MAX_SPRINTS} sprints ativas. "
                        "Conclua ou devolva uma sprint antes de promover outra."
                    )
            sprint.kanban_stage = stage
            goals = dict(sprint.goals_payload or {})
            goals["stat_sprn"] = self._panel_status_for_stage(stage)
            sprint.goals_payload = goals

        if "goals_payload" in payload:
            goals = payload.get("goals_payload")
            if goals is not None and not isinstance(goals, dict):
                raise ValueError("goals_payload deve ser um objeto JSON.")
            merged = dict(sprint.goals_payload or {})
            merged.update(goals or {})
            sprint.goals_payload = merged

        if "exec_notes" in payload:
            merged = dict(sprint.goals_payload or {})
            merged["exec_notes"] = self._optional_text(payload.get("exec_notes"))
            sprint.goals_payload = merged

        db.session.commit()
        db.session.refresh(sprint)
        return sprint

    def promote_sprint_to_planning(self, sprint_id: str) -> TdSprint:
        """Backlog do Plano Geral → coluna Planejadas no Kanban (PanelDX)."""
        sprint = self._get_sprint_or_404(sprint_id)
        if sprint.kanban_stage != TdKanbanStage.BACKLOG.value:
            raise ValueError("Somente sprints em Backlog podem ser promovidas ao planejamento.")
        if self._count_board_sprints() >= TD_GENESE_MAX_SPRINTS:
            raise ValueError(
                f"Limite de {TD_GENESE_MAX_SPRINTS} sprints no Kanban atingido. "
                "Conclua ou reorganize o quadro antes de promover outra sprint."
            )
        return self.update_sprint(
            sprint_id,
            {"kanban_stage": TdKanbanStage.PLANEJADA.value},
        )

    def _count_board_sprints(self, *, exclude_sprint_id: uuid.UUID | None = None) -> int:
        tenant_id = self._tenant_id()
        query = TdSprint.query.filter(
            TdSprint.tenant_id == tenant_id,
            TdSprint.kanban_stage.in_(TD_KANBAN_BOARD_STAGES),
        )
        if exclude_sprint_id:
            query = query.filter(TdSprint.id != exclude_sprint_id)
        return query.count()

    @staticmethod
    def _panel_status_for_stage(stage: str) -> str:
        mapping = {
            TdKanbanStage.BACKLOG.value: "planejada_backlog",
            TdKanbanStage.KAIZEN_ENTRADA.value: "em_analise",
            TdKanbanStage.PLANEJADA.value: "planejada_backlog",
            TdKanbanStage.EXECUCAO.value: "em_andamento",
            TdKanbanStage.CONCLUIDA.value: "concluida",
        }
        return mapping.get(stage, "planejada_backlog")

    def get_readiness_status(self) -> dict[str, Any]:
        from app.services.client_journey_service import build_td_readiness_status

        return build_td_readiness_status(self._tenant_id())

    def _build_sprint(
        self,
        *,
        plan: TdPlan,
        tenant_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> TdSprint:
        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("Campo obrigatório: title.")

        domain = str(payload.get("paneldx_domain") or "").strip()
        if not domain:
            raise ValueError("Campo obrigatório: paneldx_domain.")

        origin = str(payload.get("origin_type") or TdOriginType.BASELINE.value).strip()
        self._validate_origin(origin)

        stage = str(payload.get("kanban_stage") or TdKanbanStage.BACKLOG.value).strip()
        self._validate_stage(stage)

        goals = payload.get("goals_payload")
        if goals is not None and not isinstance(goals, dict):
            raise ValueError("goals_payload deve ser um objeto JSON.")

        return TdSprint(
            tenant_id=tenant_id,
            plan_id=plan.id,
            title=title,
            description=self._optional_text(payload.get("description")),
            paneldx_domain=domain,
            origin_type=origin,
            kanban_stage=stage,
            goals_payload=goals or {},
        )

    def _active_plan(self) -> TdPlan | None:
        tenant_id = self._tenant_id()
        return (
            TdPlan.query.filter_by(tenant_id=tenant_id, is_active=True)
            .order_by(TdPlan.created_at.desc())
            .first()
        )

    def _resolve_plan_for_write(self, plan_id: Any) -> TdPlan:
        tenant_id = self._tenant_id()
        if plan_id:
            plan = db.session.get(TdPlan, self._as_uuid(plan_id, "plan_id"))
            if not plan or plan.tenant_id != tenant_id:
                raise ValueError("plan_id inválido ou de outro tenant.")
            return plan

        plan = self._active_plan()
        if plan:
            return plan

        plan = TdPlan(tenant_id=tenant_id, survey_snapshot={}, is_active=True)
        db.session.add(plan)
        db.session.flush()
        return plan

    def _get_sprint_or_404(self, sprint_id: str) -> TdSprint:
        sprint = db.session.get(TdSprint, self._as_uuid(sprint_id, "sprint_id"))
        if not sprint or sprint.tenant_id != self._tenant_id():
            raise ValueError("Sprint não encontrada.")
        return sprint

    def _tenant_id(self) -> uuid.UUID:
        tenant_id = getattr(g, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("Contexto de tenant ausente.")
        if isinstance(tenant_id, uuid.UUID):
            return tenant_id
        return uuid.UUID(str(tenant_id))

    @staticmethod
    def _as_uuid(value: Any, field: str) -> uuid.UUID:
        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} inválido.") from exc

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _validate_stage(stage: str) -> None:
        if stage not in TD_KANBAN_STAGES:
            raise ValueError(
                f"kanban_stage inválido. Use um de: {', '.join(TD_KANBAN_STAGES)}"
            )

    @staticmethod
    def _validate_origin(origin: str) -> None:
        if origin not in TD_ORIGIN_TYPES:
            raise ValueError(
                f"origin_type inválido. Use um de: {', '.join(TD_ORIGIN_TYPES)}"
            )
