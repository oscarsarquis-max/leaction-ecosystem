"""Regras de negócio do RDO (Gemba)."""

from __future__ import annotations

import calendar
import uuid
from datetime import date, datetime, timezone
from typing import Any

from app.extensions import db
from app.models import (
    DailyLog,
    DailyLogStatus,
    EquipmentOperationalStatus,
    EquipmentStatus,
    ExecutedService,
    Occurrence,
    OccurrenceType,
    ProjectSite,
    WeatherPeriod,
    Workforce,
    WorkforceType,
)

FINALIZED_STATUSES = {DailyLogStatus.ASSINADO, DailyLogStatus.SINCRONIZADO}


class RdoService:
    def create_site(self, payload: dict[str, Any]) -> ProjectSite:
        tenant_id = str(payload.get("tenant_id") or "").strip()
        name = str(payload.get("name") or "").strip()
        if not tenant_id:
            raise ValueError("Campo obrigatório: tenant_id.")
        if not name:
            raise ValueError("Campo obrigatório: name.")

        site = ProjectSite(
            tenant_id=tenant_id,
            name=name,
            location=(payload.get("location") or "").strip() or None,
            rt_engineer_name=(payload.get("rt_engineer_name") or "").strip() or None,
        )
        db.session.add(site)
        db.session.commit()
        return site

    def list_sites(self, tenant_id: str | None = None) -> list[ProjectSite]:
        query = ProjectSite.query
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id.strip())
        return query.order_by(ProjectSite.name.asc(), ProjectSite.created_at.desc()).all()

    def serialize_site(self, site: ProjectSite) -> dict[str, Any]:
        return {
            "id": str(site.id),
            "tenant_id": site.tenant_id,
            "name": site.name,
            "location": site.location,
            "rt_engineer_name": site.rt_engineer_name,
            "created_at": site.created_at.isoformat() if site.created_at else None,
        }

    def get_month_calendar(
        self, project_id: uuid.UUID | str, year: int, month: int
    ) -> dict[str, Any]:
        project_uuid = self._as_uuid(project_id, "project_id")
        if not db.session.get(ProjectSite, project_uuid):
            raise ValueError("Canteiro (project_id) não encontrado.")
        if month < 1 or month > 12:
            raise ValueError("Mês inválido.")

        start = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end = date(year, month, last_day)

        logs = DailyLog.query.filter(
            DailyLog.project_id == project_uuid,
            DailyLog.log_date >= start,
            DailyLog.log_date <= end,
        ).all()
        by_date = {log.log_date.isoformat(): log for log in logs}

        days: list[dict[str, Any]] = []
        for day_num in range(1, last_day + 1):
            iso = date(year, month, day_num).isoformat()
            log = by_date.get(iso)
            if not log:
                calendar_status = "empty"
            elif log.status in FINALIZED_STATUSES or log.is_signed:
                calendar_status = "finalized"
            else:
                calendar_status = "draft"

            days.append(
                {
                    "date": iso,
                    "calendar_status": calendar_status,
                    "status": log.status.value if log else None,
                    "log_id": str(log.id) if log else None,
                    "is_editable": self.is_log_editable(log, date.fromisoformat(iso)),
                }
            )

        return {"year": year, "month": month, "project_id": str(project_uuid), "days": days}

    def get_log_by_date(self, project_id: uuid.UUID | str, log_date: date) -> DailyLog | None:
        project_uuid = self._as_uuid(project_id, "project_id")
        return DailyLog.query.filter_by(project_id=project_uuid, log_date=log_date).first()

    def create_draft_log(self, payload: dict[str, Any]) -> DailyLog:
        project_id = self._as_uuid(payload.get("project_id"), "project_id")
        if not db.session.get(ProjectSite, project_id):
            raise ValueError("Canteiro (project_id) não encontrado.")

        log_date = self._parse_date(payload.get("date") or payload.get("log_date"))
        if not log_date:
            raise ValueError("Campo obrigatório: date (YYYY-MM-DD).")

        if log_date != date.today():
            raise ValueError("Só é permitido criar RDO para a data de hoje.")

        existing = DailyLog.query.filter_by(project_id=project_id, log_date=log_date).first()
        if existing:
            if self.is_log_editable(existing, log_date):
                return self.update_log(str(existing.id), payload)
            raise ValueError(f"Já existe RDO para este canteiro na data {log_date.isoformat()}.")

        daily_log = DailyLog(
            project_id=project_id,
            log_date=log_date,
            status=DailyLogStatus.RASCUNHO,
            is_signed=False,
        )
        db.session.add(daily_log)
        db.session.flush()
        self._apply_payload_to_log(daily_log, payload)
        db.session.commit()
        return daily_log

    def update_log(self, log_id: uuid.UUID | str, payload: dict[str, Any]) -> DailyLog:
        log_uuid = self._as_uuid(log_id, "log_id")
        daily_log = db.session.get(DailyLog, log_uuid)
        if not daily_log:
            raise ValueError("RDO não encontrado.")

        self._assert_editable(daily_log)
        finalize = bool(payload.get("finalize"))
        self._apply_payload_to_log(daily_log, payload)
        db.session.commit()
        if finalize:
            self._emit_hub_webhook(daily_log)
        return daily_log

    def list_logs_by_project(self, project_id: uuid.UUID | str) -> list[DailyLog]:
        project_uuid = self._as_uuid(project_id, "project_id")
        if not db.session.get(ProjectSite, project_uuid):
            raise ValueError("Canteiro (project_id) não encontrado.")

        return (
            DailyLog.query.filter_by(project_id=project_uuid)
            .order_by(DailyLog.log_date.desc(), DailyLog.created_at.desc())
            .all()
        )

    def is_log_editable(self, log: DailyLog | None, log_date: date) -> bool:
        if not log:
            return log_date == date.today()
        if log_date != date.today():
            return False
        if log.status in FINALIZED_STATUSES or log.is_signed:
            return False
        return log.status == DailyLogStatus.RASCUNHO

    def _assert_editable(self, log: DailyLog) -> None:
        if log.status in FINALIZED_STATUSES or log.is_signed:
            raise ValueError("RDO finalizado não pode ser alterado.")
        if log.log_date != date.today():
            raise ValueError("RDO de dias anteriores é somente leitura.")
        if log.status != DailyLogStatus.RASCUNHO:
            raise ValueError("Somente RDOs em Rascunho podem ser editados.")

    def serialize_log(self, log: DailyLog) -> dict[str, Any]:
        return {
            "id": str(log.id),
            "project_id": str(log.project_id),
            "date": log.log_date.isoformat(),
            "weather_morning": log.weather_morning.value if log.weather_morning else None,
            "weather_afternoon": log.weather_afternoon.value if log.weather_afternoon else None,
            "status": log.status.value,
            "technical_comments": log.technical_comments,
            "ppe_compliant": log.ppe_compliant,
            "ppe_compliant_details": log.ppe_compliant_details,
            "delay_waiting_material": log.delay_waiting_material,
            "delay_rework": log.delay_rework,
            "delay_lack_of_front": log.delay_lack_of_front,
            "end_shift_clean": log.end_shift_clean,
            "end_shift_tools_stored": log.end_shift_tools_stored,
            "end_shift_loose_materials": log.end_shift_loose_materials,
            "sprint_daily_goal": log.sprint_daily_goal,
            "sprint_goal_locked": bool(log.sprint_goal_locked),
            "goal_achieved": log.goal_achieved,
            "impediment_details": log.impediment_details,
            "mitigation_action": log.mitigation_action,
            "preventive_action": log.preventive_action,
            "supplies": log.supplies_data or [],
            "is_signed": log.is_signed,
            "signed_by": log.signed_by,
            "signed_at": log.signed_at.isoformat() if log.signed_at else None,
            "is_editable": self.is_log_editable(log, log.log_date),
            "calendar_status": (
                "finalized"
                if log.status in FINALIZED_STATUSES or log.is_signed
                else "draft"
            ),
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "updated_at": log.updated_at.isoformat() if log.updated_at else None,
            "workforce": [
                {
                    "id": str(row.id),
                    "role": row.role,
                    "headcount": row.headcount,
                    "type": row.workforce_type.value,
                    "company_name": row.company_name,
                    "presence_details": row.presence_details,
                    "absences_count": row.absences_count or row.absences or 0,
                    "absences_details": row.absences_details,
                    "extra_hours_count": row.extra_hours_count or row.overtime_hours or 0,
                    "extra_hours_details": row.extra_hours_details,
                    "general_remarks": row.general_remarks,
                }
                for row in log.workforce
            ],
            "equipment_statuses": [
                {
                    "id": str(row.id),
                    "equipment_name": row.equipment_name,
                    "status": row.status.value,
                    "quantity": row.quantity or 0,
                    "remarks": row.remarks,
                }
                for row in log.equipment_statuses
            ],
            "executed_services": [
                {
                    "id": str(row.id),
                    "description": row.description,
                    "location_on_site": row.location_on_site,
                    "remarks": row.remarks,
                }
                for row in log.executed_services
            ],
            "occurrences": [
                {
                    "id": str(row.id),
                    "type": row.type.value,
                    "exact_location": row.exact_location,
                    "what_happened": row.what_happened,
                    "immediate_action_taken": row.immediate_action_taken,
                    "photo_url": row.photo_url,
                    "safety_ppe_notes": row.safety_ppe_notes,
                }
                for row in log.occurrences
            ],
        }

    def _apply_payload_to_log(self, daily_log: DailyLog, payload: dict[str, Any]) -> None:
        if "weather_morning" in payload:
            daily_log.weather_morning = self._parse_weather(payload.get("weather_morning"))
        if "weather_afternoon" in payload:
            daily_log.weather_afternoon = self._parse_weather(payload.get("weather_afternoon"))
        if "technical_comments" in payload:
            daily_log.technical_comments = (payload.get("technical_comments") or "").strip() or None
        if "ppe_compliant" in payload:
            val = payload.get("ppe_compliant")
            daily_log.ppe_compliant = bool(val) if val is not None else None
        if "ppe_compliant_details" in payload:
            raw = payload.get("ppe_compliant_details")
            daily_log.ppe_compliant_details = (raw or "").strip() or None
        if "delay_waiting_material" in payload:
            daily_log.delay_waiting_material = bool(payload.get("delay_waiting_material"))
        if "delay_rework" in payload:
            daily_log.delay_rework = bool(payload.get("delay_rework"))
        if "delay_lack_of_front" in payload:
            daily_log.delay_lack_of_front = bool(payload.get("delay_lack_of_front"))
        if "end_shift_clean" in payload:
            val = payload.get("end_shift_clean")
            daily_log.end_shift_clean = None if val is None else bool(val)
        if "end_shift_tools_stored" in payload:
            val = payload.get("end_shift_tools_stored")
            daily_log.end_shift_tools_stored = None if val is None else bool(val)
        if "end_shift_loose_materials" in payload:
            val = payload.get("end_shift_loose_materials")
            daily_log.end_shift_loose_materials = None if val is None else bool(val)
        if "sprint_daily_goal" in payload and not daily_log.sprint_goal_locked:
            raw = payload.get("sprint_daily_goal")
            daily_log.sprint_daily_goal = (raw or "").strip() or None
        if "goal_achieved" in payload:
            val = payload.get("goal_achieved")
            daily_log.goal_achieved = None if val is None else bool(val)
        if "impediment_details" in payload:
            raw = payload.get("impediment_details")
            daily_log.impediment_details = (raw or "").strip() or None
        if "mitigation_action" in payload:
            raw = payload.get("mitigation_action")
            daily_log.mitigation_action = (raw or "").strip() or None
        if "preventive_action" in payload:
            raw = payload.get("preventive_action")
            daily_log.preventive_action = (raw or "").strip() or None
        if "supplies" in payload:
            daily_log.supplies_data = payload.get("supplies") or []

        if any(k in payload for k in ("workforce", "equipment_statuses", "executed_services", "occurrences")):
            self._replace_nested_collections(daily_log, payload)

        if payload.get("finalize"):
            signed_by = (payload.get("signed_by") or "").strip() or "Encarregado de obra"
            self._finalize_log(daily_log, signed_by)

    def _replace_nested_collections(self, daily_log: DailyLog, payload: dict[str, Any]) -> None:
        if "workforce" in payload:
            for row in list(daily_log.workforce):
                db.session.delete(row)
            for item in payload.get("workforce") or []:
                absences_count = int(
                    item.get("absences_count") if item.get("absences_count") is not None else item.get("absences") or 0
                )
                extra_hours_count = int(
                    item.get("extra_hours_count")
                    if item.get("extra_hours_count") is not None
                    else item.get("overtime_hours") or 0
                )
                daily_log.workforce.append(
                    Workforce(
                        role=str(item.get("role") or "").strip() or "Não informado",
                        headcount=int(item.get("headcount") or 0),
                        workforce_type=self._parse_workforce_type(item.get("type")),
                        company_name=(item.get("company_name") or "").strip() or None,
                        presence_details=(item.get("presence_details") or "").strip() or None,
                        absences_count=absences_count,
                        absences_details=(item.get("absences_details") or "").strip() or None,
                        extra_hours_count=extra_hours_count,
                        extra_hours_details=(item.get("extra_hours_details") or "").strip() or None,
                        general_remarks=(item.get("general_remarks") or "").strip() or None,
                        overtime_hours=extra_hours_count,
                        absences=absences_count,
                    )
                )

        if "equipment_statuses" in payload:
            for row in list(daily_log.equipment_statuses):
                db.session.delete(row)
            for item in payload.get("equipment_statuses") or []:
                status_raw = item.get("status")
                quantity = int(item.get("quantity") or 0)
                if not status_raw or quantity <= 0:
                    continue
                daily_log.equipment_statuses.append(
                    EquipmentStatus(
                        equipment_name=str(item.get("equipment_name") or "").strip() or "Equipamento",
                        status=EquipmentOperationalStatus(status_raw),
                        quantity=quantity,
                        remarks=(item.get("remarks") or item.get("details") or "").strip() or None,
                    )
                )

        if "executed_services" in payload:
            for row in list(daily_log.executed_services):
                db.session.delete(row)
            for item in payload.get("executed_services") or []:
                description = (item.get("description") or "").strip()
                if not description:
                    continue
                daily_log.executed_services.append(
                    ExecutedService(
                        description=description,
                        location_on_site=(item.get("location_on_site") or "").strip() or None,
                        remarks=(item.get("remarks") or item.get("details") or "").strip() or None,
                    )
                )

        if "occurrences" in payload:
            for row in list(daily_log.occurrences):
                db.session.delete(row)
            for item in payload.get("occurrences") or []:
                type_raw = item.get("type")
                what_happened = (
                    (item.get("what_happened") or item.get("description") or "").strip()
                )
                exact_location = (item.get("exact_location") or "").strip()
                if not type_raw or not what_happened:
                    continue
                if not exact_location:
                    exact_location = "Não informado"
                daily_log.occurrences.append(
                    Occurrence(
                        type=OccurrenceType(type_raw),
                        exact_location=exact_location,
                        what_happened=what_happened,
                        description=what_happened,
                        immediate_action_taken=(
                            (item.get("immediate_action_taken") or "").strip() or None
                        ),
                        photo_url=(item.get("photo_url") or "").strip() or None,
                        safety_ppe_notes=(item.get("safety_ppe_notes") or "").strip() or None,
                    )
                )

    def _finalize_log(self, daily_log: DailyLog, signed_by: str) -> None:
        # Compatibilidade: Daily Ágil só é obrigatória quando há meta planejada
        # (ou o encarregado já começou a responder). RDOs legados sem meta seguem
        # o fluxo anterior (fechamento de turnos) sem quebrar assinaturas.
        daily_required = bool(
            (daily_log.sprint_daily_goal or "").strip()
            or daily_log.sprint_goal_locked
            or daily_log.goal_achieved is not None
            or (daily_log.impediment_details or "").strip()
            or (daily_log.mitigation_action or "").strip()
            or (daily_log.preventive_action or "").strip()
        )
        if daily_required and daily_log.goal_achieved is None:
            raise ValueError("Responda se a meta do dia foi atingida (Daily Ágil) antes de assinar.")
        if daily_log.end_shift_clean is None:
            raise ValueError("Responda o fechamento do canteiro antes de assinar.")
        if daily_log.end_shift_tools_stored is None:
            raise ValueError("Informe se as ferramentas foram recolhidas.")
        if daily_log.end_shift_loose_materials is None:
            raise ValueError("Informe se ficou material solto no tempo.")
        daily_log.is_signed = True
        daily_log.status = DailyLogStatus.ASSINADO
        daily_log.signed_by = signed_by
        daily_log.signed_at = datetime.now(timezone.utc)

    def _emit_hub_webhook(self, daily_log: DailyLog) -> None:
        """Notifica o hub; falha de rede/config não impede a assinatura local."""
        try:
            from app.services.hub_webhook_client import (
                EVENT_TYPE_RDO_FINALIZED,
                SOURCE_APP,
                HubWebhookClient,
            )

            site = daily_log.project
            if not site:
                return

            rdo_body = self.serialize_log(daily_log)
            payload = {
                "tenant_id": site.tenant_id,
                "source_app": SOURCE_APP,
                "event_type": EVENT_TYPE_RDO_FINALIZED,
                "event_date": daily_log.log_date.isoformat(),
                "project_id": str(daily_log.project_id),
                "rdo": rdo_body,
            }
            HubWebhookClient().notify_rdo_signed(payload)
        except Exception:
            # Compatibilidade: RDO assinado localmente mesmo se o hub estiver indisponível
            import logging

            logging.getLogger(__name__).exception(
                "Webhook Chamelleon falhou após assinatura (RDO %s)", daily_log.id
            )

    @staticmethod
    def _parse_weather(value: Any) -> WeatherPeriod | None:
        if value is None or value == "":
            return None
        return WeatherPeriod(str(value).upper())

    @staticmethod
    def _parse_workforce_type(value: Any) -> WorkforceType:
        if not value:
            return WorkforceType.PROPRIA
        normalized = str(value).strip()
        if normalized.lower().startswith("terc"):
            return WorkforceType.TERCEIRIZADA
        return WorkforceType.PROPRIA

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not value:
            return None
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    @staticmethod
    def _as_uuid(value: Any, field_name: str) -> uuid.UUID:
        if value is None:
            raise ValueError(f"Campo obrigatório ausente: {field_name}.")
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"UUID inválido em '{field_name}': {value}") from exc
