"""Conformidade — treinamento, ASO e não-conformidade (NR-18 / SiAC)."""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from flask import g

from app.database.models import TenantUser, db
from app.models.capacity_models import Professional
from app.models.compliance_models import (
    CORRECTIVE_ACTION_PROJECT_STATUSES,
    EXAM_RESULTS,
    EXAM_TYPES,
    NC_CATEGORIES,
    NC_OPERATIONAL_RUBRICS,
    NC_STATUSES,
    RECURRENCE_SIGNAL_STATUSES,
    TRAINING_TYPES,
    CorrectiveActionProject,
    CorrectiveActionProjectStatus,
    ExamResult,
    HealthRecord,
    NcOwnerSource,
    NonConformity,
    NonConformityCategory,
    NonConformityStatus,
    RecurrenceSignal,
    RecurrenceSignalStatus,
    TrainingRecord,
    TrainingType,
)
from app.models.kaizen_models import (
    SEVERITY_CRITICA,
    STAGE_CONCLUIDO,
    KaizenTicket,
)

logger = logging.getLogger(__name__)

RECURRENCE_THRESHOLD = 3
RECURRENCE_WINDOW_DAYS = 90

# Rubrica operacional a partir do título Andon/Kaizen (ticket não tem campo category).
_TITLE_RUBRIC_RULES: tuple[tuple[str, str], ...] = (
    ("não conformidade de epi", "EPI"),
    ("conformidade de epi", "EPI"),
    (" epi", "EPI"),
    ("acidente", "Acidente"),
    ("faltas excessivas", "Absenteismo"),
    ("equipamento", "Equipamento"),
    ("quebra", "Equipamento"),
    ("material", "Material"),
    ("frente de trabalho", "Frente"),
    ("energia", "Energia"),
    ("chuva", "Clima"),
)


class ComplianceService:
    def list_training_records(self, professional_id: str) -> list[dict[str, Any]]:
        professional = self._get_professional(professional_id)
        rows = (
            TrainingRecord.query.filter_by(
                tenant_id=self._tenant_id(), professional_id=professional.id
            )
            .order_by(TrainingRecord.completed_at.desc())
            .all()
        )
        return [r.to_dict() for r in rows]

    def create_training_record(self, payload: dict[str, Any]) -> dict[str, Any]:
        professional = self._get_professional(payload.get("professional_id"))
        training_type = str(payload.get("training_type") or "").strip()
        if training_type not in TRAINING_TYPES:
            raise ValueError(f"training_type inválido. Use: {', '.join(TRAINING_TYPES)}")
        completed_at = self._parse_date(payload.get("completed_at"), "completed_at")
        if not completed_at:
            raise ValueError("Campo obrigatório: completed_at.")
        custom_label = self._optional_text(payload.get("custom_label"))
        if training_type == TrainingType.OUTRO.value and not custom_label:
            raise ValueError("Informe custom_label quando training_type for Outro.")

        row = TrainingRecord(
            tenant_id=self._tenant_id(),
            professional_id=professional.id,
            training_type=training_type,
            custom_label=custom_label,
            completed_at=completed_at,
            expires_at=self._parse_date(payload.get("expires_at"), "expires_at"),
            hours=self._optional_int(payload.get("hours")),
            certificate_url=self._optional_text(payload.get("certificate_url")),
            notes=self._optional_text(payload.get("notes")),
        )
        db.session.add(row)
        db.session.commit()
        return row.to_dict()

    def update_training_record(self, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        row = self._get_training(record_id)
        if "training_type" in payload:
            training_type = str(payload.get("training_type") or "").strip()
            if training_type not in TRAINING_TYPES:
                raise ValueError(f"training_type inválido. Use: {', '.join(TRAINING_TYPES)}")
            row.training_type = training_type
        if "custom_label" in payload:
            row.custom_label = self._optional_text(payload.get("custom_label"))
        if "completed_at" in payload:
            completed_at = self._parse_date(payload.get("completed_at"), "completed_at")
            if not completed_at:
                raise ValueError("completed_at inválida.")
            row.completed_at = completed_at
        if "expires_at" in payload:
            row.expires_at = self._parse_date(payload.get("expires_at"), "expires_at")
        if "hours" in payload:
            row.hours = self._optional_int(payload.get("hours"))
        if "certificate_url" in payload:
            row.certificate_url = self._optional_text(payload.get("certificate_url"))
        if "notes" in payload:
            row.notes = self._optional_text(payload.get("notes"))
        db.session.commit()
        return row.to_dict()

    def delete_training_record(self, record_id: str) -> None:
        row = self._get_training(record_id)
        db.session.delete(row)
        db.session.commit()

    def list_health_records(self, professional_id: str) -> list[dict[str, Any]]:
        professional = self._get_professional(professional_id)
        rows = (
            HealthRecord.query.filter_by(
                tenant_id=self._tenant_id(), professional_id=professional.id
            )
            .order_by(HealthRecord.exam_date.desc())
            .all()
        )
        return [r.to_dict() for r in rows]

    def create_health_record(self, payload: dict[str, Any]) -> dict[str, Any]:
        professional = self._get_professional(payload.get("professional_id"))
        exam_type = str(payload.get("exam_type") or "").strip()
        if exam_type not in EXAM_TYPES:
            raise ValueError(f"exam_type inválido. Use: {', '.join(EXAM_TYPES)}")
        exam_date = self._parse_date(payload.get("exam_date"), "exam_date")
        if not exam_date:
            raise ValueError("Campo obrigatório: exam_date.")
        result = str(payload.get("result") or ExamResult.APTO.value).strip()
        if result not in EXAM_RESULTS:
            raise ValueError(f"result inválido. Use: {', '.join(EXAM_RESULTS)}")

        row = HealthRecord(
            tenant_id=self._tenant_id(),
            professional_id=professional.id,
            exam_type=exam_type,
            exam_date=exam_date,
            expires_at=self._parse_date(payload.get("expires_at"), "expires_at"),
            result=result,
            attachment_url=self._optional_text(payload.get("attachment_url")),
            notes=self._optional_text(payload.get("notes")),
        )
        db.session.add(row)
        db.session.commit()
        return row.to_dict()

    def update_health_record(self, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        row = self._get_health(record_id)
        if "exam_type" in payload:
            exam_type = str(payload.get("exam_type") or "").strip()
            if exam_type not in EXAM_TYPES:
                raise ValueError(f"exam_type inválido. Use: {', '.join(EXAM_TYPES)}")
            row.exam_type = exam_type
        if "exam_date" in payload:
            exam_date = self._parse_date(payload.get("exam_date"), "exam_date")
            if not exam_date:
                raise ValueError("exam_date inválida.")
            row.exam_date = exam_date
        if "expires_at" in payload:
            row.expires_at = self._parse_date(payload.get("expires_at"), "expires_at")
        if "result" in payload:
            result = str(payload.get("result") or "").strip()
            if result not in EXAM_RESULTS:
                raise ValueError(f"result inválido. Use: {', '.join(EXAM_RESULTS)}")
            row.result = result
        if "attachment_url" in payload:
            row.attachment_url = self._optional_text(payload.get("attachment_url"))
        if "notes" in payload:
            row.notes = self._optional_text(payload.get("notes"))
        db.session.commit()
        return row.to_dict()

    def delete_health_record(self, record_id: str) -> None:
        row = self._get_health(record_id)
        db.session.delete(row)
        db.session.commit()

    def get_site_compliance_status(self, site_id: str) -> dict[str, Any]:
        from app.services.operational_service import OperationalService

        professionals = OperationalService().get_field_professionals_for_site(site_id)
        people: list[dict[str, Any]] = []
        aptos = atencao = pendentes = 0

        for pro in professionals:
            trainings = (
                TrainingRecord.query.filter_by(
                    tenant_id=self._tenant_id(), professional_id=pro.id
                )
                .order_by(TrainingRecord.completed_at.desc())
                .all()
            )
            # Mais recente por tipo
            latest_by_type: dict[str, dict[str, Any]] = {}
            for row in trainings:
                if row.training_type not in latest_by_type:
                    latest_by_type[row.training_type] = row.to_dict()

            health_rows = (
                HealthRecord.query.filter_by(
                    tenant_id=self._tenant_id(), professional_id=pro.id
                )
                .order_by(HealthRecord.exam_date.desc())
                .all()
            )
            health = health_rows[0].to_dict() if health_rows else None

            status = self._person_status(list(latest_by_type.values()), health)
            if status == "apto":
                aptos += 1
            elif status == "atencao":
                atencao += 1
            else:
                pendentes += 1

            people.append(
                {
                    "professional_id": str(pro.id),
                    "name": pro.name,
                    "role": pro.role,
                    "status": status,
                    "trainings": list(latest_by_type.values()),
                    "health": health,
                }
            )

        return {
            "site_id": str(site_id),
            "total_professionals": len(professionals),
            "aptos": aptos,
            "atencao": atencao,
            "pendentes": pendentes,
            "professionals": people,
        }

    def list_non_conformities(
        self,
        *,
        operational_site_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        query = NonConformity.query.filter_by(tenant_id=self._tenant_id())
        if operational_site_id:
            query = query.filter_by(
                operational_site_id=self._parse_uuid(operational_site_id, "operational_site_id")
            )
        if status:
            if status not in NC_STATUSES:
                raise ValueError(f"status inválido. Use: {', '.join(NC_STATUSES)}")
            query = query.filter_by(status=status)
        rows = query.order_by(NonConformity.updated_at.desc()).all()
        return self._enrich_ncs([r.to_dict() for r in rows])

    def update_non_conformity(self, nc_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        nc = self._get_nc(nc_id)
        if "corrective_action" in payload:
            nc.corrective_action = self._optional_text(payload.get("corrective_action"))
        if "closed_evidence" in payload:
            nc.closed_evidence = self._optional_text(payload.get("closed_evidence"))
        if "status" in payload:
            status = str(payload.get("status") or "").strip()
            if status not in NC_STATUSES:
                raise ValueError(f"status inválido. Use: {', '.join(NC_STATUSES)}")
            nc.status = status
            if status == NonConformityStatus.FECHADA.value and not nc.closed_at:
                nc.closed_at = datetime.now(timezone.utc)
            if status != NonConformityStatus.FECHADA.value:
                nc.closed_at = None
        if "category" in payload:
            nc.category = self._normalize_nc_category(payload.get("category"))
        # owner/due via update geral também trava como Manual (compat)
        if "owner_user_id" in payload or "due_date" in payload:
            self._apply_manual_assignment(
                nc,
                owner_user_id=payload.get("owner_user_id")
                if "owner_user_id" in payload
                else nc.owner_user_id,
                due_date=payload.get("due_date") if "due_date" in payload else nc.due_date,
            )
        db.session.commit()
        return self._enrich_ncs([nc.to_dict()])[0]

    def assign_non_conformity(self, nc_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Atribuição manual de responsável/prazo — marca owner_source=Manual."""
        nc = self._get_nc(nc_id)
        if "owner_user_id" not in payload and "due_date" not in payload:
            raise ValueError("Informe owner_user_id e/ou due_date.")
        self._apply_manual_assignment(
            nc,
            owner_user_id=payload.get("owner_user_id")
            if "owner_user_id" in payload
            else nc.owner_user_id,
            due_date=payload.get("due_date") if "due_date" in payload else nc.due_date,
        )
        db.session.commit()
        return self._enrich_ncs([nc.to_dict()])[0]

    def _apply_manual_assignment(
        self,
        nc: NonConformity,
        *,
        owner_user_id: Any,
        due_date: Any,
    ) -> None:
        if isinstance(owner_user_id, uuid.UUID):
            nc.owner_user_id = owner_user_id
        else:
            nc.owner_user_id = self._resolve_owner_user_id(owner_user_id)
        if isinstance(due_date, date):
            nc.due_date = due_date
        else:
            nc.due_date = self._parse_date(due_date, "due_date")
        nc.owner_source = NcOwnerSource.MANUAL.value

    def get_or_create_non_conformity_for_ticket(
        self, ticket: KaizenTicket
    ) -> NonConformity | None:
        """Idempotente: cria/espelha NC para ticket crítico. Sem commit próprio."""
        existing = NonConformity.query.filter_by(
            source_kaizen_ticket_id=ticket.id
        ).first()

        if ticket.severity != SEVERITY_CRITICA:
            if existing:
                self._mirror_ticket_onto_nc(existing, ticket)
            return existing

        if existing:
            self._mirror_ticket_onto_nc(existing, ticket)
            return existing

        nc = NonConformity(
            tenant_id=ticket.tenant_id,
            operational_site_id=ticket.operational_site_id,
            source_kaizen_ticket_id=ticket.id,
            category=self.derive_category_from_ticket(ticket),
            severity=ticket.severity,
            norm_refs=["NR-18"],
            title=(ticket.title or "Não conformidade")[:255],
            description=ticket.description,
            owner_user_id=ticket.owner_user_id,
            due_date=ticket.due_date,
            owner_source=NcOwnerSource.HERDADO.value,
            status=NonConformityStatus.ABERTA.value,
        )
        self._mirror_ticket_onto_nc(nc, ticket)
        db.session.add(nc)
        db.session.flush()
        self._evaluate_recurrence_best_effort(nc)
        return nc

    def sync_ticket_best_effort(self, ticket: KaizenTicket) -> None:
        """Hook seguro — falha de conformidade não quebra o board Kaizen."""
        try:
            self.get_or_create_non_conformity_for_ticket(ticket)
            db.session.flush()
        except Exception:
            logger.exception(
                "Falha ao sincronizar NonConformity para ticket %s (ignorada).",
                getattr(ticket, "id", None),
            )

    def list_recurrence_signals(
        self,
        *,
        operational_site_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        query = RecurrenceSignal.query.filter_by(tenant_id=self._tenant_id())
        if operational_site_id:
            query = query.filter_by(
                operational_site_id=self._parse_uuid(operational_site_id, "operational_site_id")
            )
        if status:
            if status not in RECURRENCE_SIGNAL_STATUSES:
                raise ValueError(
                    f"status inválido. Use: {', '.join(RECURRENCE_SIGNAL_STATUSES)}"
                )
            query = query.filter_by(status=status)
        rows = query.order_by(RecurrenceSignal.updated_at.desc()).all()
        return self._enrich_recurrence_signals([r.to_dict() for r in rows])

    def mark_recurrence_signal_seen(self, signal_id: str) -> dict[str, Any]:
        signal = self._get_recurrence_signal(signal_id)
        if signal.status == RecurrenceSignalStatus.NOVO.value:
            signal.status = RecurrenceSignalStatus.VISTO.value
            db.session.commit()
        return self._enrich_recurrence_signals([signal.to_dict()])[0]

    def dismiss_recurrence_signal(self, signal_id: str) -> dict[str, Any]:
        signal = self._get_recurrence_signal(signal_id)
        if signal.status in (
            RecurrenceSignalStatus.CONVERTIDO.value,
            RecurrenceSignalStatus.DISPENSADO.value,
        ):
            raise ValueError("Sinal já finalizado; não pode ser dispensado.")
        signal.status = RecurrenceSignalStatus.DISPENSADO.value
        db.session.commit()
        return self._enrich_recurrence_signals([signal.to_dict()])[0]

    def convert_recurrence_signal(
        self, signal_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        signal = self._get_recurrence_signal(signal_id)
        if signal.status not in (
            RecurrenceSignalStatus.NOVO.value,
            RecurrenceSignalStatus.VISTO.value,
        ):
            raise ValueError("Apenas sinais Novo/Visto podem ser convertidos.")

        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("Campo obrigatório: title.")
        owner_user_id = self._resolve_owner_user_id(payload.get("owner_user_id"))
        if not owner_user_id:
            raise ValueError("Campo obrigatório: owner_user_id.")
        due_date = self._parse_date(payload.get("due_date"), "due_date")
        if not due_date:
            raise ValueError("Campo obrigatório: due_date.")

        project = CorrectiveActionProject(
            tenant_id=signal.tenant_id,
            title=title[:255],
            category=signal.category,
            operational_site_id=signal.operational_site_id,
            root_cause_notes=self._optional_text(payload.get("root_cause_notes")),
            owner_user_id=owner_user_id,
            due_date=due_date,
            status=CorrectiveActionProjectStatus.ABERTO.value,
            linked_non_conformity_ids=list(signal.non_conformity_ids or []),
        )
        db.session.add(project)
        db.session.flush()
        signal.status = RecurrenceSignalStatus.CONVERTIDO.value
        signal.corrective_action_project_id = project.id
        db.session.commit()
        return {
            "signal": self._enrich_recurrence_signals([signal.to_dict()])[0],
            "project": self._enrich_caps([project.to_dict()])[0],
        }

    def list_corrective_action_projects(self) -> list[dict[str, Any]]:
        rows = (
            CorrectiveActionProject.query.filter_by(tenant_id=self._tenant_id())
            .order_by(CorrectiveActionProject.updated_at.desc())
            .all()
        )
        return self._enrich_caps([r.to_dict() for r in rows])

    def get_corrective_action_project(self, project_id: str) -> dict[str, Any]:
        project = self._get_cap(project_id)
        return self._enrich_caps([project.to_dict()])[0]

    def update_corrective_action_project(
        self, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        project = self._get_cap(project_id)
        if "title" in payload:
            title = str(payload.get("title") or "").strip()
            if not title:
                raise ValueError("title não pode ser vazio.")
            project.title = title[:255]
        if "category" in payload:
            project.category = self._normalize_nc_category(payload.get("category"))
        if "root_cause_notes" in payload:
            project.root_cause_notes = self._optional_text(payload.get("root_cause_notes"))
        if "owner_user_id" in payload:
            owner = self._resolve_owner_user_id(payload.get("owner_user_id"))
            if not owner:
                raise ValueError("Campo obrigatório: owner_user_id.")
            project.owner_user_id = owner
        if "due_date" in payload:
            due = self._parse_date(payload.get("due_date"), "due_date")
            if not due:
                raise ValueError("Campo obrigatório: due_date.")
            project.due_date = due
        if "closed_evidence" in payload:
            project.closed_evidence = self._optional_text(payload.get("closed_evidence"))
        if "status" in payload:
            status = str(payload.get("status") or "").strip()
            if status not in CORRECTIVE_ACTION_PROJECT_STATUSES:
                raise ValueError(
                    f"status inválido. Use: {', '.join(CORRECTIVE_ACTION_PROJECT_STATUSES)}"
                )
            if status == CorrectiveActionProjectStatus.CONCLUIDO.value:
                evidence = project.closed_evidence
                if "closed_evidence" in payload:
                    evidence = self._optional_text(payload.get("closed_evidence"))
                    project.closed_evidence = evidence
                if not evidence:
                    raise ValueError(
                        "closed_evidence é obrigatório para concluir o projeto."
                    )
            project.status = status
        db.session.commit()
        return self._enrich_caps([project.to_dict()])[0]

    def _evaluate_recurrence_best_effort(self, nc: NonConformity) -> None:
        """Best-effort: falha na recorrência não reverte a NC."""
        try:
            self._evaluate_recurrence(nc)
        except Exception:
            logger.exception(
                "Falha ao avaliar recorrência para NC %s (ignorada).",
                getattr(nc, "id", None),
            )

    def _evaluate_recurrence(self, nc: NonConformity) -> None:
        if not nc.category:
            return
        now = datetime.now(timezone.utc)
        window_start_dt = now - timedelta(days=RECURRENCE_WINDOW_DAYS)
        query = NonConformity.query.filter(
            NonConformity.tenant_id == nc.tenant_id,
            NonConformity.category == nc.category,
            NonConformity.created_at >= window_start_dt,
        )
        if nc.operational_site_id is None:
            query = query.filter(NonConformity.operational_site_id.is_(None))
        else:
            query = query.filter(
                NonConformity.operational_site_id == nc.operational_site_id
            )
        matching = query.order_by(NonConformity.created_at.asc()).all()
        if len(matching) < RECURRENCE_THRESHOLD:
            return

        active = RecurrenceSignal.query.filter(
            RecurrenceSignal.tenant_id == nc.tenant_id,
            RecurrenceSignal.category == nc.category,
            RecurrenceSignal.status.in_(
                [
                    RecurrenceSignalStatus.NOVO.value,
                    RecurrenceSignalStatus.VISTO.value,
                ]
            ),
        )
        if nc.operational_site_id is None:
            active = active.filter(RecurrenceSignal.operational_site_id.is_(None))
        else:
            active = active.filter(
                RecurrenceSignal.operational_site_id == nc.operational_site_id
            )
        signal = active.order_by(RecurrenceSignal.created_at.desc()).first()

        nc_ids = [str(row.id) for row in matching]
        window_start = window_start_dt.date()
        window_end = now.date()
        if signal:
            signal.occurrence_count = len(matching)
            signal.non_conformity_ids = nc_ids
            signal.window_start = window_start
            signal.window_end = window_end
        else:
            signal = RecurrenceSignal(
                tenant_id=nc.tenant_id,
                operational_site_id=nc.operational_site_id,
                category=nc.category,
                non_conformity_ids=nc_ids,
                occurrence_count=len(matching),
                window_start=window_start,
                window_end=window_end,
                status=RecurrenceSignalStatus.NOVO.value,
            )
            db.session.add(signal)
        db.session.flush()

    def _mirror_ticket_onto_nc(self, nc: NonConformity, ticket: KaizenTicket) -> None:
        nc.title = (ticket.title or nc.title or "Não conformidade")[:255]
        nc.description = ticket.description
        nc.severity = ticket.severity
        nc.operational_site_id = ticket.operational_site_id

        # Owner/prazo: herda do ticket só se a NC não foi editada manualmente.
        if (nc.owner_source or NcOwnerSource.HERDADO.value) != NcOwnerSource.MANUAL.value:
            nc.owner_user_id = ticket.owner_user_id
            nc.due_date = ticket.due_date
            nc.owner_source = NcOwnerSource.HERDADO.value

        if ticket.workflow_stage == STAGE_CONCLUIDO:
            nc.status = NonConformityStatus.FECHADA.value
            if not nc.closed_at:
                nc.closed_at = datetime.now(timezone.utc)
            nc.closed_evidence = ticket.standardization_action
        elif ticket.owner_user_id and ticket.due_date:
            # Status Em_Tratativa segue o ticket (Contenção), mesmo se owner NC for Manual.
            nc.status = NonConformityStatus.EM_TRATATIVA.value
            nc.closed_at = None
        else:
            nc.status = NonConformityStatus.ABERTA.value
            nc.closed_at = None

    @staticmethod
    def _person_status(
        trainings: list[dict[str, Any]], health: dict[str, Any] | None
    ) -> str:
        statuses = [t.get("status") for t in trainings]
        if health:
            statuses.append(health.get("status"))
        if not statuses:
            return "pendente"
        if any(s == "vencido" for s in statuses):
            return "pendente"
        if any(s == "a_vencer" for s in statuses):
            return "atencao"
        return "apto"

    def _enrich_ncs(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        from app.database.models import User
        from app.models.operational_models import OperationalSite

        site_ids = {r["operational_site_id"] for r in rows if r.get("operational_site_id")}
        owner_ids = {r["owner_user_id"] for r in rows if r.get("owner_user_id")}
        sites = (
            {
                str(s.id): s.name
                for s in OperationalSite.query.filter(OperationalSite.id.in_(site_ids)).all()
            }
            if site_ids
            else {}
        )
        owners = (
            {str(u.id): u.name for u in User.query.filter(User.id.in_(owner_ids)).all()}
            if owner_ids
            else {}
        )
        for row in rows:
            row["operational_site_name"] = sites.get(row.get("operational_site_id"))
            row["owner_name"] = owners.get(row.get("owner_user_id"))
        return rows

    def _enrich_recurrence_signals(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        from app.models.operational_models import OperationalSite

        site_ids = {r["operational_site_id"] for r in rows if r.get("operational_site_id")}
        sites = (
            {
                str(s.id): s.name
                for s in OperationalSite.query.filter(OperationalSite.id.in_(site_ids)).all()
            }
            if site_ids
            else {}
        )
        all_nc_ids: set[str] = set()
        for row in rows:
            all_nc_ids.update(str(x) for x in (row.get("non_conformity_ids") or []))
        nc_map: dict[str, NonConformity] = {}
        if all_nc_ids:
            uuids = []
            for raw in all_nc_ids:
                try:
                    uuids.append(uuid.UUID(raw))
                except ValueError:
                    continue
            if uuids:
                for nc in NonConformity.query.filter(NonConformity.id.in_(uuids)).all():
                    nc_map[str(nc.id)] = nc

        for row in rows:
            row["operational_site_name"] = sites.get(row.get("operational_site_id"))
            linked = [nc_map[i] for i in (row.get("non_conformity_ids") or []) if i in nc_map]
            norms: list[str] = []
            for nc in linked:
                for ref in nc.norm_refs or []:
                    text = str(ref).strip()
                    if text and text not in norms:
                        norms.append(text)
            row["norm_refs_support"] = norms
            row["norm_context"] = (
                f"Possível relação: {', '.join(norms)}" if norms else None
            )
            row["linked_non_conformities"] = [
                {
                    "id": str(nc.id),
                    "title": nc.title,
                    "status": nc.status,
                    "created_at": nc.created_at.isoformat() if nc.created_at else None,
                }
                for nc in linked
            ]
        return rows

    def _enrich_caps(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        from app.database.models import User
        from app.models.operational_models import OperationalSite

        site_ids = {r["operational_site_id"] for r in rows if r.get("operational_site_id")}
        owner_ids = {r["owner_user_id"] for r in rows if r.get("owner_user_id")}
        sites = (
            {
                str(s.id): s.name
                for s in OperationalSite.query.filter(OperationalSite.id.in_(site_ids)).all()
            }
            if site_ids
            else {}
        )
        owners = (
            {str(u.id): u.name for u in User.query.filter(User.id.in_(owner_ids)).all()}
            if owner_ids
            else {}
        )
        all_nc_ids: set[str] = set()
        for row in rows:
            all_nc_ids.update(str(x) for x in (row.get("linked_non_conformity_ids") or []))
        nc_map: dict[str, dict[str, Any]] = {}
        if all_nc_ids:
            uuids = []
            for raw in all_nc_ids:
                try:
                    uuids.append(uuid.UUID(raw))
                except ValueError:
                    continue
            if uuids:
                for nc in NonConformity.query.filter(NonConformity.id.in_(uuids)).all():
                    nc_map[str(nc.id)] = {
                        "id": str(nc.id),
                        "title": nc.title,
                        "status": nc.status,
                        "category": nc.category,
                    }
        for row in rows:
            row["operational_site_name"] = sites.get(row.get("operational_site_id"))
            row["owner_name"] = owners.get(row.get("owner_user_id"))
            row["linked_non_conformities"] = [
                nc_map[i]
                for i in (row.get("linked_non_conformity_ids") or [])
                if i in nc_map
            ]
        return rows

    @classmethod
    def derive_category_from_ticket(cls, ticket: KaizenTicket) -> str:
        """Rubrica operacional — ticket não tem category; usa título Andon."""
        haystack = cls._fold(f"{ticket.title or ''} {ticket.description or ''}")
        for needle, rubric in _TITLE_RUBRIC_RULES:
            if cls._fold(needle) in haystack:
                return rubric
        return NonConformityCategory.SEGURANCA.value

    @staticmethod
    def _fold(text: str) -> str:
        import unicodedata

        normalized = unicodedata.normalize("NFKD", (text or "").lower())
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

    @classmethod
    def _normalize_nc_category(cls, value: Any) -> str:
        category = str(value or "").strip()
        if not category:
            raise ValueError("category não pode ser vazia.")
        if len(category) > 64:
            raise ValueError("category excede 64 caracteres.")
        allowed = set(NC_CATEGORIES) | set(NC_OPERATIONAL_RUBRICS)
        if category not in allowed:
            # Aceita rubricas já persistidas / futuras sem migração destrutiva.
            if not category.replace("_", "").replace("-", "").isalnum():
                raise ValueError(
                    f"category inválida. Use: {', '.join(sorted(allowed))}"
                )
        return category

    def _get_recurrence_signal(self, signal_id: str) -> RecurrenceSignal:
        row = db.session.get(RecurrenceSignal, self._parse_uuid(signal_id, "signal_id"))
        if not row or row.tenant_id != self._tenant_id():
            raise ValueError("Sinal de recorrência não encontrado.")
        return row

    def _get_cap(self, project_id: str) -> CorrectiveActionProject:
        row = db.session.get(
            CorrectiveActionProject, self._parse_uuid(project_id, "project_id")
        )
        if not row or row.tenant_id != self._tenant_id():
            raise ValueError("Projeto de ação corretiva não encontrado.")
        return row

    def _get_professional(self, professional_id: Any) -> Professional:
        pid = self._parse_uuid(professional_id, "professional_id")
        professional = Professional.query.filter_by(
            id=pid, tenant_id=self._tenant_id()
        ).first()
        if not professional:
            raise ValueError("Professional não encontrado neste tenant.")
        return professional

    def _get_training(self, record_id: str) -> TrainingRecord:
        row = db.session.get(TrainingRecord, self._parse_uuid(record_id, "record_id"))
        if not row or row.tenant_id != self._tenant_id():
            raise ValueError("Registro de treinamento não encontrado.")
        return row

    def _get_health(self, record_id: str) -> HealthRecord:
        row = db.session.get(HealthRecord, self._parse_uuid(record_id, "record_id"))
        if not row or row.tenant_id != self._tenant_id():
            raise ValueError("Registro de saúde não encontrado.")
        return row

    def _get_nc(self, nc_id: str) -> NonConformity:
        row = db.session.get(NonConformity, self._parse_uuid(nc_id, "nc_id"))
        if not row or row.tenant_id != self._tenant_id():
            raise ValueError("Não conformidade não encontrada.")
        return row

    def _resolve_owner_user_id(self, value: Any) -> uuid.UUID | None:
        if value is None or str(value).strip() == "":
            return None
        uid = self._parse_uuid(value, "owner_user_id")
        membership = TenantUser.query.filter_by(
            tenant_id=self._tenant_id(), user_id=uid
        ).first()
        if not membership:
            raise ValueError("owner_user_id inválido ou de outro tenant.")
        return uid

    @staticmethod
    def _tenant_id() -> uuid.UUID:
        tenant_id = getattr(g, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("Contexto de tenant ausente.")
        return tenant_id

    @staticmethod
    def _parse_uuid(value: Any, field: str) -> uuid.UUID:
        try:
            return uuid.UUID(str(value).strip())
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError(f"{field} inválido (UUID esperado).") from exc

    @staticmethod
    def _parse_date(value: Any, field: str) -> date | None:
        if value is None or str(value).strip() == "":
            return None
        try:
            return date.fromisoformat(str(value).strip()[:10])
        except ValueError as exc:
            raise ValueError(f"{field} inválida (use YYYY-MM-DD).") from exc

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None or str(value).strip() == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("hours inválido.") from exc
