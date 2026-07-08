"""
Rotinas de cálculo de maturidade copiadas do PanelDX (LeAction_SysF/app.py + seed_dev_client.py).

Referência legada: tabela ctdi_matu — gaps Presente vs Futuro por domínio, dimensão e score geral.
Não altera o PanelDX; apenas replica a lógica no Chamelleon.
"""

from __future__ import annotations

import statistics
from typing import Any

MATRIX_CV_ALPHA = 0.4
MATRIX_WEAKNESS_BETA = 0.25

DIAGNOSTIC_STATUS_EVALUATED = "AVALIACAO OK"


def normalize_prefu(prefu_raw: Any) -> str:
    """Normaliza flag Presente/Futuro (PanelDX: prefu_ques)."""
    prefu = str(prefu_raw or "").strip().upper()
    if prefu in ("P", "PRESENTE") or prefu.startswith("P"):
        return "P"
    if prefu in ("F", "FUTURO") or prefu.startswith("F"):
        return "F"
    return ""


def _safe_grad(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in ("na", "null", ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def calculate_scores(
    answers_list: list[dict[str, Any]],
) -> tuple[dict[str, float], dict[str, float], float]:
    """
    Agrega respostas (Presente OU Futuro) → médias por domínio, dimensão e score geral.
    Cópia de PanelDX calculate_scores (app.py / seed_dev_client.py).
    """
    respostas_por_dominio: dict[str, list[float]] = {}
    respostas_por_dimensao: dict[str, list[float]] = {}

    for answer in answers_list:
        grad_val = _safe_grad(answer.get("grad_ques"))
        if grad_val is None:
            continue

        id_doma = answer.get("id_doma")
        id_dime = answer.get("id_dime")
        if id_doma is not None:
            respostas_por_dominio.setdefault(str(id_doma), []).append(grad_val)
        if id_dime is not None:
            respostas_por_dimensao.setdefault(str(id_dime), []).append(grad_val)

    pdom_scores_dict = {
        d: round(sum(scores) / len(scores), 2)
        for d, scores in respostas_por_dominio.items()
        if scores
    }
    pdim_scores_dict = {
        d: round(sum(scores) / len(scores), 2)
        for d, scores in respostas_por_dimensao.items()
        if scores
    }

    pdom_avg = sum(pdom_scores_dict.values()) / len(pdom_scores_dict) if pdom_scores_dict else 0.0
    pdim_avg = sum(pdim_scores_dict.values()) / len(pdim_scores_dict) if pdim_scores_dict else 0.0
    pgen = (
        round((pdom_avg + pdim_avg) / 2, 2)
        if (pdom_avg + pdim_avg) > 0
        else 0.0
    )
    return pdom_scores_dict, pdim_scores_dict, pgen


def filter_education_answers(all_answers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Subset educacional — dimensão LA (id_dime=4) ou setor EDUCACAO (PanelDX)."""
    subset: list[dict[str, Any]] = []
    for ans in all_answers:
        try:
            dime = int(ans.get("id_dime", 0) or 0)
        except (TypeError, ValueError):
            dime = 0
        setor = str(ans.get("setor_ques", "")).strip().upper()
        if ans.get("is_sector") or dime == 4 or setor in ("EDUCACAO", "EDUCAÇÃO"):
            subset.append(ans)
    return subset


def compute_gap_dict(
    pres: dict[str, float],
    fut: dict[str, float],
) -> dict[str, float]:
    """Gap por chave = Futuro − Presente (PanelDX finalize)."""
    result: dict[str, float] = {}
    for key, score_fut in fut.items():
        score_pres = pres.get(key, 0.0)
        result[key] = round(score_fut - score_pres, 2)
    return result


def compute_matrix_domain_stats(
    answers_list: list[dict[str, Any]],
    *,
    alpha: float | None = None,
    beta: float | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Estatísticas por domínio para matriz híbrida (PanelDX compute_matrix_domain_stats).
    """
    alpha = MATRIX_CV_ALPHA if alpha is None else alpha
    beta = MATRIX_WEAKNESS_BETA if beta is None else beta

    by_dom_pres: dict[str, list[float]] = {}
    by_dom_fut: dict[str, list[float]] = {}
    by_dom_ques: dict[str, dict[str, dict[str, float]]] = {}

    for answer in answers_list:
        grad_val = _safe_grad(answer.get("grad_ques"))
        if grad_val is None:
            continue

        raw_doma = answer.get("id_doma")
        if raw_doma is None:
            continue
        id_doma = str(raw_doma)
        if not id_doma or id_doma == "None":
            continue

        prefu = normalize_prefu(answer.get("prefu_ques"))
        id_ques = str(answer.get("id_ques") or "")
        ques_bucket = by_dom_ques.setdefault(id_doma, {}).setdefault(id_ques, {})

        if prefu == "P":
            by_dom_pres.setdefault(id_doma, []).append(grad_val)
            ques_bucket["P"] = grad_val
        elif prefu == "F":
            by_dom_fut.setdefault(id_doma, []).append(grad_val)
            ques_bucket["F"] = grad_val

    all_domains = set(by_dom_pres.keys()) | set(by_dom_fut.keys())
    result: dict[str, dict[str, Any]] = {}

    for id_doma in all_domains:
        pres_vals = by_dom_pres.get(id_doma, [])
        fut_vals = by_dom_fut.get(id_doma, [])
        ques_map = by_dom_ques.get(id_doma, {})

        mean_pres = round(sum(pres_vals) / len(pres_vals), 2) if pres_vals else 0.0
        mean_fut = round(sum(fut_vals) / len(fut_vals), 2) if fut_vals else 0.0
        min_pres = round(min(pres_vals), 2) if pres_vals else 0.0
        max_pres = round(max(pres_vals), 2) if pres_vals else 0.0
        min_fut = round(min(fut_vals), 2) if fut_vals else 0.0
        max_fut = round(max(fut_vals), 2) if fut_vals else 0.0
        range_pres = round(max_pres - min_pres, 2) if pres_vals else 0.0
        std_pres = round(statistics.stdev(pres_vals), 3) if len(pres_vals) > 1 else 0.0
        cv_pres = round(std_pres / mean_pres, 3) if mean_pres > 0 else 0.0

        block_gaps: list[float] = []
        for ques_vals in ques_map.values():
            if "P" in ques_vals and "F" in ques_vals:
                block_gaps.append(ques_vals["F"] - ques_vals["P"])
        block_gap_std = round(statistics.stdev(block_gaps), 3) if len(block_gaps) > 1 else 0.0
        block_gap_range = round(max(block_gaps) - min(block_gaps), 2) if block_gaps else 0.0

        weakness_gap = max(0.0, mean_pres - min_pres)
        cv_penalty = alpha * cv_pres
        weakness_penalty = beta * weakness_gap
        adjusted_reality = round(
            max(0.0, min(5.0, mean_pres - cv_penalty - weakness_penalty)),
            2,
        )
        gap = round(max(0.0, mean_fut - mean_pres), 2)

        frag_components = [
            min(1.0, range_pres / 2.0),
            min(1.0, std_pres / 1.0),
            min(1.0, cv_pres / 0.30),
            min(1.0, gap / 1.5),
            min(1.0, block_gap_std / 1.0),
            min(1.0, block_gap_range / 2.0),
            min(1.0, weakness_gap / 1.5),
        ]
        fragmentation_index = round(max(frag_components), 3)

        result[id_doma] = {
            "mean_pres": mean_pres,
            "mean_fut": mean_fut,
            "min_pres": min_pres,
            "max_pres": max_pres,
            "min_fut": min_fut,
            "max_fut": max_fut,
            "range_pres": range_pres,
            "std_pres": std_pres,
            "cv_pres": cv_pres,
            "block_count_pres": len(pres_vals),
            "block_gap_std": block_gap_std,
            "block_gap_range": block_gap_range,
            "adjusted_reality": adjusted_reality,
            "gap": gap,
            "cv_penalty": round(cv_penalty, 3),
            "weakness_penalty": round(weakness_penalty, 3),
            "fragmentation_index": fragmentation_index,
        }

    return result


def build_matrix_meta(matrix_domain_stats: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Medianas dinâmicas dos domínios para divisão de quadrantes (PanelDX)."""
    ambitions = [
        stats["mean_fut"]
        for stats in matrix_domain_stats.values()
        if stats.get("mean_fut", 0) > 0
    ]
    realities = [
        stats["adjusted_reality"]
        for stats in matrix_domain_stats.values()
        if stats.get("adjusted_reality", 0) > 0
    ]

    return {
        "median_ambition": round(statistics.median(ambitions), 2) if ambitions else 2.5,
        "median_reality_adjusted": round(statistics.median(realities), 2) if realities else 2.5,
        "alpha_cv": MATRIX_CV_ALPHA,
        "beta_weakness": MATRIX_WEAKNESS_BETA,
        "model": "hybrid",
    }


def finalize_maturity_calculation(
    all_answers: list[dict[str, Any]],
    *,
    require_present_and_future: bool = True,
) -> dict[str, Any]:
    """
    Replica finalize=true de POST /api/ctdi_surv (PanelDX).
    Retorna os 18 scores + matriz híbrida por domínio.
    """
    pres = [a for a in all_answers if normalize_prefu(a.get("prefu_ques")) == "P"]
    fut = [a for a in all_answers if normalize_prefu(a.get("prefu_ques")) == "F"]

    if require_present_and_future and (not pres or not fut):
        raise ValueError(
            "Finalização exige respostas completas de Presente (P) e Futuro (F)."
        )

    pdom_pres, pdim_pres, pgen_pres = calculate_scores(pres)
    pdom_fut, pdim_fut, pgen_fut = calculate_scores(fut)
    pdom_gap = compute_gap_dict(pdom_pres, pdom_fut)
    pdim_gap = compute_gap_dict(pdim_pres, pdim_fut)
    pgen_gap = round(pgen_fut - pgen_pres, 2)

    sector_answers = filter_education_answers(all_answers)
    sect_pres = [a for a in sector_answers if normalize_prefu(a.get("prefu_ques")) == "P"]
    sect_fut = [a for a in sector_answers if normalize_prefu(a.get("prefu_ques")) == "F"]

    pdom_sect_pres, pdim_sect_pres, pgen_sect_pres = calculate_scores(sect_pres)
    pdom_sect_fut, pdim_sect_fut, pgen_sect_fut = calculate_scores(sect_fut)
    pdom_sect_gap = compute_gap_dict(pdom_sect_pres, pdom_sect_fut)
    pdim_sect_gap = compute_gap_dict(pdim_sect_pres, pdim_sect_fut)
    pgen_sect_gap = round(pgen_sect_fut - pgen_sect_pres, 2)

    matrix_domain_stats = compute_matrix_domain_stats(all_answers)
    matrix_meta = build_matrix_meta(matrix_domain_stats)

    return {
        "pdom_pres": pdom_pres,
        "pdim_pres": pdim_pres,
        "pgen_pres": pgen_pres,
        "pdom_fut": pdom_fut,
        "pdim_fut": pdim_fut,
        "pgen_fut": pgen_fut,
        "pdom_gap": pdom_gap,
        "pdim_gap": pdim_gap,
        "pgen_gap": pgen_gap,
        "pdom_sect_pres": pdom_sect_pres,
        "pdim_sect_pres": pdim_sect_pres,
        "pgen_sect_pres": pgen_sect_pres,
        "pdom_sect_fut": pdom_sect_fut,
        "pdim_sect_fut": pdim_sect_fut,
        "pgen_sect_fut": pgen_sect_fut,
        "pdom_sect_gap": pdom_sect_gap,
        "pdim_sect_gap": pdim_sect_gap,
        "pgen_sect_gap": pgen_sect_gap,
        "matrix_domain_stats": matrix_domain_stats,
        "matrix_meta": matrix_meta,
        "diagnostic_status": DIAGNOSTIC_STATUS_EVALUATED,
        "general": {
            "presente": {"pgen": pgen_pres, "pdom": pdom_pres, "pdim": pdim_pres},
            "futuro": {"pgen": pgen_fut, "pdom": pdom_fut, "pdim": pdim_fut},
            "gap": {"pgen": pgen_gap, "pdom": pdom_gap, "pdim": pdim_gap},
        },
        "sector": {
            "presente": {
                "pgen": pgen_sect_pres,
                "pdom": pdom_sect_pres,
                "pdim": pdim_sect_pres,
            },
            "futuro": {
                "pgen": pgen_sect_fut,
                "pdom": pdom_sect_fut,
                "pdim": pdim_sect_fut,
            },
            "gap": {
                "pgen": pgen_sect_gap,
                "pdom": pdom_sect_gap,
                "pdim": pdim_sect_gap,
            },
        },
    }
