"""Recebe metas diárias do Chamelleon e injeta nos rascunhos de RDO."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.extensions import db
from app.models import DailyLog, DailyLogCommitment, DailyLogStatus, ProjectSite
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

        updated: list[dict[str, str]] = []

        for item in goals:
            if not isinstance(item, dict):
                continue
            log_date = self._parse_date(item.get("date"))
            if not log_date:
                continue

            items_raw = item.get("items")
            # Contrato novo: lista estruturada. Legado: sprint_daily_goal texto único.
            use_items = isinstance(items_raw, list)
            if use_items:
                parsed_items = self._parse_commitment_items(items_raw)
                if not parsed_items:
                    continue
            else:
                goal_text = (item.get("sprint_daily_goal") or item.get("goal") or "").strip()
                if not goal_text:
                    continue
                parsed_items = []

            daily_log = DailyLog.query.filter_by(
                project_id=project_uuid, log_date=log_date
            ).first()

            if daily_log and (
                daily_log.is_signed
                or daily_log.status
                in {
                    DailyLogStatus.ASSINADO,
                    DailyLogStatus.SINCRONIZADO,
                }
            ):
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

            for existing in list(daily_log.commitments):
                db.session.delete(existing)
            daily_log.commitments.clear()
            db.session.flush()

            if use_items:
                new_rows: list[DailyLogCommitment] = []
                for seq, row_data in enumerate(parsed_items):
                    row = DailyLogCommitment(
                        source_commitment_id=row_data["id"],
                        description=row_data["description"],
                        sequence=seq,
                        is_completed=None,
                        note=None,
                    )
                    daily_log.commitments.append(row)
                    new_rows.append(row)
                daily_log.sprint_daily_goal = "\n".join(
                    f"{i + 1}) {row.description}" for i, row in enumerate(new_rows)
                )
            else:
                daily_log.sprint_daily_goal = (
                    item.get("sprint_daily_goal") or item.get("goal") or ""
                ).strip()

            daily_log.sprint_goal_locked = True
            updated.append({"date": log_date.isoformat(), "log_id": str(daily_log.id)})

        if not updated:
            raise ValueError("Nenhum rascunho elegível para receber metas.")

        db.session.commit()
        return {"updated": updated, "total": len(updated)}

    @staticmethod
    def _parse_commitment_items(items_raw: list[Any]) -> list[dict[str, str]]:
        parsed: list[dict[str, str]] = []
        for row in items_raw:
            if isinstance(row, dict):
                description = str(row.get("description") or "").strip()
                source_id = str(row.get("id") or row.get("source_commitment_id") or "").strip()
                if description and source_id:
                    parsed.append({"id": source_id, "description": description})
            else:
                description = str(row or "").strip()
                if description:
                    # Texto solto sem id — sem vínculo ao Chamelleon; descartado.
                    continue
        return parsed

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not value:
            return None
        try:
            text = str(value).strip()
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
