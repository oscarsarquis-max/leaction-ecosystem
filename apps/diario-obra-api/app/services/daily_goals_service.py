"""Recebe metas diárias do Chamelleon e injeta nos rascunhos de RDO."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from app.extensions import db
from app.models import DailyLog, DailyLogStatus, ProjectSite
from app.services.rdo_service import RdoService


class DailyGoalsService:
    def upsert_goals(self, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = str(payload.get("tenant_id") or "").strip()
        project_id_raw = payload.get("project_id")
        goals = payload.get("goals") or []

        if not tenant_id:
            raise ValueError("Campo obrigatório: tenant_id.")
        if not project_id_raw:
            raise ValueError("Campo obrigatório: project_id.")
        if not isinstance(goals, list) or not goals:
            raise ValueError("Informe ao menos uma meta em 'goals'.")

        project_uuid = RdoService._as_uuid(project_id_raw, "project_id")
        site = db.session.get(ProjectSite, project_uuid)
        if not site or site.tenant_id != tenant_id:
            raise ValueError("Canteiro (project_id) não encontrado para o tenant.")

        service = RdoService()
        updated: list[dict[str, str]] = []

        for item in goals:
            if not isinstance(item, dict):
                continue
            log_date = self._parse_date(item.get("date"))
            goal_text = (item.get("sprint_daily_goal") or item.get("goal") or "").strip()
            if not log_date or not goal_text:
                continue

            daily_log = DailyLog.query.filter_by(
                project_id=project_uuid, log_date=log_date
            ).first()

            if daily_log and (daily_log.is_signed or daily_log.status in {
                DailyLogStatus.ASSINADO,
                DailyLogStatus.SINCRONIZADO,
            }):
                continue

            if not daily_log:
                daily_log = DailyLog(
                    project_id=project_uuid,
                    log_date=log_date,
                    status=DailyLogStatus.RASCUNHO,
                    is_signed=False,
                )
                db.session.add(daily_log)
                db.session.flush()

            daily_log.sprint_daily_goal = goal_text
            daily_log.sprint_goal_locked = True
            updated.append({"date": log_date.isoformat(), "log_id": str(daily_log.id)})

        if not updated:
            raise ValueError("Nenhum rascunho elegível para receber metas.")

        db.session.commit()
        return {"updated": updated, "total": len(updated)}

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not value:
            return None
        try:
            text = str(value).strip()
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
