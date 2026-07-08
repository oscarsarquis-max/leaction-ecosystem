"""Relatório de diagnóstico estilo PanelDX — gaps, sugestões de blocos, plano estruturado."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from app.core.sector_constants import (
    DEFAULT_SECTOR_ACRONYM,
    DEFAULT_SECTOR_ACTION_NAME,
    DEFAULT_SECTOR_FULL_LABEL,
    DOMAIN_NAMES_PT,
    LEGACY_DIME_ID_TO_KEY,
)
from app.database.models import (
    ActionPlan,
    AssessmentItem,
    AssessmentResponse,
    AssessmentSubmission,
    Framework,
    Tenant,
    User,
    db,
)
from app.infrastructure.ai_client import invoke_claude
from app.services.diagnostic_scoring_service import build_scoring_payload
from app.services.methodology_catalog_service import get_all_blocks_mapping

logger = logging.getLogger(__name__)

BASELINE_SNAPSHOT_KEYS = (
    "score_global",
    "nivel_maturidade",
    "score_geral_presente",
    "score_geral_futuro",
    "score_geral_gap",
    "scores_detalhe_presente",
    "scores_detalhe_futuro",
    "scores_detalhe_gap",
    "score_setorial",
    "scores_setorial_presente",
)


def build_baseline_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    """Congela o diagnóstico original para comparação ao longo do projeto."""
    from datetime import datetime, timezone

    snap = {key: report[key] for key in BASELINE_SNAPSHOT_KEYS if report.get(key) is not None}
    snap["captured_at"] = datetime.now(timezone.utc).isoformat()
    return snap


def attach_baseline_to_report(report: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any]:
    """Expõe baseline e deltas atuais no payload do relatório."""
    if not baseline:
        return report
    enriched = dict(report)
    enriched["baseline_snapshot"] = baseline
    enriched["evolution"] = {
        "score_geral_presente_delta": _delta(
            report.get("score_geral_presente"),
            baseline.get("score_geral_presente"),
        ),
        "score_geral_gap_delta": _delta(
            report.get("score_geral_gap"),
            baseline.get("score_geral_gap"),
        ),
        "score_global_delta": _delta(report.get("score_global"), baseline.get("score_global")),
    }
    return enriched


def _delta(current: Any, baseline: Any) -> float | None:
    try:
        if current is None or baseline is None:
            return None
        return round(float(current) - float(baseline), 2)
    except (TypeError, ValueError):
        return None


def _domain_display_name(id_doma: int | str, domain_key: str | None = None) -> str:
    if domain_key:
        return DOMAIN_NAMES_PT.get(domain_key, domain_key)
    labels = {
        1: "Estratégia Digital",
        2: "Modelos de Negócio",
        3: "Inovação",
        4: "Cultura de Dados",
        5: "Colaboração",
        6: "Governança",
        7: "Plataformas",
        8: "Capacidades",
        9: "Métricas",
    }
    try:
        return labels.get(int(id_doma), f"Domínio {id_doma}")
    except (TypeError, ValueError):
        return f"Domínio {id_doma}"


def build_block_suggestions(
    framework_id: str,
    pdom_gap: dict[str, float],
    pdim_gap: dict[str, float],
    *,
    use_sector: bool = False,
) -> list[dict[str, Any]]:
    """Sugestões determinísticas — domínios com gap > 0 → blocos das dimensões com dor."""
    blocks_data = get_all_blocks_mapping(framework_id)
    dimensoes_com_dor = {int(d) for d, g in pdim_gap.items() if float(g) > 0}

    suggestions: list[dict[str, Any]] = []
    for id_doma_str, gap_score_dom in pdom_gap.items():
        gap_val = float(gap_score_dom)
        if gap_val <= 0:
            continue
        try:
            id_doma = int(id_doma_str)
        except (TypeError, ValueError):
            continue

        blocos = [
            {
                "id_bloc": b.get("id_bloc"),
                "nome": b.get("name_bloc"),
                "desc": b.get("desc_bloc"),
                "id_dime": int(b["id_dime"]) if b.get("id_dime") is not None else None,
                "id_doma": id_doma,
                "deliverables": b.get("deliverables") or [],
            }
            for b in blocks_data
            if int(b.get("id_doma") or 0) == id_doma
            and (
                b.get("id_dime") is None
                or int(b.get("id_dime")) in dimensoes_com_dor
                or not dimensoes_com_dor
            )
        ]
        if not blocos:
            continue

        domain_key = next(
            (b.get("domain_key") for b in blocks_data if int(b.get("id_doma") or 0) == id_doma),
            None,
        )
        suggestions.append(
            {
                "id_doma": id_doma,
                "domain_key": domain_key,
                "dominio_nome": _domain_display_name(id_doma, domain_key),
                "gap_dom": round(gap_val, 2),
                "score_prioridade": gap_val,
                "scope": "sector" if use_sector else "general",
                "blocos_sugeridos": blocos,
            }
        )

    suggestions.sort(key=lambda x: x["score_prioridade"], reverse=True)
    return suggestions


def _sector_dimension_display(framework: Framework | None) -> str:
    """Rótulo da dimensão operacional (LA, TA, CO, …) para a tabela comparativa."""
    if not framework:
        return DEFAULT_SECTOR_FULL_LABEL
    rules = framework.rules_metadata or {}
    name = rules.get("operational_dimension_name")
    acronym = rules.get("operational_dimension_acronym") or DEFAULT_SECTOR_ACRONYM
    op = rules.get("operational_dimension") or {}
    if not name:
        name = op.get("full_label") or op.get("name") or DEFAULT_SECTOR_ACTION_NAME
    if acronym and f"({acronym})" not in str(name):
        return f"{name} ({acronym})"
    return str(name)


def _paneldx_comparative_slices(scoring: dict[str, Any]) -> dict[str, Any]:
    """Fatias Presente/Futuro/Gap no formato PanelDX (scores_detalhe_*)."""
    general = scoring.get("general") or {}
    presente = general.get("presente") or {}
    futuro = general.get("futuro") or {}
    gap = general.get("gap") or {}

    sector = scoring.get("sector") or {}
    sect_pres = sector.get("presente") or {}
    sect_fut = sector.get("futuro") or {}
    sect_gap = sector.get("gap") or {}

    pdim_pres = dict(presente.get("pdim") or {})
    pdim_fut = dict(futuro.get("pdim") or {})
    pdim_gap = dict(gap.get("pdim") or {})
    for src_pres, src_fut, src_gap, key in (
        (sect_pres, sect_fut, sect_gap, "pdim"),
    ):
        for dim_id, val in (src_pres.get(key) or {}).items():
            if dim_id not in pdim_pres:
                pdim_pres[dim_id] = val
        for dim_id, val in (src_fut.get(key) or {}).items():
            if dim_id not in pdim_fut:
                pdim_fut[dim_id] = val
        for dim_id, val in (src_gap.get(key) or {}).items():
            if dim_id not in pdim_gap:
                pdim_gap[dim_id] = val

    return {
        "scores_detalhe_presente": {
            "pdom_scores": presente.get("pdom") or {},
            "pdim_scores": pdim_pres,
            "pgen_score": presente.get("pgen"),
        },
        "scores_detalhe_futuro": {
            "pdom_scores": futuro.get("pdom") or {},
            "pdim_scores": pdim_fut,
            "pgen_score": futuro.get("pgen"),
        },
        "scores_detalhe_gap": {
            "pdom_scores": gap.get("pdom") or {},
            "pdim_scores": pdim_gap,
            "pgen_gap": gap.get("pgen"),
        },
    }


def enrich_paneldx_comparative_scores(
    report: dict[str, Any],
    *,
    framework: Framework | None = None,
) -> dict[str, Any]:
    """Preenche scores_detalhe_* e rótulo setorial em relatórios antigos."""
    if not report.get("scores_detalhe_presente") or not report.get("scores_detalhe_futuro"):
        scoring = report.get("scores_detalhe")
        if scoring:
            report.update(_paneldx_comparative_slices(scoring))
    if not report.get("sector_dimension_label"):
        report["sector_dimension_label"] = _sector_dimension_display(framework)
    if not report.get("scores_setorial_presente"):
        sector = (report.get("scores_detalhe") or {}).get("sector") or {}
        presente = sector.get("presente") or {}
        if presente:
            report["scores_setorial_presente"] = {
                "pdom_scores": presente.get("pdom") or {},
                "pdim_scores": presente.get("pdim") or {},
            }
    return report


def _movement_for_gap(gap: float) -> dict[str, str]:
    if gap <= 0.5:
        return {
            "nome": "Otimização Contínua",
            "estagio_descricao": "Gap reduzido — foco em refinamento e escala.",
            "implicacoes_diagnostico": "Priorizar blocos de consolidação e métricas.",
        }
    if gap <= 1.5:
        return {
            "nome": "Transformação Incremental",
            "estagio_descricao": "Gap moderado — evolução estruturada necessária.",
            "implicacoes_diagnostico": "Atacar domínios com maior gap e blocos associados.",
        }
    return {
        "nome": "Transformação Profunda",
        "estagio_descricao": "Gap elevado — mudança estrutural necessária.",
        "implicacoes_diagnostico": "Foco nos pilares de maior gap e quick wins paralelos.",
    }


def _generate_structured_action_plan(
    framework_id: str,
    sector: str,
    maturity_name: str,
    scoring: dict[str, Any],
    suggestions: list[dict[str, Any]],
    responses_summary: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Plano de ação ancorado em blocos — Markdown + JSON estruturado."""
    catalog_snippet = []
    for sug in suggestions[:8]:
        for bloc in sug.get("blocos_sugeridos", [])[:3]:
            catalog_snippet.append(
                {
                    "id_bloc": bloc.get("id_bloc"),
                    "nome": bloc.get("nome"),
                    "id_doma": sug.get("id_doma"),
                    "dominio": sug.get("dominio_nome"),
                    "gap_dom": sug.get("gap_dom"),
                    "deliverables": [
                        d.get("name_derv") for d in (bloc.get("deliverables") or [])[:2]
                    ],
                }
            )

    prompt = f"""Você é consultor PanelDX/Chamelleon especialista em Transformação Digital no setor {sector}.

Framework: {framework_id}
Nível de maturidade: {maturity_name}

Scores gerais (Presente/Futuro/Gap):
{json.dumps(scoring.get('general', {}), ensure_ascii=False, indent=2)}

Scores setoriais:
{json.dumps(scoring.get('sector', {}), ensure_ascii=False, indent=2)}

Blocos metodológicos sugeridos (USE ESTES id_bloc/nome — não invente ações genéricas):
{json.dumps(catalog_snippet, ensure_ascii=False, indent=2)}

Resumo das respostas (domínio, temporalidade, nota):
{json.dumps(responses_summary[:30], ensure_ascii=False)}

Gere um JSON com:
{{
  "relatorio_inteligencia": {{
    "sintese_executiva": "...",
    "analise_dominios": "...",
    "proximos_passos_90_dias": "..."
  }},
  "roadmap_estrategico": [
    {{"id_bloco": <id do catálogo ou null>, "nome_sprint": "<nome do bloco>", "justificativa": "...", "dominio": "..."}}
  ],
  "plano_tatico": [
    {{"id_bloco": ..., "nome_sprint": "...", "como_resolve": "...", "entregavel_alvo": "..."}}
  ],
  "markdown_executivo": "# Diagnóstico Executivo\\n..."
}}

Máximo 5 itens no roadmap e 3 no plano tático. Ancore cada ação a um bloco do catálogo."""

    raw = invoke_claude(prompt, max_tokens=4000)
    structured: dict[str, Any] = {}
    markdown = raw

    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            structured = json.loads(raw[start : end + 1])
            markdown = structured.pop("markdown_executivo", None) or _structured_to_markdown(structured)
    except json.JSONDecodeError:
        logger.warning("IA não retornou JSON válido — usando Markdown bruto.")

    if not structured:
        structured = {
            "relatorio_inteligencia": {"sintese_executiva": raw[:500]},
            "roadmap_estrategico": [
                {
                    "id_bloco": b.get("id_bloc"),
                    "nome_sprint": b.get("nome"),
                    "justificativa": f"Gap no domínio {b.get('dominio')}",
                }
                for b in catalog_snippet[:5]
            ],
        }

    return markdown, structured


def _structured_to_markdown(structured: dict[str, Any]) -> str:
    lines = ["# Diagnóstico Executivo\n"]
    ri = structured.get("relatorio_inteligencia") or {}
    if ri.get("sintese_executiva"):
        lines.append(ri["sintese_executiva"])
        lines.append("")
    if ri.get("proximos_passos_90_dias"):
        lines.append("## Próximos 90 dias\n")
        lines.append(ri["proximos_passos_90_dias"])
        lines.append("")
    roadmap = structured.get("roadmap_estrategico") or []
    if roadmap:
        lines.append("## Roadmap estratégico (blocos metodológicos)\n")
        for i, item in enumerate(roadmap, 1):
            nome = item.get("nome_sprint") or item.get("nome") or "Ação"
            lines.append(f"{i}. **{nome}** — {item.get('justificativa', '')}")
        lines.append("")
    return "\n".join(lines)


def build_diagnostic_report(
    submission: AssessmentSubmission,
    *,
    generate_ai_plan: bool = True,
) -> dict[str, Any]:
    """Monta relatório completo para uma submissão concluída."""
    framework = db.session.get(Framework, submission.framework_id)
    tenant = db.session.get(Tenant, submission.tenant_id)
    user = db.session.get(User, submission.user_id)

    responses = AssessmentResponse.query.filter_by(submission_id=submission.id).all()
    item_ids = [r.assessment_item_id for r in responses]
    items = AssessmentItem.query.filter(AssessmentItem.id.in_(item_ids)).all() if item_ids else []
    items_by_id = {i.id: i for i in items}
    catalog_items = AssessmentItem.query.filter_by(framework_id=submission.framework_id).all()

    scoring = build_scoring_payload(
        responses, items_by_id, catalog_items=catalog_items
    )
    general_gap = scoring.get("general", {}).get("gap", {})
    sector_gap = scoring.get("sector", {}).get("gap", {})

    suggestions_general = build_block_suggestions(
        submission.framework_id,
        general_gap.get("pdom", {}),
        general_gap.get("pdim", {}),
        use_sector=False,
    )
    suggestions_sector = build_block_suggestions(
        submission.framework_id,
        sector_gap.get("pdom", {}),
        sector_gap.get("pdim", {}),
        use_sector=True,
    )

    pgen_gap = float(general_gap.get("pgen", 0))
    movement = _movement_for_gap(pgen_gap)

    responses_summary = []
    for resp in responses:
        item = items_by_id.get(resp.assessment_item_id)
        if not item:
            continue
        meta = item.item_metadata or {}
        responses_summary.append(
            {
                "axis": item.axis,
                "domain_key": meta.get("domain_key"),
                "prefu": meta.get("prefu_ques"),
                "nota": resp.selected_value,
            }
        )

    rules = (framework.rules_metadata or {}) if framework else {}
    sector_name = rules.get("sector") or framework.industry if framework else ""

    comparative = _paneldx_comparative_slices(scoring)
    sector_presente = scoring.get("sector", {}).get("presente") or {}

    report: dict[str, Any] = {
        "submission_id": str(submission.id),
        "framework_id": submission.framework_id,
        "sector": sector_name,
        "cliente": tenant.name if tenant else "",
        "respondente": user.name if user else "",
        "score_global": scoring.get("score_global"),
        "nivel_maturidade": submission.maturity_level_name,
        "score_geral_presente": scoring.get("general", {}).get("presente", {}).get("pgen"),
        "score_geral_futuro": scoring.get("general", {}).get("futuro", {}).get("pgen"),
        "score_geral_gap": pgen_gap,
        "score_setorial": {
            "presente": scoring.get("sector", {}).get("presente", {}).get("pgen"),
            "futuro": scoring.get("sector", {}).get("futuro", {}).get("pgen"),
            "gap": sector_gap.get("pgen"),
        },
        "scores_detalhe": scoring,
        **comparative,
        "scores_setorial_presente": {
            "pdom_scores": sector_presente.get("pdom") or {},
            "pdim_scores": sector_presente.get("pdim") or {},
        },
        "matrix_domain_stats": scoring.get("maturity_scores", {}).get("matrix_domain_stats", {}),
        "matrix_meta": scoring.get("maturity_scores", {}).get("matrix_meta", {}),
        "maturity_scores": scoring.get("maturity_scores"),
        "diagnostic_status": submission.diagnostic_status,
        "movimento_principal": movement,
        "suggestions": suggestions_general,
        "suggestions_sector": suggestions_sector,
        "top_actions": _top_action_cards(suggestions_general + suggestions_sector),
        "dimension_labels": scoring.get("dimension_labels", {}),
        "domain_labels": scoring.get("domain_labels", {}),
        "sector_dimension_label": _sector_dimension_display(framework),
    }

    if generate_ai_plan:
        md, structured = _generate_structured_action_plan(
            submission.framework_id,
            sector_name,
            submission.maturity_level_name or "",
            scoring,
            suggestions_general + suggestions_sector,
            responses_summary,
        )
        report["action_plan_md"] = md
        report["structured_plan"] = structured

    return report


def _top_action_cards(suggestions: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sug in suggestions:
        for bloc in sug.get("blocos_sugeridos", []):
            key = str(bloc.get("id_bloc") or bloc.get("nome"))
            if key in seen:
                continue
            seen.add(key)
            derv = (bloc.get("deliverables") or [{}])[0]
            cards.append(
                {
                    "id_bloc": bloc.get("id_bloc"),
                    "nome_bloc": bloc.get("nome"),
                    "desc_bloc": bloc.get("desc"),
                    "dominio": sug.get("dominio_nome"),
                    "gap_dom": sug.get("gap_dom"),
                    "entregavel": derv.get("name_derv") if isinstance(derv, dict) else None,
                    "metricas": derv.get("derv_metr") if isinstance(derv, dict) else None,
                }
            )
            if len(cards) >= limit:
                return cards
    return cards


def persist_diagnostic_report(
    submission: AssessmentSubmission,
    report: dict[str, Any],
) -> ActionPlan | None:
    """Grava report_data na submissão e plano de ação estruturado."""
    existing = dict(submission.report_data or {})
    baseline = existing.get("baseline_snapshot") or build_baseline_snapshot(report)

    from datetime import datetime, timezone

    submission.report_data = {
        k: v
        for k, v in report.items()
        if k not in ("action_plan_md", "structured_plan")
    }
    submission.report_data["baseline_snapshot"] = baseline
    submission.report_data["last_updated_at"] = datetime.now(timezone.utc).isoformat()
    submission.scores_por_eixo = report.get("scores_detalhe", {}).get("scores_por_eixo", submission.scores_por_eixo)
    submission.score_global = report.get("score_global", submission.score_global)

    plan = None
    md = report.get("action_plan_md")
    if md:
        plan = ActionPlan(
            tenant_id=submission.tenant_id,
            framework_id=submission.framework_id,
            ai_generated_md=md,
            structured_plan=report.get("structured_plan"),
        )
        db.session.add(plan)
        db.session.flush()
        submission.action_plan_id = plan.id

    return plan
