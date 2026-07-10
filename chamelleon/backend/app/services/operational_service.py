"""Serviço operacional — unidades, planejamento e relatórios de execução."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from flask import g

from app.core.rbac.constants import ROLE_LED
from app.database.models import TenantUser, db
from app.models.operational_models import (
    INDUSTRY_CONSTRUCAO,
    DailyExecutionReport,
    IndustryType,
    OperationalSite,
)
from app.services.satellite_client import SatelliteClient


class OperationalService:
    def list_sites(self) -> list[dict[str, Any]]:
        tenant_id = g.tenant_id
        sites = (
            OperationalSite.query.filter_by(tenant_id=tenant_id, is_active=True)
            .order_by(OperationalSite.name.asc())
            .all()
        )
        return [self._site_dict(site) for site in sites]

    def create_site(self, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = g.tenant_id
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValueError("Nome da unidade operacional é obrigatório.")

        duplicate = (
            OperationalSite.query.filter_by(tenant_id=tenant_id, is_active=True)
            .filter(db.func.lower(OperationalSite.name) == name.lower())
            .first()
        )
        if duplicate:
            raise ValueError("Já existe uma unidade operacional com este nome.")

        industry_type = self._parse_industry_type(payload.get("industry_type"))
        manager_id = self._resolve_manager_id(payload.get("manager_id"))
        location = (payload.get("location") or "").strip() or None

        site = OperationalSite(
            tenant_id=tenant_id,
            name=name,
            location=location,
            industry_type=industry_type.value if isinstance(industry_type, IndustryType) else str(industry_type),
            manager_id=manager_id,
        )
        db.session.add(site)
        db.session.flush()

        sync_warning = None
        if self._is_construction(industry_type):
            sync_warning = self._try_sync_satellite(site)

        db.session.commit()
        result = self._site_dict(site)
        if sync_warning:
            result["sync_warning"] = sync_warning
            result["satellite_sync_pending"] = True
        return result

    def update_site(self, site_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        site = self._get_site(site_id)
        if "name" in payload and payload["name"]:
            site.name = str(payload["name"]).strip()
        if "location" in payload:
            site.location = (payload.get("location") or "").strip() or None
        if "industry_type" in payload and payload["industry_type"]:
            parsed = self._parse_industry_type(payload.get("industry_type"))
            site.industry_type = parsed.value if isinstance(parsed, IndustryType) else str(parsed)
        if "manager_id" in payload:
            site.manager_id = self._resolve_manager_id(payload.get("manager_id"))
        if "is_active" in payload:
            site.is_active = bool(payload["is_active"])
        db.session.commit()
        return self._site_dict(site)

    def delete_site(self, site_id: str) -> None:
        site = self._get_site(site_id)
        site.is_active = False
        db.session.commit()

    def sync_site_to_satellite(self, site_id: str) -> dict[str, Any]:
        site = self._get_site(site_id)
        if not self._is_construction(site.industry_type):
            raise ValueError("Somente unidades de Construção sincronizam com o Diário de Obra.")
        if site.satellite_site_id:
            return {
                **self._site_dict(site),
                "message": "Unidade já está vinculada ao satélite.",
            }
        warning = self._try_sync_satellite(site)
        db.session.commit()
        result = self._site_dict(site)
        if warning:
            result["sync_warning"] = warning
            result["satellite_sync_pending"] = True
            raise RuntimeError(warning)
        result["message"] = "Canteiro sincronizado com o Diário de Obra."
        return result

    def push_weekly_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        site_id = payload.get("operational_site_id") or payload.get("site_id")
        site = self._get_site(site_id)
        if not site.satellite_site_id:
            raise ValueError("Unidade sem vínculo com o satélite Diário de Obra.")

        goals = payload.get("goals") or []
        if not isinstance(goals, list) or not goals:
            raise ValueError("Informe ao menos uma meta diária em 'goals'.")

        normalized = []
        for item in goals:
            if not isinstance(item, dict):
                continue
            goal_date = self._parse_date(item.get("date"))
            goal_text = (item.get("sprint_daily_goal") or item.get("goal") or "").strip()
            if not goal_date or not goal_text:
                continue
            normalized.append({"date": goal_date.isoformat(), "sprint_daily_goal": goal_text})

        if not normalized:
            raise ValueError("Nenhuma meta válida informada.")

        result = SatelliteClient().push_daily_goals(
            {
                "tenant_id": str(site.tenant_id),
                "project_id": site.satellite_site_id,
                "goals": normalized,
            }
        )
        return {"status": "ok", "site": self._site_dict(site), "satellite": result}

    def list_execution_reports(
        self, *, report_date: date | None = None, site_id: str | None = None
    ) -> list[dict[str, Any]]:
        tenant_id = g.tenant_id
        query = DailyExecutionReport.query.filter_by(tenant_id=tenant_id)
        if report_date:
            query = query.filter_by(report_date=report_date)
        if site_id:
            query = query.filter_by(operational_site_id=self._as_uuid(site_id))
        reports = query.order_by(DailyExecutionReport.report_date.desc()).all()

        site_map = {
            str(site.id): site
            for site in OperationalSite.query.filter_by(tenant_id=tenant_id, is_active=True).all()
        }

        results: list[dict[str, Any]] = []
        for report in reports:
            row = report.to_dict()
            site = site_map.get(row["operational_site_id"] or "")
            row["site_name"] = site.name if site else "Unidade"
            row["site_location"] = site.location if site else None
            row["industry_type"] = str(site.industry_type) if site else None
            results.append(row)

        # Inclui unidades sem relatório no dia (farol cinza)
        if report_date:
            reported_ids = {r["operational_site_id"] for r in results if r["operational_site_id"]}
            for site in site_map.values():
                sid = str(site.id)
                if sid not in reported_ids:
                    industry = str(site.industry_type) if site.industry_type else INDUSTRY_CONSTRUCAO
                    results.append(
                        {
                            "id": None,
                            "tenant_id": str(tenant_id),
                            "site_id": sid,
                            "operational_site_id": sid,
                            "date": report_date.isoformat(),
                            "report_date": report_date.isoformat(),
                            "sprint_daily_goal": None,
                            "goal_achieved": None,
                            "impediment_details": None,
                            "mitigation_action": None,
                            "preventive_action": None,
                            "site_name": site.name,
                            "site_location": site.location,
                            "industry_type": industry,
                            "pending": True,
                        }
                    )
        return results

    def reopen_execution_day(
        self,
        *,
        site_id: str,
        report_date: date,
        reopened_by: str | None = None,
    ) -> dict[str, Any]:
        """Reabre RDO no satélite para edição pelo executor."""
        site = self._get_site(site_id)
        if not site.satellite_site_id:
            raise ValueError("Canteiro ainda não sincronizado com o Diário de Obra.")

        actor = (reopened_by or getattr(g, "user_name", None) or "Gestor operacional").strip()
        result = SatelliteClient().reopen_rdo_log(
            {
                "project_id": site.satellite_site_id,
                "date": report_date.isoformat(),
                "reopened_by": actor,
            }
        )

        report = DailyExecutionReport.query.filter_by(
            tenant_id=g.tenant_id,
            operational_site_id=site.id,
            report_date=report_date,
        ).first()
        if report:
            db.session.delete(report)
            db.session.commit()

        return {
            "status": "ok",
            "site": self._site_dict(site),
            "date": report_date.isoformat(),
            "satellite": result,
        }

    def reports_summary(
        self,
        *,
        start_date: date,
        end_date: date,
        site_id: str | None = None,
    ) -> dict[str, Any]:
        """Agrega DailyExecutionReport no intervalo para visão consolidada."""
        if end_date < start_date:
            raise ValueError("end_date deve ser igual ou posterior a start_date.")

        tenant_id = g.tenant_id
        query = DailyExecutionReport.query.filter(
            DailyExecutionReport.tenant_id == tenant_id,
            DailyExecutionReport.report_date >= start_date,
            DailyExecutionReport.report_date <= end_date,
        )
        if site_id:
            query = query.filter_by(operational_site_id=self._as_uuid(site_id))

        reports = query.order_by(DailyExecutionReport.report_date.desc()).all()
        site_map = {
            str(site.id): site
            for site in OperationalSite.query.filter_by(tenant_id=tenant_id).all()
        }

        total_days_planned = len(reports)
        total_goals_achieved = sum(1 for r in reports if r.goal_achieved is True)
        answered = [r for r in reports if r.goal_achieved is not None]
        success_rate = (
            round((total_goals_achieved / len(answered)) * 100, 1) if answered else 0.0
        )

        consolidated_impediments: list[dict[str, Any]] = []
        occurrences_by_type: dict[str, int] = {}
        occurrences_over_time: dict[str, int] = {}

        for report in reports:
            rdo = report.raw_payload if isinstance(report.raw_payload, dict) else {}
            day_key = report.report_date.isoformat()
            day_count = self._count_rdo_occurrences(rdo)
            if day_count:
                occurrences_over_time[day_key] = occurrences_over_time.get(day_key, 0) + day_count
            for occ_type, count in self._occurrence_type_counts(rdo).items():
                occurrences_by_type[occ_type] = occurrences_by_type.get(occ_type, 0) + count

            if report.goal_achieved is not False:
                continue
            site = site_map.get(str(report.operational_site_id) if report.operational_site_id else "")
            consolidated_impediments.append(
                {
                    "id": str(report.id),
                    "site_id": str(report.operational_site_id)
                    if report.operational_site_id
                    else None,
                    "site_name": site.name if site else "Unidade",
                    "industry_type": str(site.industry_type) if site else None,
                    "date": report.report_date.isoformat(),
                    "report_date": report.report_date.isoformat(),
                    "sprint_daily_goal": report.sprint_daily_goal,
                    "goal_achieved": report.goal_achieved,
                    "impediment_details": report.impediment_details,
                    "mitigation_action": report.mitigation_action,
                    "preventive_action": report.preventive_action,
                    "raw_payload": report.raw_payload,
                }
            )

        type_labels = self._occurrence_type_labels()
        occurrences_by_type_list = [
            {
                "type": key,
                "label": type_labels.get(key, key.replace("_", " ").title()),
                "count": count,
            }
            for key, count in sorted(occurrences_by_type.items(), key=lambda item: (-item[1], item[0]))
        ]
        occurrences_over_time_list = [
            {"date": day, "count": count}
            for day, count in sorted(occurrences_over_time.items())
        ]

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "site_id": site_id,
            "total_days_planned": total_days_planned,
            "total_goals_achieved": total_goals_achieved,
            "total_goals_failed": sum(1 for r in reports if r.goal_achieved is False),
            "total_unanswered": sum(1 for r in reports if r.goal_achieved is None),
            "success_rate": success_rate,
            "consolidated_impediments": consolidated_impediments,
            "occurrences_by_type": occurrences_by_type_list,
            "occurrences_over_time": occurrences_over_time_list,
        }

    @staticmethod
    def _occurrence_type_labels() -> dict[str, str]:
        return {
            "meta_nao_atingida": "Meta não atingida",
            "acidente": "Acidente",
            "falta_material": "Falta de material",
            "queda_energia": "Queda de energia",
            "chuva_forte": "Chuva forte",
            "geral": "Ocorrência geral",
            "equipment_breakdown": "Quebra de equipamento",
            "delay_material": "Espera de material",
            "delay_rework": "Retrabalho",
            "delay_front": "Falta de frente",
            "ppe_non_compliance": "EPI não conforme",
            "excessive_absences": "Faltas excessivas",
        }

    @staticmethod
    def _occurrence_type_counts(rdo: dict[str, Any]) -> dict[str, int]:
        counts: dict[str, int] = {}
        if not rdo:
            return counts

        if rdo.get("goal_achieved") is False:
            counts["meta_nao_atingida"] = counts.get("meta_nao_atingida", 0) + 1

        for item in rdo.get("occurrences") or []:
            if not isinstance(item, dict):
                continue
            occ_type = str(item.get("type") or "geral").strip().lower() or "geral"
            counts[occ_type] = counts.get(occ_type, 0) + 1

        for item in rdo.get("equipment_statuses") or []:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or "").strip().lower()
            if status == "parado por quebra":
                counts["equipment_breakdown"] = counts.get("equipment_breakdown", 0) + 1

        if rdo.get("ppe_compliant") is False:
            counts["ppe_non_compliance"] = counts.get("ppe_non_compliance", 0) + 1
        if rdo.get("delay_waiting_material"):
            counts["delay_material"] = counts.get("delay_material", 0) + 1
        if rdo.get("delay_rework"):
            counts["delay_rework"] = counts.get("delay_rework", 0) + 1
        if rdo.get("delay_lack_of_front"):
            counts["delay_front"] = counts.get("delay_front", 0) + 1

        workforce = [row for row in (rdo.get("workforce") or []) if isinstance(row, dict)]
        total_absences = sum(
            int(
                row.get("absences_count")
                if row.get("absences_count") is not None
                else row.get("absences") or 0
            )
            for row in workforce
        )
        hot_spots = sum(
            1
            for row in workforce
            if int(
                row.get("absences_count")
                if row.get("absences_count") is not None
                else row.get("absences") or 0
            )
            >= 3
        )
        if total_absences >= 5 or hot_spots:
            counts["excessive_absences"] = counts.get("excessive_absences", 0) + 1

        return counts

    @staticmethod
    def _count_rdo_occurrences(rdo: dict[str, Any]) -> int:
        if not rdo:
            return 0
        return sum(OperationalService._occurrence_type_counts(rdo).values())

    def upsert_execution_report_from_rdo(
        self,
        *,
        tenant_id: uuid.UUID,
        event_id: uuid.UUID,
        event_date: date,
        payload: dict[str, Any],
    ) -> DailyExecutionReport | None:
        rdo = payload.get("rdo") if isinstance(payload.get("rdo"), dict) else payload
        if not isinstance(rdo, dict):
            return None

        goal_achieved = rdo.get("goal_achieved")

        site = self._resolve_site_from_payload(tenant_id, rdo, payload)
        site_id = site.id if site else None

        report = (
            DailyExecutionReport.query.filter_by(
                tenant_id=tenant_id,
                operational_site_id=site_id,
                report_date=event_date,
            ).first()
            if site_id
            else DailyExecutionReport.query.filter_by(
                tenant_id=tenant_id, report_date=event_date, gemba_event_id=event_id
            ).first()
        )

        if not report:
            report = DailyExecutionReport(
                tenant_id=tenant_id,
                operational_site_id=site_id,
                report_date=event_date,
            )
            db.session.add(report)

        report.gemba_event_id = event_id
        report.sprint_daily_goal = (rdo.get("sprint_daily_goal") or "").strip() or None
        report.goal_achieved = None if goal_achieved is None else bool(goal_achieved)
        report.impediment_details = (rdo.get("impediment_details") or "").strip() or None
        report.mitigation_action = (rdo.get("mitigation_action") or "").strip() or None
        report.preventive_action = (rdo.get("preventive_action") or "").strip() or None
        report.raw_payload = rdo
        db.session.flush()
        return report

    def _resolve_site_from_payload(
        self, tenant_id: uuid.UUID, rdo: dict[str, Any], payload: dict[str, Any]
    ) -> OperationalSite | None:
        satellite_id = str(
            rdo.get("project_id") or payload.get("project_id") or rdo.get("site_id") or ""
        ).strip()
        if satellite_id:
            site = OperationalSite.query.filter_by(
                tenant_id=tenant_id, satellite_site_id=satellite_id
            ).first()
            if site:
                return site
        return None

    def _try_sync_satellite(self, site: OperationalSite) -> str | None:
        """Tenta criar canteiro no satélite. Em falha, mantém a unidade no hub."""
        try:
            site.satellite_site_id = self._sync_construction_site_to_satellite(site)
            return None
        except Exception as exc:
            return (
                "Unidade criada no hub, mas falhou a sincronização com o Diário de Obra: "
                f"{exc}. Use 'Sincronizar satélite' para tentar de novo."
            )

    def _sync_construction_site_to_satellite(self, site: OperationalSite) -> str:
        satellite = SatelliteClient().create_rdo_site(
            {
                "tenant_id": str(site.tenant_id),
                "name": site.name,
                "location": site.location,
            }
        )
        satellite_id = str(satellite.get("id") or "").strip()
        if not satellite_id:
            raise RuntimeError("Satélite não retornou id do canteiro.")
        return satellite_id

    def _resolve_manager_id(self, value: Any) -> uuid.UUID | None:
        manager_id = self._optional_uuid(value, "manager_id")
        if not manager_id:
            return None
        membership = TenantUser.query.filter_by(
            tenant_id=g.tenant_id, user_id=manager_id, role=ROLE_LED
        ).first()
        if not membership:
            raise ValueError("Gestor responsável deve ser um lead do mesmo tenant.")
        return manager_id

    @staticmethod
    def _parse_industry_type(value: Any) -> IndustryType:
        raw = (value or INDUSTRY_CONSTRUCAO).strip() if isinstance(value, str) else value
        if isinstance(raw, IndustryType):
            return raw
        text = str(raw or INDUSTRY_CONSTRUCAO).strip()
        for member in IndustryType:
            if member.value.lower() == text.lower() or member.name.lower() == text.lower():
                return member
        # Aceita prefixo legado "construcao-civil" → Construcao
        if text.lower().startswith("constr"):
            return IndustryType.CONSTRUCAO
        raise ValueError(
            "industry_type inválido. Use: Construcao, Varejo, TI, Telecom, Industrial, Educacao, Saude, Outro."
        )

    @staticmethod
    def _is_construction(industry_type: IndustryType | str | None) -> bool:
        if isinstance(industry_type, IndustryType):
            return industry_type == IndustryType.CONSTRUCAO
        return bool(industry_type) and str(industry_type).lower().startswith("constr")

    @staticmethod
    def _site_dict(site: OperationalSite) -> dict[str, Any]:
        data = site.to_dict()
        data["satellite_sync_pending"] = bool(
            OperationalService._is_construction(site.industry_type)
            and not site.satellite_site_id
        )
        return data

    def _get_site(self, site_id: Any) -> OperationalSite:
        site_uuid = self._as_uuid(site_id)
        site = OperationalSite.query.filter_by(id=site_uuid, tenant_id=g.tenant_id).first()
        if not site:
            raise ValueError("Unidade operacional não encontrada.")
        return site

    @staticmethod
    def _as_uuid(value: Any) -> uuid.UUID:
        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError("UUID inválido.") from exc

    @staticmethod
    def _optional_uuid(value: Any, field: str) -> uuid.UUID | None:
        if value in (None, ""):
            return None
        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} inválido.") from exc

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not value:
            return None
        try:
            text = str(value).strip()
            if "T" in text:
                return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def week_dates(reference: date | None = None) -> list[date]:
    """Segunda a domingo da semana da data de referência."""
    ref = reference or date.today()
    monday = ref - timedelta(days=ref.weekday())
    return [monday + timedelta(days=i) for i in range(7)]
