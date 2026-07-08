"""Seed do framework padrão Educação (educacao-v1) — ingestão completa PanelDX."""

from __future__ import annotations

import logging
from typing import Any

from app.core.dev_users import DEV_FRAMEWORK_ID
from app.core.sector_constants import (
    DEFAULT_SECTOR,
    DEFAULT_SECTOR_ACRONYM,
    DEFAULT_SECTOR_ACTION_NAME,
    DEFAULT_SECTOR_FULL_LABEL,
    DOMAIN_NAMES_PT,
)
from app.data.legacy_framework_loader import (
    build_full_methodology_document,
    load_la_methodology_structure,
    methodology_summary_counts,
)
from app.data.legacy_quest_loader import (
    load_la_sector_assessment_items,
    load_universal_assessment_items,
    universal_dimensions_summary,
)
from app.data.maturity_defaults import DEFAULT_MATURITY_LEVELS
from app.data.rubric_patterns import normalize_rubric_options, repair_rubric_options
from app.database.models import AssessmentItem, Framework, MaturityLevel, db
from app.services.framework_taxonomy_service import (
    ensure_framework_taxonomy,
    import_taxonomy_from_legacy,
)

logger = logging.getLogger(__name__)


def _group_la_questions_by_domain(
    la_items: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    """domain_key -> { present|future -> item }"""
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for item in la_items:
        meta = item.get("metadata") or {}
        domain_key = meta.get("domain_key")
        if not domain_key:
            continue
        temporal = meta.get("temporal_key") or (
            "present" if str(meta.get("prefu_ques", "P")).upper() == "P" else "future"
        )
        grouped.setdefault(domain_key, {})[temporal] = item
    return grouped


def _build_operational_dimension(
    la_methodology: dict[str, Any],
    la_questions: list[dict[str, Any]],
) -> dict[str, Any]:
    questions_by_domain = _group_la_questions_by_domain(la_questions)
    building_blocks: list[dict[str, Any]] = []

    for domain in la_methodology.get("domains") or []:
        domain_key = domain.get("domain_key") or ""
        if not domain_key:
            continue
        domain_name = (
            domain.get("name_doma")
            or DOMAIN_NAMES_PT.get(domain_key, domain_key)
        )
        blocks = domain.get("blocks") or []
        primary_block = blocks[0] if blocks else {}
        block_name = primary_block.get("name_bloc") or domain_name
        block_desc = primary_block.get("desc_bloc") or f"Capacidades de {domain_name} na educação."

        leaf_blocks: list[dict[str, Any]] = []
        for bloc in blocks:
            leaf_blocks.append(
                {
                    "id_bloc": bloc.get("id_bloc"),
                    "name_bloc": bloc.get("name_bloc"),
                    "desc_bloc": bloc.get("desc_bloc"),
                    "level_bloc": bloc.get("level_bloc"),
                    "deliverables": bloc.get("deliverables") or [],
                }
            )

        qmap = questions_by_domain.get(domain_key, {})
        present_item = qmap.get("present")
        future_item = qmap.get("future")

        def _question_payload(item: dict[str, Any] | None, temporal: str) -> dict[str, Any]:
            if not item:
                return {
                    "question_text": (
                        f"Qual o nível em {domain_name} ({'presente' if temporal == 'present' else 'futuro'})?"
                    ),
                    "question_type": "multiple_choice",
                    "prefu_ques": "P" if temporal == "present" else "F",
                    "options": normalize_rubric_options([]),
                }
            meta = item.get("metadata") or {}
            prefu = meta.get("prefu_ques") or ("P" if temporal == "present" else "F")
            options = repair_rubric_options(
                item.get("options") or [],
                temporal_key=temporal,
            )
            return {
                "question_text": item.get("question_text", ""),
                "question_type": item.get("question_type", "multiple_choice"),
                "prefu_ques": prefu,
                "options": options,
            }

        building_blocks.append(
            {
                "domain_key": domain_key,
                "domain_name": domain_name,
                "block_name": block_name,
                "block_description": block_desc,
                "leaf_blocks": leaf_blocks,
                "assessment_questions": {
                    "present": _question_payload(present_item, "present"),
                    "future": _question_payload(future_item, "future"),
                },
            }
        )

    return {
        "name": DEFAULT_SECTOR_ACTION_NAME,
        "acronym": DEFAULT_SECTOR_ACRONYM,
        "full_label": DEFAULT_SECTOR_FULL_LABEL,
        "description": (
            "Dimensão canônica de Aprendizagem em Ação (LA) — setor Educação. "
            "Substitui o template LA por si mesma; demais setores geram dimensões equivalentes via Builder."
        ),
        "is_canonical_la": True,
        "building_blocks": building_blocks,
    }


def _upsert_assessment_items(framework_id: str, items: list[dict[str, Any]]) -> int:
    """Insere ou atualiza itens por eixo + prefu."""
    existing: dict[tuple[str, str], AssessmentItem] = {}
    for row in AssessmentItem.query.filter_by(framework_id=framework_id).all():
        meta = row.item_metadata or {}
        prefu = str(meta.get("prefu_ques") or "P").upper()
        dim_type = meta.get("dimension_type", "universal")
        if dim_type == "sector":
            key = (str(meta.get("domain_key") or ""), prefu)
        else:
            key = (str(meta.get("dimension_key") or row.axis), prefu)
        existing[key] = row

    count = 0
    for item_data in items:
        meta = dict(item_data.get("metadata") or {})
        dim_type = meta.get("dimension_type", "universal")
        prefu = str(meta.get("prefu_ques") or "P").upper()
        if dim_type == "sector":
            lookup = (str(meta.get("domain_key") or ""), prefu)
        else:
            lookup = (str(meta.get("dimension_key") or item_data["axis"]), prefu)

        temporal_key = "future" if prefu == "F" else "present"
        options = item_data.get("options") or []
        if dim_type == "sector":
            options = repair_rubric_options(options, temporal_key=temporal_key)
        else:
            options = normalize_rubric_options(options)

        row = existing.get(lookup)
        if row:
            row.axis = item_data["axis"]
            row.question_text = item_data["question_text"]
            row.question_type = item_data.get("question_type", "multiple_choice")
            row.options = options
            row.item_metadata = meta
        else:
            db.session.add(
                AssessmentItem(
                    framework_id=framework_id,
                    axis=item_data["axis"],
                    question_text=item_data["question_text"],
                    question_type=item_data.get("question_type", "multiple_choice"),
                    options=options,
                    item_metadata=meta,
                )
            )
        count += 1
    return count


def ensure_education_framework(*, force_refresh: bool = False) -> str:
    """
    Garante framework educacao-v1 completo: universal + LA + metodologia leaf_bloc/leaf_derv.
    Retorna framework_id.
    """
    framework_id = DEV_FRAMEWORK_ID
    la_methodology = load_la_methodology_structure()
    la_questions = load_la_sector_assessment_items()
    universal_items = load_universal_assessment_items()
    op_dim = _build_operational_dimension(la_methodology, la_questions)
    methodology_doc = build_full_methodology_document(operational_dimension=op_dim)
    counts = methodology_summary_counts(methodology_doc)

    existing = db.session.get(Framework, framework_id)
    if existing and not force_refresh:
        meta = existing.rules_metadata or {}
        if (
            meta.get("ingestion_complete")
            and meta.get("methodology_document")
            and AssessmentItem.query.filter_by(framework_id=framework_id).count()
            >= len(universal_items) + len(la_questions)
        ):
            if not existing.is_active:
                existing.is_active = True
                db.session.commit()
            try:
                ensure_framework_taxonomy(framework_id)
            except Exception as exc:
                logger.warning("Taxonomia Educação não carregada: %s", exc)
            return framework_id

    if existing and force_refresh:
        AssessmentItem.query.filter_by(framework_id=framework_id).delete()
        MaturityLevel.query.filter_by(framework_id=framework_id).delete()
        db.session.delete(existing)
        db.session.flush()

    if not existing or force_refresh:
        framework = Framework(
            id=framework_id,
            name="Chamelleon — Framework Educação",
            industry=DEFAULT_SECTOR,
            version="1.0",
            is_active=True,
            rules_metadata={},
        )
        db.session.add(framework)
    else:
        framework = existing
        framework.is_active = True

    framework.name = "Chamelleon — Framework Educação"
    framework.industry = DEFAULT_SECTOR
    framework.rules_metadata = {
        "sector": DEFAULT_SECTOR,
        "bootstrap": True,
        "ingestion_complete": True,
        "is_default_sector": True,
        "is_canonical_la": True,
        "manifest": {
            "name": "Chamelleon — Framework Educação",
            "descricao": (
                "Framework de maturidade digital para o setor Educação, "
                "com 4 dimensões universais PanelDX e dimensão LA (Aprendizagem em Ação) canônica."
            ),
        },
        "operational_dimension_acronym": DEFAULT_SECTOR_ACRONYM,
        "operational_dimension_name": DEFAULT_SECTOR_FULL_LABEL,
        "operational_dimension": op_dim,
        "methodology_document": methodology_doc,
        "methodology_counts": counts,
        "universal_dimensions": universal_dimensions_summary(),
        "approval_status": "approved",
        "scale_min": 1,
        "scale_max": 4,
    }

    if MaturityLevel.query.filter_by(framework_id=framework_id).count() == 0:
        for level, name, description in DEFAULT_MATURITY_LEVELS:
            db.session.add(
                MaturityLevel(
                    framework_id=framework_id,
                    level=level,
                    name=name,
                    description=description,
                )
            )

    universal_meta_items: list[dict[str, Any]] = []
    for item in universal_items:
        meta = dict(item.get("metadata") or {})
        meta["dimension_type"] = "universal"
        if "prefu_ques" not in meta:
            axis = item.get("axis", "")
            if "(Futuro)" in axis:
                meta["prefu_ques"] = "F"
                meta["temporal_key"] = "future"
            elif "(Presente)" in axis:
                meta["prefu_ques"] = "P"
                meta["temporal_key"] = "present"
        universal_meta_items.append({**item, "metadata": meta})

    sector_meta_items: list[dict[str, Any]] = []
    for item in la_questions:
        meta = dict(item.get("metadata") or {})
        meta["dimension_type"] = "sector"
        meta["operational_acronym"] = DEFAULT_SECTOR_ACRONYM
        meta["sector"] = DEFAULT_SECTOR
        sector_meta_items.append({**item, "metadata": meta})

    total = _upsert_assessment_items(framework_id, universal_meta_items + sector_meta_items)
    db.session.commit()

    try:
        if force_refresh:
            taxonomy_counts = import_taxonomy_from_legacy(framework_id)
        else:
            taxonomy_counts = ensure_framework_taxonomy(framework_id)
    except Exception as exc:
        logger.warning("Taxonomia PanelDX não importada para '%s': %s", framework_id, exc)
        taxonomy_counts = {}

    logger.info(
        "Framework Educação '%s' pronto — %d itens, %d blocos metodologia, %d entregáveis; "
        "taxonomia: %s.",
        framework_id,
        total,
        counts.get("blocks", 0),
        counts.get("deliverables", 0),
        taxonomy_counts,
    )
    return framework_id
