"""Regras de negócio do módulo de Assessment.

O catálogo de questões (`AssessmentItem`) é definido administrativamente (Builder / Questões,
apenas sysadmin) e vinculado ao `framework_id`. Rubricas e questões setoriais (TA) são
persistidas em JSONB na base e servidas sem transformação em leitura — só mudam quando
o administrador edita e grava novamente.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from flask import g

from app.core.rbac.constants import ROLE_LED, ROLE_SYSADMIN
from app.core.sector_constants import DEFAULT_FRAMEWORK_ID
from app.database.models import (
    ActionPlan,
    AssessmentItem,
    AssessmentResponse,
    AssessmentSubmission,
    Framework,
    MaturityLevel,
    Tenant,
    User,
    db,
)
from app.data.rubric_patterns import normalize_rubric_options, repair_rubric_options
from app.services.diagnostic_report_service import (
    attach_baseline_to_report,
    build_baseline_snapshot,
    build_diagnostic_report,
    enrich_paneldx_comparative_scores,
    persist_diagnostic_report,
)
from app.services.diagnostic_completeness import completeness_summary, _prefu_for_item
from app.services.diagnostic_scoring_service import maturity_scores_snapshot
from app.services.framework_builder_service import (
    APPROVAL_STATUS_APPROVED,
    UNIVERSAL_AXIS_PREFIXES,
)


class AssessmentService:
    def save_draft(
        self,
        user_id: uuid.UUID | str,
        answers_list: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Grava respostas parciais sem finalizar o diagnóstico."""
        if not answers_list:
            raise ValueError("A lista de respostas não pode estar vazia.")

        tenant_id = g.tenant_id
        framework_id = g.framework_id
        user_uuid = self._as_uuid(user_id, "user_id")
        submission = self._get_or_create_draft_submission(user_uuid, tenant_id, framework_id)

        self._upsert_responses(submission, user_uuid, tenant_id, answers_list)
        db.session.commit()

        return {
            "submission_id": str(submission.id),
            "saved": len(answers_list),
            "status": "in_progress",
        }

    def get_draft(self, user_id: uuid.UUID | str) -> dict[str, Any] | None:
        """Rascunho em andamento ou último diagnóstico concluído do framework ativo."""
        self.ensure_assessment_started(user_id)
        submission = self._find_draft_submission(user_id)
        if not submission:
            submission = self._find_latest_completed_submission(user_id)
        if not submission:
            return None

        answers = self._submission_answers_payload(submission)
        catalog_items = AssessmentItem.query.filter_by(framework_id=submission.framework_id).all()
        items_by_id = {item.id: item for item in catalog_items}
        responses = AssessmentResponse.query.filter_by(submission_id=submission.id).all()
        completeness = completeness_summary(catalog_items, responses, items_by_id)

        completed_at = None
        if submission.status == "completed":
            ts = submission.evaluated_at or submission.created_at
            if ts:
                completed_at = ts.isoformat()

        return {
            "submission_id": str(submission.id),
            "answers": answers,
            "status": submission.status,
            "completeness": completeness,
            "completed_at": completed_at,
            "has_diagnostic_report": bool(submission.report_data),
        }

    def ensure_assessment_started(self, user_id: uuid.UUID | str) -> dict[str, Any]:
        """Garante submission em andamento para o utilizador (auto-início do questionário)."""
        if self._find_latest_completed_submission(user_id):
            return {"started": False, "status": "completed"}
        if self._find_draft_submission(user_id):
            return {"started": False, "status": "in_progress"}

        tenant_id = g.tenant_id
        framework_id = g.framework_id
        user_uuid = self._as_uuid(user_id, "user_id")
        submission = self._get_or_create_draft_submission(user_uuid, tenant_id, framework_id)
        db.session.commit()
        return {"started": True, "status": submission.status, "submission_id": str(submission.id)}

    def get_tenant_survey_progress_pct(self, tenant_id: uuid.UUID | str) -> float:
        """Percentual de respostas do questionário no tenant (framework ativo)."""
        from app.services.diagnostic_completeness import completeness_summary

        tenant_uuid = self._as_uuid(tenant_id, "tenant_id")
        framework_id = getattr(g, "framework_id", None)
        if not framework_id:
            fw_row = (
                AssessmentSubmission.query.filter_by(tenant_id=tenant_uuid)
                .order_by(AssessmentSubmission.created_at.desc())
                .first()
            )
            framework_id = fw_row.framework_id if fw_row else None
        if not framework_id:
            return 0.0

        completed = (
            AssessmentSubmission.query.filter_by(
                tenant_id=tenant_uuid,
                framework_id=framework_id,
                status="completed",
            )
            .first()
        )
        if completed:
            return 100.0

        submission = (
            AssessmentSubmission.query.filter_by(
                tenant_id=tenant_uuid,
                framework_id=framework_id,
                status="in_progress",
            )
            .order_by(AssessmentSubmission.updated_at.desc())
            .first()
        )
        if not submission:
            return 0.0

        catalog_items = AssessmentItem.query.filter_by(framework_id=framework_id).all()
        if not catalog_items:
            return 0.0
        items_by_id = {item.id: item for item in catalog_items}
        responses = AssessmentResponse.query.filter_by(submission_id=submission.id).all()
        summary = completeness_summary(catalog_items, responses, items_by_id)
        total_expected = summary.get("total_expected") or 0
        total_answered = summary.get("total_answered") or 0
        if total_expected <= 0:
            return 0.0
        return min(100.0, (total_answered / total_expected) * 100.0)

    def reset_draft(self, user_id: uuid.UUID | str) -> None:
        """Remove rascunho em andamento (ex.: refazer diagnóstico)."""
        submission = self._find_draft_submission(user_id)
        if submission:
            db.session.delete(submission)
            db.session.commit()

    def update_present_responses(
        self,
        user_id: uuid.UUID | str,
        answers_list: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Atualiza respostas Presente (P) no diagnóstico concluído e recalcula o relatório."""
        if not answers_list:
            raise ValueError("A lista de respostas não pode estar vazia.")

        user_uuid = self._as_uuid(user_id, "user_id")
        submission = self._find_latest_completed_submission(user_id)
        if not submission:
            raise ValueError("Nenhum diagnóstico concluído encontrado para atualizar.")

        if submission.user_id != user_uuid:
            raise PermissionError("Diagnóstico não pertence a este utilizador.")

        framework_id = submission.framework_id
        catalog_items = AssessmentItem.query.filter_by(framework_id=framework_id).all()
        items_by_id = {item.id: item for item in catalog_items}

        present_answers: list[dict[str, Any]] = []
        for answer in answers_list:
            self._assert_answer_is_response_only(answer)
            item_id = self._as_uuid(answer.get("assessment_item_id"), "assessment_item_id")
            item = items_by_id.get(item_id)
            if not item:
                raise ValueError(f"Item de assessment inválido: {item_id}")
            if _prefu_for_item(item) != "P":
                raise ValueError(
                    "Somente respostas de Realidade (Presente) podem ser atualizadas após a conclusão."
                )
            present_answers.append(answer)

        self._upsert_responses(submission, user_uuid, submission.tenant_id, present_answers)

        responses = AssessmentResponse.query.filter_by(submission_id=submission.id).all()
        scoring_result = self._score_submission(submission, responses, catalog_items, items_by_id)

        existing_report = dict(submission.report_data or {})
        baseline = existing_report.get("baseline_snapshot")
        if not baseline:
            baseline = build_baseline_snapshot(existing_report) if existing_report else None

        report = build_diagnostic_report(submission, generate_ai_plan=False)
        persist_diagnostic_report(submission, report)
        if baseline and submission.report_data:
            submission.report_data["baseline_snapshot"] = baseline

        db.session.commit()

        return {
            "submission_id": str(submission.id),
            "status": "completed",
            "updated": len(present_answers),
            **scoring_result,
            "has_diagnostic_report": bool(submission.report_data),
        }

    def process_submission(
        self,
        user_id: uuid.UUID | str,
        answers_list: list[dict[str, Any]],
    ) -> dict[str, Any]:
        tenant_id = g.tenant_id
        framework_id = g.framework_id
        user_uuid = self._as_uuid(user_id, "user_id")

        if not answers_list:
            raise ValueError("A lista de respostas não pode estar vazia.")

        if self._find_latest_completed_submission(user_id):
            existing = self._find_latest_completed_submission(user_id)
            if existing and existing.report_data and existing.score_global is not None:
                raise ValueError(
                    "Diagnóstico já concluído. Revise o questionário e atualize a Realidade (Presente)."
                )
            if existing:
                submission = existing
                submission.status = "in_progress"
            else:
                submission = self._find_draft_submission(user_id)
        else:
            submission = self._find_draft_submission(user_id)

        if not submission:
            submission = AssessmentSubmission(
                tenant_id=tenant_id,
                user_id=user_uuid,
                framework_id=framework_id,
                status="in_progress",
            )
            db.session.add(submission)
            db.session.flush()

        self._upsert_responses(submission, user_uuid, tenant_id, answers_list)

        responses = AssessmentResponse.query.filter_by(submission_id=submission.id).all()
        if not responses:
            raise ValueError("Não há respostas para calcular o diagnóstico.")

        item_ids = [resp.assessment_item_id for resp in responses]
        items = (
            AssessmentItem.query.filter(
                AssessmentItem.id.in_(item_ids),
                AssessmentItem.framework_id == framework_id,
            ).all()
        )

        catalog_items = (
            AssessmentItem.query.filter_by(framework_id=framework_id).all()
        )

        if len(items) != len(set(item_ids)):
            raise ValueError(
                "Um ou mais itens de assessment são inválidos ou não pertencem ao framework informado."
            )

        items_by_id = {item.id: item for item in items}
        scoring = None
        try:
            from app.services.diagnostic_scoring_service import (
                apply_maturity_scores_to_submission,
                build_scoring_payload,
            )

            scoring = build_scoring_payload(
                responses, items_by_id, catalog_items=catalog_items
            )
            scores_por_eixo = scoring.get("scores_por_eixo") or {}
            score_global = scoring.get("score_global", 0.0)
            maturity = scoring.get("maturity_scores")
            if maturity:
                apply_maturity_scores_to_submission(submission, maturity)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        except Exception:
            axis_values: dict[str, list[float]] = defaultdict(list)
            for resp in responses:
                if resp.selected_value is None:
                    continue
                item = items_by_id.get(resp.assessment_item_id)
                if not item:
                    continue
                axis_values[item.axis].append(float(resp.selected_value))
            scores_por_eixo = {
                axis: round(sum(values) / len(values), 2)
                for axis, values in axis_values.items()
            }
            score_global = round(
                sum(scores_por_eixo.values()) / len(scores_por_eixo), 2
            ) if scores_por_eixo else 0.0

        if not scores_por_eixo:
            raise ValueError("Não foi possível calcular scores por eixo.")

        maturity_level = self._resolve_maturity_level(framework_id, score_global)

        submission.score_global = score_global
        submission.maturity_level_name = maturity_level.name
        submission.scores_por_eixo = scores_por_eixo
        submission.status = "completed"

        report = build_diagnostic_report(submission, generate_ai_plan=False)
        persist_diagnostic_report(submission, report)

        from app.services.client_journey_service import advance_after_assessment

        advance_after_assessment(tenant_id)
        action_plan_id = submission.action_plan_id
        db.session.commit()

        full_result = self.get_my_latest_submission()
        if full_result:
            return full_result

        return {
            "submission_id": str(submission.id),
            "framework_id": framework_id,
            "score_global": score_global,
            "nivel_maturidade": maturity_level.name,
            "maturity_level_description": maturity_level.description,
            "scores_por_eixo": scores_por_eixo,
            "action_plan_id": str(action_plan_id) if action_plan_id else None,
            "action_plan_md": report.get("action_plan_md"),
            "has_diagnostic_report": bool(submission.report_data),
            "report_summary": {
                "score_geral_gap": report.get("score_geral_gap"),
                "top_actions_count": len(report.get("top_actions") or []),
            },
        }

    def get_questionnaire(self) -> dict[str, Any]:
        """Catálogo publicado do framework ativo — somente leitura (lead e admin no diagnóstico)."""
        framework_id = g.framework_id
        items = (
            AssessmentItem.query.filter_by(framework_id=framework_id)
            .order_by(AssessmentItem.axis.asc(), AssessmentItem.id.asc())
            .all()
        )

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            dimension = self._dimension_from_axis(item.axis)
            meta = item.item_metadata or {}
            prefu = str(meta.get("prefu_ques") or "").upper()
            temporal_key = "future" if prefu == "F" else "present"
            options = repair_rubric_options(item.options or [], temporal_key=temporal_key)
            grouped[dimension].append(
                {
                    "id": str(item.id),
                    "axis": item.axis,
                    "question_text": item.question_text,
                    "question_type": item.question_type,
                    "prefu_ques": prefu if prefu in ("P", "F") else ("F" if temporal_key == "future" else "P"),
                    "options": options,
                }
            )

        dimensions = [
            {"name": name, "items": grouped[name]} for name in sorted(grouped.keys())
        ]

        items_by_id = {item.id: item for item in items}
        draft = self._find_draft_submission(g.user_id) if getattr(g, "user_id", None) else None
        completeness = None
        if draft:
            draft_responses = AssessmentResponse.query.filter_by(submission_id=draft.id).all()
            completeness = completeness_summary(items, draft_responses, items_by_id)
        elif getattr(g, "user_id", None):
            completed = self._find_latest_completed_submission(g.user_id)
            if completed:
                completed_responses = AssessmentResponse.query.filter_by(
                    submission_id=completed.id
                ).all()
                completeness = completeness_summary(items, completed_responses, items_by_id)

        return {
            "framework_id": framework_id,
            "total_items": len(items),
            "required_questions_per_dimension": 18,
            "required_domains_per_temporal": 9,
            "dimensions": dimensions,
            "completeness": completeness,
        }

    def get_action_plan(self, action_plan_id: uuid.UUID | str) -> dict[str, Any]:
        plan_uuid = self._as_uuid(action_plan_id, "action_plan_id")
        action_plan = db.session.get(ActionPlan, plan_uuid)
        if not action_plan:
            raise ValueError("Plano de ação não encontrado.")
        if action_plan.tenant_id != g.tenant_id and g.system_role != ROLE_SYSADMIN:
            raise PermissionError("Plano de ação não pertence a este tenant.")

        return {
            "id": str(action_plan.id),
            "framework_id": action_plan.framework_id,
            "action_plan_md": action_plan.ai_generated_md,
            "created_at": action_plan.created_at.isoformat() if action_plan.created_at else None,
        }

    def get_my_latest_submission(self) -> dict[str, Any] | None:
        """Último diagnóstico concluído do utilizador autenticado (lead)."""
        submission = self._find_latest_completed_submission(g.user_id)
        if not submission:
            return None

        maturity_description = None
        if submission.maturity_level_name and submission.framework_id:
            level = (
                MaturityLevel.query.filter_by(
                    framework_id=submission.framework_id,
                    name=submission.maturity_level_name,
                ).first()
            )
            if level:
                maturity_description = level.description

        action_plan_md = None
        structured_plan = None
        if submission.action_plan_id:
            plan = db.session.get(ActionPlan, submission.action_plan_id)
            if plan:
                action_plan_md = plan.ai_generated_md
                structured_plan = plan.structured_plan

        report_data = submission.report_data or {}
        framework = db.session.get(Framework, submission.framework_id)
        report_data = enrich_paneldx_comparative_scores(dict(report_data), framework=framework)
        baseline = report_data.get("baseline_snapshot")
        if not baseline and report_data:
            baseline = build_baseline_snapshot(report_data)
            report_data["baseline_snapshot"] = baseline

        return {
            "submission_id": str(submission.id),
            "framework_id": submission.framework_id,
            "score_global": submission.score_global,
            "nivel_maturidade": submission.maturity_level_name,
            "maturity_level_description": maturity_description,
            "scores_por_eixo": submission.scores_por_eixo or {},
            "action_plan_id": str(submission.action_plan_id) if submission.action_plan_id else None,
            "action_plan_md": action_plan_md,
            "structured_plan": structured_plan,
            "score_geral_gap": report_data.get("score_geral_gap"),
            "score_geral_presente": report_data.get("score_geral_presente"),
            "score_geral_futuro": report_data.get("score_geral_futuro"),
            "scores_detalhe_presente": report_data.get("scores_detalhe_presente"),
            "scores_detalhe_futuro": report_data.get("scores_detalhe_futuro"),
            "scores_detalhe_gap": report_data.get("scores_detalhe_gap"),
            "scores_setorial_presente": report_data.get("scores_setorial_presente"),
            "sector": report_data.get("sector"),
            "dimension_labels": report_data.get("dimension_labels") or {},
            "domain_labels": report_data.get("domain_labels") or {},
            "sector_dimension_label": report_data.get("sector_dimension_label"),
            "top_actions": report_data.get("top_actions") or [],
            "has_diagnostic_report": bool(submission.report_data),
            "baseline_snapshot": baseline,
            "evolution": attach_baseline_to_report(report_data, baseline).get("evolution"),
            "questionnaire_status": "completed",
        }

    def get_diagnostic_report(self, submission_id: uuid.UUID | str) -> dict[str, Any]:
        """Relatório completo de diagnóstico (estilo PanelDX)."""
        sub_uuid = self._as_uuid(submission_id, "submission_id")
        submission = db.session.get(AssessmentSubmission, sub_uuid)
        if not submission:
            raise ValueError("Diagnóstico não encontrado.")
        if submission.tenant_id != g.tenant_id and g.system_role != ROLE_SYSADMIN:
            raise PermissionError("Diagnóstico não pertence a este tenant.")
        if submission.status != "completed":
            raise ValueError("Diagnóstico ainda não foi finalizado.")

        if submission.report_data:
            framework = db.session.get(Framework, submission.framework_id)
            report = enrich_paneldx_comparative_scores(
                dict(submission.report_data),
                framework=framework,
            )
            baseline = report.get("baseline_snapshot")
            if not baseline:
                baseline = build_baseline_snapshot(report)
                report["baseline_snapshot"] = baseline
            report = attach_baseline_to_report(report, baseline)
            if submission.action_plan_id:
                plan = db.session.get(ActionPlan, submission.action_plan_id)
                if plan:
                    report["action_plan_md"] = plan.ai_generated_md
                    report["structured_plan"] = plan.structured_plan
            return report

        framework = db.session.get(Framework, submission.framework_id)
        report = build_diagnostic_report(submission, generate_ai_plan=False)
        return enrich_paneldx_comparative_scores(report, framework=framework)

    def list_surveys(self, search: str | None = None) -> list[dict[str, Any]]:
        """Lista surveys realizados por clientes."""
        query = (
            AssessmentSubmission.query.join(Tenant, AssessmentSubmission.tenant_id == Tenant.id)
            .join(User, AssessmentSubmission.user_id == User.id)
            .filter(AssessmentSubmission.status == "completed")
            .order_by(AssessmentSubmission.created_at.desc())
        )

        if g.system_role != ROLE_SYSADMIN:
            query = query.filter(AssessmentSubmission.tenant_id == g.tenant_id)

        if search and len(search.strip()) >= 3:
            term = f"%{search.strip()}%"
            query = query.filter(Tenant.name.ilike(term))

        submissions = query.all()
        results: list[dict[str, Any]] = []

        for sub in submissions:
            response_count = AssessmentResponse.query.filter_by(submission_id=sub.id).count()
            tenant = db.session.get(Tenant, sub.tenant_id)
            user = db.session.get(User, sub.user_id)
            results.append(
                {
                    "id": str(sub.id),
                    "tenant_id": str(sub.tenant_id),
                    "tenant_name": tenant.name if tenant else str(sub.tenant_id),
                    "user_id": str(sub.user_id),
                    "user_name": user.name if user else str(sub.user_id),
                    "framework_id": sub.framework_id,
                    "score_global": sub.score_global,
                    "maturity_level_name": sub.maturity_level_name,
                    "pgen_gap": sub.pgen_gap,
                    "pgen_pres": sub.pgen_pres,
                    "pgen_fut": sub.pgen_fut,
                    "diagnostic_status": sub.diagnostic_status,
                    "scores_por_eixo": sub.scores_por_eixo or {},
                    "action_plan_id": str(sub.action_plan_id) if sub.action_plan_id else None,
                    "response_count": response_count,
                    "status": sub.status,
                    "created_at": sub.created_at.isoformat() if sub.created_at else None,
                }
            )

        return results

    def get_survey(self, submission_id: uuid.UUID | str) -> dict[str, Any]:
        """Detalhe de um survey com respostas — equivalente ao formulário ctdi_surv."""
        sub_uuid = self._as_uuid(submission_id, "submission_id")
        submission = db.session.get(AssessmentSubmission, sub_uuid)
        if not submission:
            raise ValueError("Survey não encontrado.")

        if submission.tenant_id != g.tenant_id and g.system_role != ROLE_SYSADMIN:
            raise PermissionError("Survey não pertence a este tenant.")
        if g.system_role == ROLE_LED and submission.user_id != g.user_id:
            raise PermissionError("Survey não pertence a este utilizador.")

        tenant = db.session.get(Tenant, submission.tenant_id)
        user = db.session.get(User, submission.user_id)

        responses = (
            AssessmentResponse.query.filter_by(submission_id=submission.id)
            .join(AssessmentItem, AssessmentResponse.assessment_item_id == AssessmentItem.id)
            .order_by(AssessmentItem.axis.asc(), AssessmentItem.id.asc())
            .all()
        )

        items_by_id = {r.assessment_item_id: r.assessment_item for r in responses}

        response_rows = []
        for response in responses:
            item = items_by_id.get(response.assessment_item_id)
            response_rows.append(
                {
                    "id": str(response.id),
                    "assessment_item_id": str(response.assessment_item_id),
                    "axis": item.axis if item else None,
                    "question_text": item.question_text if item else None,
                    "selected_value": response.selected_value,
                }
            )

        maturity_description = None
        if submission.maturity_level_name and submission.framework_id:
            level = (
                MaturityLevel.query.filter_by(
                    framework_id=submission.framework_id,
                    name=submission.maturity_level_name,
                ).first()
            )
            if level:
                maturity_description = level.description

        return {
            "id": str(submission.id),
            "tenant_id": str(submission.tenant_id),
            "tenant_name": tenant.name if tenant else None,
            "user_id": str(submission.user_id),
            "user_name": user.name if user else None,
            "framework_id": submission.framework_id,
            "score_global": submission.score_global,
            "nivel_maturidade": submission.maturity_level_name,
            "maturity_level_description": maturity_description,
            "scores_por_eixo": submission.scores_por_eixo or {},
            "maturity_scores": maturity_scores_snapshot(submission),
            "action_plan_id": str(submission.action_plan_id) if submission.action_plan_id else None,
            "status": submission.status,
            "created_at": submission.created_at.isoformat() if submission.created_at else None,
            "responses": response_rows,
        }

    def list_questions_catalog(self) -> list[dict[str, Any]]:
        """Catálogo plano de questões do framework ativo — gestão administrativa."""
        framework_id = g.framework_id
        items = (
            AssessmentItem.query.filter_by(framework_id=framework_id)
            .order_by(AssessmentItem.axis.asc(), AssessmentItem.id.asc())
            .all()
        )
        return [self._serialize_catalog_item(item) for item in items]

    def list_questions_catalog_admin(self) -> dict[str, Any]:
        """Visão global para sysadmin — educação (5 dim.) + domínio setorial por framework."""
        education_items = (
            AssessmentItem.query.filter_by(framework_id=DEFAULT_FRAMEWORK_ID)
            .order_by(AssessmentItem.axis.asc(), AssessmentItem.id.asc())
            .all()
        )

        framework_groups: list[dict[str, Any]] = []
        frameworks = Framework.query.order_by(Framework.name.asc()).all()
        for framework in frameworks:
            if framework.id == DEFAULT_FRAMEWORK_ID:
                continue

            metadata = framework.rules_metadata or {}
            sector_items = [
                self._serialize_catalog_item(item)
                for item in AssessmentItem.query.filter_by(framework_id=framework.id)
                .order_by(AssessmentItem.axis.asc(), AssessmentItem.id.asc())
                .all()
                if not self._is_universal_axis(item.axis)
            ]
            framework_groups.append(
                {
                    "id": framework.id,
                    "name": framework.name,
                    "sector": metadata.get("sector") or framework.industry,
                    "approval_status": metadata.get(
                        "approval_status", APPROVAL_STATUS_APPROVED
                    ),
                    "questions": sector_items,
                    "total": len(sector_items),
                }
            )

        framework_groups.sort(
            key=lambda row: (0 if row.get("approval_status") == APPROVAL_STATUS_APPROVED else 1, row.get("name") or "")
        )

        return {
            "education_framework_id": DEFAULT_FRAMEWORK_ID,
            "education_questions": [self._serialize_catalog_item(item) for item in education_items],
            "education_total": len(education_items),
            "frameworks": framework_groups,
        }

    @classmethod
    def _is_universal_axis(cls, axis: str) -> bool:
        return (axis or "").startswith(UNIVERSAL_AXIS_PREFIXES)

    @classmethod
    def _serialize_catalog_item(cls, item: AssessmentItem) -> dict[str, Any]:
        return {
            "id": str(item.id),
            "framework_id": item.framework_id,
            "axis": item.axis,
            "dimension": cls._dimension_from_axis(item.axis),
            "question_text": item.question_text,
            "question_type": item.question_type,
            "options": item.options or [],
            "is_universal": cls._is_universal_axis(item.axis),
        }

    def _resolve_admin_framework_id(self, payload: dict[str, Any] | None = None) -> str:
        role = getattr(g, "system_role", None)
        requested = (payload or {}).get("framework_id")
        if role == ROLE_SYSADMIN and requested:
            return str(requested).strip()
        return g.framework_id

    def _assert_catalog_item_access(self, item: AssessmentItem | None) -> AssessmentItem:
        if not item:
            raise ValueError("Questão não encontrada.")
        if getattr(g, "system_role", None) == ROLE_SYSADMIN:
            return item
        if item.framework_id != g.framework_id:
            raise ValueError("Questão não encontrada no framework ativo.")
        return item

    def create_question(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Cria item no catálogo do framework — uso exclusivo administrativo (rota /api/questions)."""
        framework_id = self._resolve_admin_framework_id(payload)
        question_text = (payload.get("question_text") or "").strip()
        axis = (payload.get("axis") or "").strip()

        if not question_text or not axis:
            raise ValueError("Campos obrigatórios: question_text, axis.")

        item = AssessmentItem(
            framework_id=framework_id,
            axis=axis,
            question_text=question_text,
            question_type=payload.get("question_type") or "likert_4",
            options=normalize_rubric_options(
                payload.get("options")
                or [
                    {"label": "Inexistente", "description": "1 — Inexistente", "weight": 1},
                    {"label": "Inicial", "description": "2 — Inicial", "weight": 2},
                    {"label": "Definido", "description": "3 — Definido", "weight": 3},
                    {"label": "Otimizado", "description": "4 — Otimizado", "weight": 4},
                ]
            ),
        )
        db.session.add(item)
        db.session.commit()
        return {"id": str(item.id), "message": "Questão criada."}

    def update_question(self, item_id: uuid.UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        item_uuid = self._as_uuid(item_id, "question_id")
        item = self._assert_catalog_item_access(db.session.get(AssessmentItem, item_uuid))

        if "question_text" in payload:
            item.question_text = str(payload["question_text"]).strip()
        if "axis" in payload:
            item.axis = str(payload["axis"]).strip()
        if "question_type" in payload:
            item.question_type = str(payload["question_type"]).strip()
        if "options" in payload:
            item.options = normalize_rubric_options(payload["options"] or [])

        db.session.commit()
        return {"id": str(item.id), "message": "Questão atualizada."}

    def delete_question(self, item_id: uuid.UUID | str) -> dict[str, Any]:
        item_uuid = self._as_uuid(item_id, "question_id")
        item = self._assert_catalog_item_access(db.session.get(AssessmentItem, item_uuid))

        db.session.delete(item)
        db.session.commit()
        return {"message": "Questão removida."}

    @staticmethod
    def _assert_answer_is_response_only(answer: dict[str, Any]) -> None:
        if any(key in answer for key in ("question_text", "axis", "options", "question_type")):
            raise ValueError(
                "O diagnóstico não permite criar ou alterar questões. "
                "Envie apenas assessment_item_id e selected_value."
            )

    def _find_draft_submission(self, user_id: uuid.UUID | str) -> AssessmentSubmission | None:
        user_uuid = self._as_uuid(user_id, "user_id")
        submission = AssessmentSubmission.query.filter_by(
            tenant_id=g.tenant_id,
            user_id=user_uuid,
            framework_id=g.framework_id,
            status="in_progress",
        ).first()
        if submission:
            return submission
        return (
            AssessmentSubmission.query.filter_by(
                tenant_id=g.tenant_id,
                user_id=user_uuid,
                status="in_progress",
            )
            .order_by(AssessmentSubmission.updated_at.desc())
            .first()
        )

    def _find_latest_completed_submission(
        self, user_id: uuid.UUID | str, framework_id: str | None = None
    ) -> AssessmentSubmission | None:
        user_uuid = self._as_uuid(user_id, "user_id")
        fw = framework_id or getattr(g, "framework_id", None)
        if fw:
            submission = (
                AssessmentSubmission.query.filter_by(
                    tenant_id=g.tenant_id,
                    user_id=user_uuid,
                    framework_id=fw,
                    status="completed",
                )
                .order_by(AssessmentSubmission.created_at.desc())
                .first()
            )
            if submission:
                return submission
        return (
            AssessmentSubmission.query.filter_by(
                tenant_id=g.tenant_id,
                user_id=user_uuid,
                status="completed",
            )
            .order_by(AssessmentSubmission.created_at.desc())
            .first()
        )

    def _submission_answers_payload(self, submission: AssessmentSubmission) -> list[dict[str, Any]]:
        responses = AssessmentResponse.query.filter_by(submission_id=submission.id).all()
        answers: list[dict[str, Any]] = []
        for resp in responses:
            option_index = None
            if isinstance(resp.raw_response, dict):
                option_index = resp.raw_response.get("option_index")
            answers.append(
                {
                    "assessment_item_id": str(resp.assessment_item_id),
                    "selected_value": resp.selected_value,
                    "option_index": option_index,
                }
            )
        return answers

    def _score_submission(
        self,
        submission: AssessmentSubmission,
        responses: list[AssessmentResponse],
        catalog_items: list[AssessmentItem],
        items_by_id: dict[Any, AssessmentItem],
    ) -> dict[str, Any]:
        item_ids = [resp.assessment_item_id for resp in responses]
        items = [items_by_id[item_id] for item_id in item_ids if item_id in items_by_id]

        if len(items) != len(set(item_ids)):
            raise ValueError(
                "Um ou mais itens de assessment são inválidos ou não pertencem ao framework informado."
            )

        try:
            from app.services.diagnostic_scoring_service import (
                apply_maturity_scores_to_submission,
                build_scoring_payload,
            )

            scoring = build_scoring_payload(
                responses, items_by_id, catalog_items=catalog_items
            )
            scores_por_eixo = scoring.get("scores_por_eixo") or {}
            score_global = scoring.get("score_global", 0.0)
            maturity = scoring.get("maturity_scores")
            if maturity:
                apply_maturity_scores_to_submission(submission, maturity)
        except ValueError:
            raise
        except Exception:
            axis_values: dict[str, list[float]] = defaultdict(list)
            for resp in responses:
                if resp.selected_value is None:
                    continue
                item = items_by_id.get(resp.assessment_item_id)
                if not item:
                    continue
                axis_values[item.axis].append(float(resp.selected_value))
            scores_por_eixo = {
                axis: round(sum(values) / len(values), 2)
                for axis, values in axis_values.items()
            }
            score_global = round(
                sum(scores_por_eixo.values()) / len(scores_por_eixo), 2
            ) if scores_por_eixo else 0.0

        if not scores_por_eixo:
            raise ValueError("Não foi possível calcular scores por eixo.")

        maturity_level = self._resolve_maturity_level(submission.framework_id, score_global)
        submission.score_global = score_global
        submission.maturity_level_name = maturity_level.name
        submission.scores_por_eixo = scores_por_eixo

        return {
            "score_global": score_global,
            "nivel_maturidade": maturity_level.name,
            "maturity_level_description": maturity_level.description,
            "scores_por_eixo": scores_por_eixo,
        }

    def _get_or_create_draft_submission(
        self,
        user_uuid: uuid.UUID,
        tenant_id: uuid.UUID,
        framework_id: str,
    ) -> AssessmentSubmission:
        submission = AssessmentSubmission.query.filter_by(
            tenant_id=tenant_id,
            user_id=user_uuid,
            framework_id=framework_id,
            status="in_progress",
        ).first()
        if submission:
            return submission

        submission = AssessmentSubmission(
            tenant_id=tenant_id,
            user_id=user_uuid,
            framework_id=framework_id,
            status="in_progress",
        )
        db.session.add(submission)
        db.session.flush()
        return submission

    def _upsert_responses(
        self,
        submission: AssessmentSubmission,
        user_uuid: uuid.UUID,
        tenant_id: uuid.UUID,
        answers_list: list[dict[str, Any]],
    ) -> None:
        for answer in answers_list:
            self._assert_answer_is_response_only(answer)
            item_id = self._as_uuid(answer.get("assessment_item_id"), "assessment_item_id")
            selected_value = answer.get("selected_value")

            if selected_value is None:
                raise ValueError(f"selected_value ausente para o item {item_id}.")

            option_index = answer.get("option_index")
            raw_response = (
                {"option_index": option_index}
                if option_index is not None
                else None
            )

            existing = AssessmentResponse.query.filter_by(
                submission_id=submission.id,
                assessment_item_id=item_id,
            ).first()

            if existing:
                existing.selected_value = float(selected_value)
                existing.raw_response = raw_response
            else:
                db.session.add(
                    AssessmentResponse(
                        tenant_id=tenant_id,
                        submission_id=submission.id,
                        assessment_item_id=item_id,
                        user_id=user_uuid,
                        selected_value=float(selected_value),
                        raw_response=raw_response,
                    )
                )

    @staticmethod
    def _dimension_from_axis(axis: str) -> str:
        if " / " in axis:
            return axis.split(" / ", 1)[0].strip()
        return axis.strip() or "Geral"

    def _resolve_maturity_level(
        self, framework_id: str, global_score: float
    ) -> MaturityLevel:
        levels = (
            MaturityLevel.query.filter_by(framework_id=framework_id)
            .order_by(MaturityLevel.level.asc())
            .all()
        )

        if not levels:
            raise ValueError(
                f"Níveis de maturidade não configurados para o framework '{framework_id}'."
            )

        if global_score <= 1.5:
            target_level = 1
        elif global_score <= 2.5:
            target_level = 2
        elif global_score <= 3.5:
            target_level = 3
        else:
            target_level = 4

        for maturity in levels:
            if maturity.level == target_level:
                return maturity

        raise ValueError(
            f"Nível de maturidade {target_level} não encontrado para o framework '{framework_id}'."
        )

    @staticmethod
    def _as_uuid(value: Any, field_name: str) -> uuid.UUID:
        if value is None:
            raise ValueError(f"Campo obrigatório ausente: {field_name}.")
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"UUID inválido em '{field_name}': {value}") from exc
