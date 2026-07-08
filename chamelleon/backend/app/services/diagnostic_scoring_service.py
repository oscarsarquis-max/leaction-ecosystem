"""Motor de scoring — integração Chamelleon ↔ rotinas PanelDX (ctdi_matu)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.sector_constants import LEGACY_DIME_ID_TO_KEY, LEGACY_DOMAIN_ID_TO_KEY
from app.database.models import AssessmentItem, AssessmentResponse, AssessmentSubmission
from app.services.diagnostic_completeness import validate_diagnostic_completeness
from app.services.paneldx_maturity_calculator import (
    DIAGNOSTIC_STATUS_EVALUATED,
    finalize_maturity_calculation,
    normalize_prefu,
)

MATURITY_SCORE_COLUMNS = (
    "pdom_pres",
    "pdim_pres",
    "pgen_pres",
    "pdom_fut",
    "pdim_fut",
    "pgen_fut",
    "pdom_gap",
    "pdim_gap",
    "pgen_gap",
    "pdom_sect_pres",
    "pdim_sect_pres",
    "pgen_sect_pres",
    "pdom_sect_fut",
    "pdim_sect_fut",
    "pgen_sect_fut",
    "pdom_sect_gap",
    "pdim_sect_gap",
    "pgen_sect_gap",
    "matrix_domain_stats",
    "matrix_meta",
    "diagnostic_status",
)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in ("na", "null", ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _item_legacy_ids(item: AssessmentItem) -> tuple[int | None, int | None, str]:
    meta = item.item_metadata or {}
    id_dime = meta.get("legacy_id_dime")
    id_doma = meta.get("legacy_id_doma")
    dim_key = meta.get("dimension_key", "")

    if id_dime is None and dim_key:
        from app.data.legacy_quest_loader import LEGACY_DIME_TO_KEY

        rev = {v: k for k, v in LEGACY_DIME_TO_KEY.items()}
        id_dime = rev.get(str(dim_key).upper())

    if id_doma is None:
        dom_key = meta.get("domain_key")
        if dom_key:
            from app.data.legacy_quest_loader import LEGACY_DOMA_TO_KEY

            rev_dom = {v: k for k, v in LEGACY_DOMA_TO_KEY.items()}
            id_doma = rev_dom.get(str(dom_key).lower())

    prefu = str(meta.get("prefu_ques") or "P").upper()
    if prefu not in ("P", "F"):
        if "(Futuro)" in (item.axis or ""):
            prefu = "F"
        else:
            prefu = "P"
    return id_dime, id_doma, prefu


def _is_sector_item(item: AssessmentItem, id_dime: int | None) -> bool:
    meta = item.item_metadata or {}
    dim_type = meta.get("dimension_type", "universal")
    dim_key = str(meta.get("dimension_key", "")).upper()
    setor = str(meta.get("setor") or meta.get("sector") or "").strip().upper()
    return (
        dim_type == "sector"
        or dim_key == "LA"
        or id_dime == 4
        or setor in ("EDUCACAO", "EDUCAÇÃO")
    )


def responses_to_paneldx_answers(
    responses: list[AssessmentResponse],
    items_by_id: dict[Any, AssessmentItem],
) -> list[dict[str, Any]]:
    """Converte respostas Chamelleon para o formato de cálculo PanelDX (ctdi_surv + ctdi_quest)."""
    answers: list[dict[str, Any]] = []
    for resp in responses:
        item = items_by_id.get(resp.assessment_item_id)
        if not item:
            continue
        grad = _safe_float(resp.selected_value)
        if grad is None:
            continue

        id_dime, id_doma, prefu = _item_legacy_ids(item)
        meta = item.item_metadata or {}
        answers.append(
            {
                "id_ques": str(item.id),
                "grad_ques": grad,
                "id_dime": id_dime,
                "id_doma": id_doma,
                "prefu_ques": prefu,
                "setor_ques": meta.get("setor") or meta.get("sector") or "",
                "is_sector": _is_sector_item(item, id_dime),
            }
        )
    return answers


def build_scoring_payload(
    responses: list[AssessmentResponse],
    items_by_id: dict[Any, AssessmentItem],
    *,
    catalog_items: list[AssessmentItem] | None = None,
) -> dict[str, Any]:
    """Calcula matriz completa via rotinas PanelDX (ctdi_matu)."""
    if catalog_items:
        validate_diagnostic_completeness(catalog_items, responses, items_by_id)

    all_answers = responses_to_paneldx_answers(responses, items_by_id)
    maturity = finalize_maturity_calculation(all_answers, require_present_and_future=True)

    scores_por_eixo: dict[str, float] = {}
    for resp in responses:
        item = items_by_id.get(resp.assessment_item_id)
        if not item or resp.selected_value is None:
            continue
        if normalize_prefu((item.item_metadata or {}).get("prefu_ques")) == "P":
            scores_por_eixo[item.axis] = round(float(resp.selected_value), 2)

    score_global = maturity["pgen_pres"] if maturity["pgen_pres"] > 0 else (
        round(sum(scores_por_eixo.values()) / len(scores_por_eixo), 2) if scores_por_eixo else 0.0
    )

    domain_keys = set(maturity["pdom_pres"]) | set(maturity["pdom_fut"]) | set(maturity["pdom_sect_pres"])
    dimension_keys = set(maturity["pdim_pres"]) | set(maturity["pdim_fut"]) | set(maturity["pdim_sect_pres"])

    return {
        "score_global": score_global,
        "scores_por_eixo": scores_por_eixo,
        "general": maturity["general"],
        "sector": maturity["sector"],
        "maturity_scores": maturity,
        "domain_labels": {
            str(k): LEGACY_DOMAIN_ID_TO_KEY.get(int(k), f"dom{k}") for k in domain_keys if str(k).isdigit()
        },
        "dimension_labels": {
            str(k): LEGACY_DIME_ID_TO_KEY.get(int(k), f"dim{k}") for k in dimension_keys if str(k).isdigit()
        },
    }


def apply_maturity_scores_to_submission(
    submission: AssessmentSubmission,
    maturity: dict[str, Any],
) -> None:
    """Persiste os 18 scores + matriz híbrida na submissão (equivalente update_maturity_scores)."""
    for column in MATURITY_SCORE_COLUMNS:
        if column in maturity:
            setattr(submission, column, maturity[column])
    submission.diagnostic_status = maturity.get("diagnostic_status", DIAGNOSTIC_STATUS_EVALUATED)
    submission.evaluated_at = datetime.now(timezone.utc)


def maturity_scores_snapshot(submission: AssessmentSubmission) -> dict[str, Any]:
    """Lê scores persistidos no formato PanelDX."""
    return {
        column: getattr(submission, column, None)
        for column in MATURITY_SCORE_COLUMNS
    }
