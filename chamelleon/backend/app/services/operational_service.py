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
    WeeklyCommitment,
)
from app.models.kaizen_models import (
    RESTRICTION_CATEGORIES,
    RESTRICTION_CATEGORY_LABELS,
    Restriction,
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
        organizational_unit_id = self._resolve_organizational_unit_id(
            payload.get("organizational_unit_id")
        )
        location = (payload.get("location") or "").strip() or None

        site = OperationalSite(
            tenant_id=tenant_id,
            name=name,
            location=location,
            industry_type=industry_type.value if isinstance(industry_type, IndustryType) else str(industry_type),
            manager_id=manager_id,
            organizational_unit_id=organizational_unit_id,
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
        if "organizational_unit_id" in payload:
            site.organizational_unit_id = self._resolve_organizational_unit_id(
                payload.get("organizational_unit_id"),
                current_id=site.organizational_unit_id,
            )
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

    def sync_site_roster(self, site_id: str) -> dict[str, Any]:
        site = self._get_site(site_id)
        if not self._is_construction(site.industry_type):
            raise ValueError(
                "Somente unidades de Construção sincronizam equipe com o Diário de Obra."
            )
        if not site.satellite_site_id:
            raise ValueError("Sincronize a unidade com o satélite antes de enviar a equipe.")
        roster = self._build_site_roster(site)
        SatelliteClient().push_roster(
            {
                "tenant_id": str(site.tenant_id),
                "project_id": site.satellite_site_id,
                "roster": roster,
            }
        )
        return {"site_id": str(site.id), "roster_count": len(roster)}

    def push_weekly_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        site_id = payload.get("operational_site_id") or payload.get("site_id")
        site = self._get_site(site_id)
        tenant_id = g.tenant_id

        raw_commitments = payload.get("commitments")
        if not isinstance(raw_commitments, list) or not raw_commitments:
            raise ValueError("Informe ao menos um dia em 'commitments'.")

        # Por data: lista de textos (pode ser vazia = limpar o dia)
        by_date: dict[str, list[str]] = {}
        for entry in raw_commitments:
            if not isinstance(entry, dict):
                continue
            commitment_date = self._parse_date(entry.get("date"))
            if not commitment_date:
                continue
            day_key = commitment_date.isoformat()
            items_raw = entry.get("items")
            if items_raw is None:
                items_raw = []
            if not isinstance(items_raw, list):
                continue
            items = [str(text).strip() for text in items_raw if str(text or "").strip()]
            by_date[day_key] = items

        if not by_date:
            raise ValueError("Nenhuma data válida informada em 'commitments'.")

        saved_rows: list[WeeklyCommitment] = []
        satellite_goals: list[dict[str, Any]] = []

        for day_key, items in sorted(by_date.items()):
            day = date.fromisoformat(day_key)
            # Replace completo por (site, date) — inclusive limpeza quando items=[]
            existing = WeeklyCommitment.query.filter_by(
                tenant_id=tenant_id,
                operational_site_id=site.id,
                commitment_date=day,
            ).all()
            for row in existing:
                db.session.delete(row)
            db.session.flush()

            for seq, description in enumerate(items):
                row = WeeklyCommitment(
                    tenant_id=tenant_id,
                    operational_site_id=site.id,
                    commitment_date=day,
                    description=description,
                    sequence=seq,
                    is_completed=None,
                )
                db.session.add(row)
                saved_rows.append(row)

        db.session.flush()

        for day_key, items in sorted(by_date.items()):
            if not items:
                continue
            satellite_goals.append(
                {
                    "date": day_key,
                    "items": [
                        {"id": str(row.id), "description": row.description}
                        for row in saved_rows
                        if row.commitment_date.isoformat() == day_key
                    ],
                }
            )

        db.session.commit()
        for row in saved_rows:
            db.session.refresh(row)

        commitments_out = self._group_commitments_by_date(saved_rows)

        satellite_result: dict[str, Any] | None = None
        satellite_warning: str | None = None
        if site.satellite_site_id:
            if satellite_goals:
                try:
                    satellite_result = SatelliteClient().push_daily_goals(
                        {
                            "tenant_id": str(site.tenant_id),
                            "project_id": site.satellite_site_id,
                            "goals": satellite_goals,
                        }
                    )
                except Exception as exc:
                    satellite_warning = (
                        "Compromissos salvos no Chamelleon, mas falhou o envio ao "
                        f"Diário: {exc}"
                    )
        else:
            satellite_warning = (
                "Compromissos salvos no Chamelleon. Sincronize o canteiro para "
                "publicar no Diário de Obra."
            )

        result: dict[str, Any] = {
            "status": "ok",
            "site": self._site_dict(site),
            "commitments": commitments_out,
            "saved_count": len(saved_rows),
        }
        if satellite_result is not None:
            result["satellite"] = satellite_result
        if satellite_warning:
            result["satellite_warning"] = satellite_warning
        return result

    def get_weekly_goals(
        self,
        *,
        site_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        site = self._get_site(site_id)
        tenant_id = g.tenant_id
        query = WeeklyCommitment.query.filter_by(
            tenant_id=tenant_id,
            operational_site_id=site.id,
        )
        start = self._parse_date(start_date)
        end = self._parse_date(end_date)
        if start:
            query = query.filter(WeeklyCommitment.commitment_date >= start)
        if end:
            query = query.filter(WeeklyCommitment.commitment_date <= end)

        rows = query.order_by(
            WeeklyCommitment.commitment_date.asc(),
            WeeklyCommitment.sequence.asc(),
        ).all()
        filtered = self._group_commitments_by_date(rows)

        all_rows = (
            WeeklyCommitment.query.filter_by(
                tenant_id=tenant_id,
                operational_site_id=site.id,
            )
            .order_by(
                WeeklyCommitment.commitment_date.asc(),
                WeeklyCommitment.sequence.asc(),
            )
            .all()
        )
        all_commitments = self._group_commitments_by_date(all_rows)

        return {
            "status": "ok",
            "site_id": str(site.id),
            "satellite_site_id": site.satellite_site_id,
            "commitments": filtered,
            "all_commitments": all_commitments,
        }

    def list_restrictions(
        self,
        *,
        start_date: date,
        end_date: date,
        site_id: str | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        if end_date < start_date:
            raise ValueError("end_date deve ser igual ou posterior a start_date.")

        tenant_id = g.tenant_id
        query = Restriction.query.filter(
            Restriction.tenant_id == tenant_id,
            Restriction.occurrence_date >= start_date,
            Restriction.occurrence_date <= end_date,
        )
        if site_id:
            query = query.filter_by(operational_site_id=self._as_uuid(site_id))
        if category:
            cat = str(category).strip().upper()
            if cat not in RESTRICTION_CATEGORIES:
                raise ValueError(
                    "category inválida. Use: " + ", ".join(RESTRICTION_CATEGORIES)
                )
            query = query.filter_by(category=cat)

        rows = query.order_by(
            Restriction.occurrence_date.desc(),
            Restriction.created_at.desc(),
        ).all()
        return {
            "status": "ok",
            "restrictions": [row.to_dict() for row in rows],
            "total": len(rows),
        }

    @staticmethod
    def _format_consolidated_goal(items: list[str]) -> str:
        return "\n".join(f"{idx}) {text}" for idx, text in enumerate(items, start=1))

    @staticmethod
    def _group_commitments_by_date(
        rows: list[WeeklyCommitment],
    ) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            day_key = row.commitment_date.isoformat()
            grouped.setdefault(day_key, []).append(
                {
                    "id": str(row.id),
                    "description": row.description,
                    "sequence": row.sequence,
                    "is_completed": row.is_completed,
                }
            )
        return grouped

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
        # Reabrir = avaliação ainda desconhecida; o plano (WeeklyCommitment) permanece.
        self._sync_commitments_completion(
            tenant_id=g.tenant_id,
            operational_site_id=site.id,
            commitment_date=report_date,
            goal_achieved=None,
        )
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

        # --- PPC (Last Planner): aproximação honesta dia inteiro ---
        # O satélite devolve um único boolean por dia (goal_achieved), não por
        # compromisso. Todos os WeeklyCommitment do (site, data) recebem o mesmo
        # is_completed; não correlacionamos Restriction ↔ compromisso individual.
        commitments_query = WeeklyCommitment.query.filter(
            WeeklyCommitment.tenant_id == tenant_id,
            WeeklyCommitment.commitment_date >= start_date,
            WeeklyCommitment.commitment_date <= end_date,
        )
        if site_id:
            commitments_query = commitments_query.filter_by(
                operational_site_id=self._as_uuid(site_id)
            )
        commitments = commitments_query.all()
        evaluated = [c for c in commitments if c.is_completed is not None]
        completed = sum(1 for c in evaluated if c.is_completed)
        ppc = (
            round((completed / len(evaluated)) * 100, 1) if evaluated else 0.0
        )

        restrictions_query = Restriction.query.filter(
            Restriction.tenant_id == tenant_id,
            Restriction.occurrence_date >= start_date,
            Restriction.occurrence_date <= end_date,
        )
        if site_id:
            restrictions_query = restrictions_query.filter_by(
                operational_site_id=self._as_uuid(site_id)
            )
        restrictions = restrictions_query.all()

        restrictions_by_category_counts: dict[str, int] = {}
        restrictions_over_time_counts: dict[str, int] = {}
        restrictions_by_site_date: dict[tuple[str, str], list[dict[str, str]]] = {}
        for r in restrictions:
            restrictions_by_category_counts[r.category] = (
                restrictions_by_category_counts.get(r.category, 0) + 1
            )
            day_key = r.occurrence_date.isoformat()
            restrictions_over_time_counts[day_key] = (
                restrictions_over_time_counts.get(day_key, 0) + 1
            )
            site_key = (
                str(r.operational_site_id) if r.operational_site_id else "",
                day_key,
            )
            restrictions_by_site_date.setdefault(site_key, []).append(
                {"category": r.category, "title": r.title}
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
            site_id_str = (
                str(report.operational_site_id) if report.operational_site_id else None
            )
            consolidated_impediments.append(
                {
                    "id": str(report.id),
                    "site_id": site_id_str,
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
                    "restrictions": restrictions_by_site_date.get(
                        (site_id_str or "", report.report_date.isoformat()),
                        [],
                    ),
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
            "ppc": ppc,
            "total_commitments_promised": len(evaluated),
            "total_commitments_completed": completed,
            "total_commitments_pending_evaluation": len(commitments) - len(evaluated),
            "restrictions_by_category": [
                {
                    "category": k,
                    "label": RESTRICTION_CATEGORY_LABELS.get(k, k),
                    "count": v,
                }
                for k, v in sorted(
                    restrictions_by_category_counts.items(),
                    key=lambda i: (-i[1], i[0]),
                )
            ],
            "restrictions_over_time": [
                {"date": k, "count": v}
                for k, v in sorted(restrictions_over_time_counts.items())
            ],
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

        # Preferir resolução por item (Prompt 6). Fallback: booleano do dia (Prompt 3).
        commitments_payload = rdo.get("commitments")
        if isinstance(commitments_payload, list) and commitments_payload and site_id:
            for item in commitments_payload:
                if not isinstance(item, dict):
                    continue
                source_id = item.get("source_commitment_id") or item.get("id")
                is_completed = item.get("is_completed")
                if not source_id:
                    continue
                try:
                    commitment_uuid = uuid.UUID(str(source_id))
                except ValueError:
                    continue
                WeeklyCommitment.query.filter_by(
                    tenant_id=tenant_id, id=commitment_uuid
                ).update(
                    {
                        "is_completed": (
                            None if is_completed is None else bool(is_completed)
                        )
                    },
                    synchronize_session=False,
                )
        elif site_id:
            # Fallback pra RDOs antigos/sem commitments — aproximação dia inteiro.
            self._sync_commitments_completion(
                tenant_id=tenant_id,
                operational_site_id=site_id,
                commitment_date=event_date,
                goal_achieved=report.goal_achieved,
            )
        return report

    @staticmethod
    def _sync_commitments_completion(
        *,
        tenant_id: uuid.UUID,
        operational_site_id: uuid.UUID,
        commitment_date: date,
        goal_achieved: bool | None,
    ) -> None:
        WeeklyCommitment.query.filter_by(
            tenant_id=tenant_id,
            operational_site_id=operational_site_id,
            commitment_date=commitment_date,
        ).update({"is_completed": goal_achieved}, synchronize_session=False)

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
        except Exception as exc:
            return (
                "Unidade criada no hub, mas falhou a sincronização com o Diário de Obra: "
                f"{exc}. Use 'Sincronizar satélite' para tentar de novo."
            )
        try:
            roster = self._build_site_roster(site)
            if roster:
                SatelliteClient().push_roster(
                    {
                        "tenant_id": str(site.tenant_id),
                        "project_id": site.satellite_site_id,
                        "roster": roster,
                    }
                )
        except Exception:
            pass  # equipe pode ser sincronizada depois via botão dedicado
        return None

    def get_field_professionals_for_site(self, site_id: str | uuid.UUID) -> list[Any]:
        """Professionals com papel de campo alocados ao canteiro (via TenantUser)."""
        from app.core.professional_role_catalog import get_role_catalog
        from app.models.capacity_models import Professional

        site = self._get_site(site_id)
        field_roles = {
            item["value"]
            for item in get_role_catalog({site.industry_type})
            if item.get("group") == site.industry_type
        }
        if not field_roles:
            return []

        memberships = TenantUser.query.filter_by(
            tenant_id=site.tenant_id, operational_site_id=site.id
        ).all()
        user_ids = [m.user_id for m in memberships]
        if not user_ids:
            return []

        return (
            Professional.query.filter(
                Professional.tenant_id == site.tenant_id,
                Professional.user_id.in_(user_ids),
                Professional.role.in_(field_roles),
                Professional.is_active.is_(True),
            )
            .order_by(Professional.name.asc())
            .all()
        )

    def _build_site_roster(self, site: OperationalSite) -> list[dict[str, Any]]:
        professionals = self.get_field_professionals_for_site(site.id)
        return [{"id": str(p.id), "name": p.name, "role": p.role} for p in professionals]

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

    def _resolve_organizational_unit_id(
        self,
        value: Any,
        *,
        current_id: uuid.UUID | None = None,
    ) -> uuid.UUID | None:
        if not value:
            return None
        from app.models.organization_models import OrganizationalUnit

        unit_uuid = self._as_uuid(value)
        unit = OrganizationalUnit.query.filter_by(
            id=unit_uuid, tenant_id=g.tenant_id
        ).first()
        if not unit:
            raise ValueError("Unidade organizacional inválida.")
        # Soft-delete mantém o vínculo; só bloqueia *nova* atribuição a unidade inativa.
        if not unit.is_active and (current_id is None or unit_uuid != current_id):
            raise ValueError("Unidade organizacional inválida.")
        return unit_uuid

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
