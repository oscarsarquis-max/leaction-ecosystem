"""Gaps dimensão×domínio e acoplamento a blocos/entregáveis do framework (metodologia PanelDX)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from app.core.sector_constants import LEGACY_DOMAIN_ID_TO_KEY
from app.core.td_constants import ASSESSMENT_DOMAIN_TO_TD, TD_OFFICIAL_DOMAINS
from app.database.models import (
    AssessmentItem,
    AssessmentResponse,
    AssessmentSubmission,
    FrameworkBlock,
    FrameworkDeliverable,
    FrameworkDimension,
    FrameworkDomain,
)
from app.services.diagnostic_scoring_service import _item_legacy_ids, _safe_float


def _map_domain_to_td(domain: FrameworkDomain | None) -> str:
    if not domain:
        return TD_OFFICIAL_DOMAINS[0]
    if domain.domain_key:
        mapped = ASSESSMENT_DOMAIN_TO_TD.get(str(domain.domain_key).lower())
        if mapped:
            return mapped
    if domain.legacy_id_doma is not None:
        canon = LEGACY_DOMAIN_ID_TO_KEY.get(int(domain.legacy_id_doma))
        if canon:
            mapped = ASSESSMENT_DOMAIN_TO_TD.get(canon)
            if mapped:
                return mapped
    name = (domain.name_doma or "").strip()
    for official in TD_OFFICIAL_DOMAINS:
        if official.lower() in name.lower() or name.lower() in official.lower():
            return official
    return TD_OFFICIAL_DOMAINS[2]  # Processos


def compute_dimension_domain_gaps(submission: AssessmentSubmission) -> list[dict[str, Any]]:
    """Calcula gap F−P por par (dimensão, domínio) a partir das respostas do diagnóstico."""
    responses = AssessmentResponse.query.filter_by(submission_id=submission.id).all()
    if not responses:
        return []

    items = {
        item.id: item
        for item in AssessmentItem.query.filter_by(framework_id=submission.framework_id).all()
    }
    buckets: dict[tuple[int, int], dict[str, list[float]]] = defaultdict(
        lambda: {"p": [], "f": []}
    )

    for resp in responses:
        item = items.get(resp.assessment_item_id)
        if not item:
            continue
        id_dime, id_doma, prefu = _item_legacy_ids(item)
        if id_dime is None or id_doma is None:
            continue
        grad = _safe_float(resp.selected_value)
        if grad is None:
            continue
        key = (int(id_dime), int(id_doma))
        if prefu == "P":
            buckets[key]["p"].append(grad)
        elif prefu == "F":
            buckets[key]["f"].append(grad)

    pairs: list[dict[str, Any]] = []
    for (legacy_id_dime, legacy_id_doma), bucket in buckets.items():
        if not bucket["p"] or not bucket["f"]:
            continue
        pres = sum(bucket["p"]) / len(bucket["p"])
        fut = sum(bucket["f"]) / len(bucket["f"])
        gap = round(fut - pres, 2)
        if gap <= 0:
            continue
        pairs.append(
            {
                "legacy_id_dime": legacy_id_dime,
                "legacy_id_doma": legacy_id_doma,
                "score_presente": round(pres, 2),
                "score_futuro": round(fut, 2),
                "gap_fp": gap,
            }
        )

    pairs.sort(key=lambda row: (-row["gap_fp"], row["legacy_id_dime"], row["legacy_id_doma"]))
    return pairs


def build_block_candidates(
    submission: AssessmentSubmission,
) -> list[dict[str, Any]]:
    """
    Uma sprint candidata por par dimensão×domínio com gap F−P positivo,
    acoplada ao bloco metodológico e entregável do framework ativo.
    """
    framework_id = submission.framework_id
    gap_pairs = compute_dimension_domain_gaps(submission)
    if not gap_pairs:
        return []

    dimensions = FrameworkDimension.query.filter_by(framework_id=framework_id).all()
    domains = FrameworkDomain.query.filter_by(framework_id=framework_id).all()
    dims_by_legacy = {
        int(d.legacy_id_dime): d for d in dimensions if d.legacy_id_dime is not None
    }
    doms_by_legacy = {
        int(d.legacy_id_doma): d for d in domains if d.legacy_id_doma is not None
    }

    blocks = (
        FrameworkBlock.query.filter_by(framework_id=framework_id)
        .order_by(
            FrameworkBlock.level_bloc.asc().nullslast(),
            FrameworkBlock.legacy_id_bloc.asc().nullslast(),
        )
        .all()
    )
    blocks_by_pair: dict[tuple[str, str], list[FrameworkBlock]] = defaultdict(list)
    for block in blocks:
        if block.dimension_id and block.domain_id:
            blocks_by_pair[(str(block.dimension_id), str(block.domain_id))].append(block)

    deliverables = FrameworkDeliverable.query.filter_by(framework_id=framework_id).all()
    derv_by_block: dict[str, list[FrameworkDeliverable]] = defaultdict(list)
    for derv in deliverables:
        derv_by_block[str(derv.block_id)].append(derv)

    candidates: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for gap_row in gap_pairs:
        dim = dims_by_legacy.get(gap_row["legacy_id_dime"])
        dom = doms_by_legacy.get(gap_row["legacy_id_doma"])
        if not dim or not dom:
            continue
        pair_key = (str(dim.id), str(dom.id))
        if pair_key in seen_pairs:
            continue
        pair_blocks = blocks_by_pair.get(pair_key) or []
        if not pair_blocks:
            continue
        seen_pairs.add(pair_key)
        block = pair_blocks[0]
        derv_list = derv_by_block.get(str(block.id)) or []
        derv = derv_list[0] if derv_list else None
        dim_num = dim.legacy_id_dime if dim.legacy_id_dime is not None else dim.display_order
        paneldx_domain = _map_domain_to_td(dom)

        candidates.append(
            {
                "framework_block_id": str(block.id),
                "framework_deliverable_id": str(derv.id) if derv else None,
                "legacy_id_bloc": block.legacy_id_bloc,
                "name_bloc": block.name_bloc,
                "desc_bloc": block.desc_bloc,
                "dimension_id": str(dim.id),
                "domain_id": str(dom.id),
                "dimension_name": dim.name_dime,
                "domain_name": dom.name_doma,
                "dimension_num": dim_num,
                "domain_key": dom.domain_key,
                "paneldx_domain": paneldx_domain,
                "gap_fp": gap_row["gap_fp"],
                "score_presente": gap_row["score_presente"],
                "score_futuro": gap_row["score_futuro"],
                "name_derv": derv.name_derv if derv else None,
                "derv_defi": derv.derv_defi if derv else None,
                "derv_comp": derv.derv_comp if derv else None,
                "derv_metr": derv.derv_metr if derv else None,
                "criteria_dod": dict(derv.criteria_dod or {}) if derv else {},
            }
        )

    candidates.sort(key=lambda row: (-row["gap_fp"], row["dimension_num"], row["domain_name"]))
    return candidates


def format_block_catalog_for_prompt(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "Nenhum par dimensão×domínio com gap F−P positivo e bloco metodológico vinculado."
    lines = [
        "CATÁLOGO DE BLOCOS (use id_bloc exato — UUID do bloco):",
        "Uma sprint por par dimensão×domínio com gap positivo. NÃO invente blocos.",
    ]
    for cand in candidates:
        lines.append(
            f"id_bloc={cand['framework_block_id']} | [DIM {cand['dimension_num']}] "
            f"{cand['name_bloc']} | Domínio: {cand['domain_name']} | "
            f"Dimensão: {cand['dimension_name']} | gap F−P={cand['gap_fp']:.2f}"
        )
        if cand.get("name_derv"):
            lines.append(f"  → Entregável: {cand['name_derv']}")
    return "\n".join(lines)


def parse_block_id(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return str(uuid.UUID(text))
    except (TypeError, ValueError):
        return None


def candidate_by_block_id(
    candidates: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {c["framework_block_id"]: c for c in candidates}
