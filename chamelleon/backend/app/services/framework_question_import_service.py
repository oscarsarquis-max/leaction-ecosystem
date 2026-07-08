"""Importação de questões via JSON para frameworks aprovados."""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.data.rubric_patterns import normalize_rubric_options
from app.database.models import AssessmentItem, Framework, db
from app.services.framework_builder_service import APPROVAL_STATUS_APPROVED

REQUIRED_FIELDS = ("axis", "question_text", "question_type")


class FrameworkQuestionImportService:
    def import_json_file(self, framework_id: str, raw_content: bytes) -> dict[str, Any]:
        framework = self._get_approved_framework(framework_id)

        if not raw_content:
            raise ValueError("Arquivo JSON vazio.")

        try:
            payload = json.loads(raw_content.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"JSON inválido: {exc}") from exc

        rows = self._extract_question_rows(payload)
        if not rows:
            raise ValueError("Nenhuma questão encontrada no JSON.")

        imported = 0
        errors: list[str] = []

        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                errors.append(f"Item #{index}: esperado objeto JSON.")
                continue
            try:
                item = self._build_assessment_item(framework.id, row)
                db.session.add(item)
                imported += 1
            except ValueError as exc:
                errors.append(f"Item #{index}: {exc}")

        if imported == 0:
            detail = "; ".join(errors[:5])
            raise ValueError(
                f"Nenhuma questão importada. {detail}" if detail else "Nenhuma questão válida."
            )

        db.session.commit()

        return {
            "status": "ok",
            "framework_id": framework.id,
            "imported_count": imported,
            "total_in_file": len(rows),
            "skipped_count": len(rows) - imported,
            "errors": errors[:20],
            "message": f"{imported} questão(ões) importada(s) com sucesso.",
        }

    @staticmethod
    def _get_approved_framework(framework_id: str) -> Framework:
        framework = db.session.get(Framework, framework_id)
        if not framework:
            raise ValueError(f"Framework '{framework_id}' não encontrado.")

        approval_status = (framework.rules_metadata or {}).get(
            "approval_status", APPROVAL_STATUS_APPROVED
        )
        if approval_status != APPROVAL_STATUS_APPROVED:
            raise ValueError(
                "Importação de questões disponível apenas para frameworks com status Aprovado."
            )
        return framework

    @staticmethod
    def _extract_question_rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]

        if isinstance(payload, dict):
            for key in ("questions", "items", "assessment_items", "questoes"):
                candidate = payload.get(key)
                if isinstance(candidate, list):
                    return [row for row in candidate if isinstance(row, dict)]

        raise ValueError(
            "Formato JSON inválido. Envie uma lista de questões ou um objeto "
            'com chave "questions".'
        )

    @staticmethod
    def _build_assessment_item(framework_id: str, row: dict[str, Any]) -> AssessmentItem:
        axis = str(row.get("axis") or "").strip()
        question_text = str(row.get("question_text") or row.get("desc_ques") or "").strip()
        question_type = str(row.get("question_type") or "multiple_choice").strip()

        if not axis:
            raise ValueError("Campo obrigatório ausente: axis.")
        if not question_text:
            raise ValueError("Campo obrigatório ausente: question_text.")
        if not question_type:
            raise ValueError("Campo obrigatório ausente: question_type.")

        raw_options = row.get("options")
        if raw_options is None:
            raw_options = []
        if not isinstance(raw_options, list):
            raise ValueError("Campo options deve ser uma lista.")

        metadata = row.get("item_metadata") or row.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise ValueError("Campo item_metadata deve ser um objeto JSON.")

        item_meta = dict(metadata or {})
        item_meta.setdefault("import_source", "json_upload")

        return AssessmentItem(
            id=uuid.uuid4(),
            framework_id=framework_id,
            axis=axis,
            question_text=question_text,
            question_type=question_type,
            options=normalize_rubric_options(raw_options),
            item_metadata=item_meta,
        )
