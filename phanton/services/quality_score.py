"""Nota objetiva de qualidade do artefato (sem LLM-juiz)."""

from __future__ import annotations

from typing import Any, Optional

# Tipos que nunca auto-aprovam nesta v1 (gate humano obrigatório).
ALWAYS_HUMAN: frozenset[str] = frozenset({"security_guidelines"})

AUTO_APPROVE_THRESHOLD = 80

# Abaixo disso a fase é refeita com regras de aprendizado (antes do gate humano).
QUALITY_REDO_THRESHOLD = 95
MAX_QUALITY_REDOS = 1  # 1 reexecução com aprendizado (máx. 2 tentativas) — controla latência

# Penalidades da fórmula inicial (ajustáveis).
PENALTY_FALLBACK = 50
PENALTY_RETRY = 10  # por tentativa além da primeira (cada item em attempts)
PENALTY_MAX_TOKENS = 15
PENALTY_MISSING_FIELD = 20


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def unwrap_artifact_payload(artifact: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Retorna (meta, conteúdo interno) a partir do envelope do handler."""
    outer = _as_dict(artifact)
    meta = _as_dict(outer.get("meta"))
    inner = outer.get("artifact_data")
    if isinstance(inner, dict):
        return meta, inner
    return meta, outer


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _attempt_failures(meta: dict[str, Any]) -> int:
    """Quantas tentativas falharam antes do sucesso (lista `attempts` ou int)."""
    raw = meta.get("attempts")
    if raw is None:
        return 0
    if isinstance(raw, list):
        return len(raw)
    if isinstance(raw, int):
        # Se for contagem total de tentativas, falhas = max(0, n-1)
        return max(0, raw - 1) if raw > 0 else 0
    try:
        n = int(raw)
        return max(0, n - 1) if n > 0 else 0
    except (TypeError, ValueError):
        return 0


def _finish_reason_max_tokens(meta: dict[str, Any]) -> bool:
    reason = str(meta.get("finish_reason") or "")
    return "MAX_TOKENS" in reason.upper()


def _missing_required_fields(
    phase_type: str,
    content: dict[str, Any],
    *,
    expected_modules: Optional[list[str]] = None,
) -> list[str]:
    """Campos obrigatórios ausentes/vazios por tipo de fase."""
    missing: list[str] = []
    ptype = (phase_type or "").strip().lower()

    def need(key: str, value: Any = None) -> None:
        val = content.get(key) if value is None else value
        if not _is_present(val):
            missing.append(key)

    if ptype == "generate_sdd":
        need("sdd_markdown")
        need("build_order")
        # architecture_mermaid é desejável; se ausente o frontend deriva do build_order
    elif ptype == "generate_prd":
        need("prd_markdown")
    elif ptype == "task_breakdown":
        need("epics")
        epics = content.get("epics")
        if isinstance(epics, list) and epics:
            first = epics[0] if isinstance(epics[0], dict) else {}
            issues = first.get("issues") if isinstance(first, dict) else None
            if not _is_present(issues):
                missing.append("epics[0].issues")
            elif isinstance(issues, list) and issues and isinstance(issues[0], dict):
                if not _is_present(issues[0].get("description_micro_prompt")):
                    missing.append("epics[0].issues[0].description_micro_prompt")
    elif ptype == "security_guidelines":
        need("standards_aplicados")
        need("diretrizes_gerais")
        need("diretrizes_por_modulo")
        by_mod = content.get("diretrizes_por_modulo")
        if isinstance(by_mod, dict) and expected_modules:
            for mod in expected_modules:
                guidelines = by_mod.get(mod)
                if not _is_present(guidelines):
                    missing.append(f"diretrizes_por_modulo.{mod}")
    elif ptype == "context7_search":
        need("search_keywords")
        need("context7_hits")
        keywords = content.get("search_keywords") or []
        hits = content.get("context7_hits") or []
        if _is_present(keywords) and _is_present(hits):
            # Coerência leve: hits devem existir quando há keywords
            blob = " ".join(
                str(h.get("title") or "") + " " + str(h.get("snippet") or h.get("text") or "")
                for h in hits
                if isinstance(h, dict)
            ).lower()
            kw_list = [str(k).lower() for k in keywords if str(k).strip()]
            if kw_list and blob and not any(k in blob for k in kw_list):
                # Sem overlap textual — ainda conta como hit presente; só marca
                # incoerência se nenhum hit tiver score/source útil
                if not any(
                    isinstance(h, dict) and (h.get("score") is not None or h.get("source") or h.get("path"))
                    for h in hits
                ):
                    missing.append("context7_hits.coerencia")
    elif ptype == "prompt_cursor":
        modules = content.get("module_prompts")
        cursor = content.get("cursor_prompt")
        if not _is_present(modules) and not _is_present(cursor):
            missing.append("module_prompts|cursor_prompt")
    elif ptype == "methodology":
        if not any(_is_present(content.get(k)) for k in ("metodologia", "objetivo", "principios")):
            missing.append("metodologia|objetivo|principios")
    elif ptype == "research":
        need("achados")
    elif ptype == "synthesize":
        if not any(
            _is_present(content.get(k))
            for k in ("resumo_sintese", "pontos_chave", "requisitos_para_implementacao")
        ):
            missing.append("resumo_sintese|pontos_chave")
    elif ptype == "prompt":
        if not any(_is_present(content.get(k)) for k in ("html", "conteudo", "delivery", "markdown")):
            # L4 pode usar outras chaves — exige artefato não-vazio
            if not content:
                missing.append("artifact_data")

    return missing


def compute_quality_score(
    phase_type: str,
    meta: Any,
    artifact_data: Any,
    *,
    expected_modules: Optional[list[str]] = None,
) -> int:
    """Compõe nota 0–100 a partir de meta objetiva + completude estrutural."""
    meta_d = _as_dict(meta)
    # artifact_data pode ser o envelope completo ou só o miolo
    if isinstance(artifact_data, dict) and (
        "meta" in artifact_data or "artifact_data" in artifact_data
    ):
        meta_from_env, content = unwrap_artifact_payload(artifact_data)
        if not meta_d:
            meta_d = meta_from_env
    else:
        content = _as_dict(artifact_data)

    score = 100

    if meta_d.get("fallback") is True:
        score -= PENALTY_FALLBACK

    failures = _attempt_failures(meta_d)
    if failures > 0:
        score -= PENALTY_RETRY * failures

    if _finish_reason_max_tokens(meta_d):
        score -= PENALTY_MAX_TOKENS

    missing = _missing_required_fields(
        phase_type, content, expected_modules=expected_modules
    )
    score -= PENALTY_MISSING_FIELD * len(missing)

    return max(0, min(100, score))


def should_auto_approve(
    *,
    auto_approve: bool,
    phase_type: str,
    quality_score: int,
    threshold: int = AUTO_APPROVE_THRESHOLD,
) -> bool:
    if not auto_approve:
        return False
    ptype = (phase_type or "").strip().lower()
    if ptype in ALWAYS_HUMAN:
        return False
    return int(quality_score) >= int(threshold)


def should_redo_for_quality(
    quality_score: int,
    *,
    redos_done: int,
    threshold: int = QUALITY_REDO_THRESHOLD,
    max_redos: int = MAX_QUALITY_REDOS,
    artifact: Any = None,
) -> bool:
    """True se a fase deve ser re-executada com aprendizado.

    Não refaz quando o handler já esgotou retries internos (fallback=True):
    a 2ª volta LLM quase nunca recupera e dobra a latência (ex.: SDD ~2–3 min).
    """
    if int(redos_done) >= int(max_redos):
        return False
    if int(quality_score) >= int(threshold):
        return False
    meta, _ = unwrap_artifact_payload(artifact) if artifact is not None else ({}, {})
    if meta.get("fallback") is True:
        return False
    return True


def build_quality_learning(
    phase_type: str,
    quality_score: int,
    artifact: Any,
    *,
    attempt: int,
    expected_modules: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Regras de aprendizado a partir da avaliação objetiva.

    Usado na reexecução: o modelo recebe lições concretas (campos faltantes,
    fallback, truncamento) para corrigir a próxima tentativa.
    """
    meta, content = unwrap_artifact_payload(artifact)
    if not meta and isinstance(artifact, dict):
        meta = _as_dict(artifact.get("meta"))
    missing = _missing_required_fields(
        phase_type, content, expected_modules=expected_modules
    )
    lessons: list[str] = []

    if meta.get("fallback") is True:
        lessons.append(
            "A tentativa anterior caiu em FALLBACK — produza o artefato completo "
            "nos campos obrigatórios; não devolva template genérico."
        )
    if _finish_reason_max_tokens(meta):
        lessons.append(
            "A saída foi truncada (MAX_TOKENS) — seja mais conciso, priorize "
            "seções/campos obrigatórios e evite repetir o pedido do usuário."
        )
    failures = _attempt_failures(meta)
    if failures > 0:
        lessons.append(
            "Houve falhas de parsing/validação antes do sucesso — responda só "
            "JSON válido no schema pedido, sem preâmbulo nem markdown fora dos campos."
        )
    for field in missing:
        lessons.append(
            f"Campo obrigatório ausente ou vazio: `{field}` — preencha com conteúdo real."
        )

    ptype = (phase_type or "").strip().lower()
    if ptype == "generate_sdd" and not _is_present(content.get("architecture_mermaid")):
        lessons.append(
            "Inclua `architecture_mermaid` (flowchart Mermaid da arquitetura) "
            "além do sdd_markdown e build_order."
        )
    if ptype == "task_breakdown":
        lessons.append(
            "Garanta Epics com Issues e description_micro_prompt em PT-BR em cada issue."
        )
    if ptype == "prompt_cursor":
        lessons.append(
            "Entregue module_prompts substantivos (ou cursor_prompt rico); "
            "evite um único parágrafo genérico."
        )

    if not lessons:
        lessons.append(
            "A nota ficou abaixo do limiar — melhore completude, precisão e "
            "aderência ao schema da fase sem inventar dados contraditórios."
        )

    return {
        "attempt": int(attempt),
        "previous_score": int(quality_score),
        "threshold": QUALITY_REDO_THRESHOLD,
        "phase_type": ptype,
        "missing_fields": missing,
        "fallback": bool(meta.get("fallback") is True),
        "max_tokens": _finish_reason_max_tokens(meta),
        "lessons": lessons,
    }


def format_quality_learning_block(learning: Any) -> str:
    """Texto injetado no prompt da reexecução."""
    if not isinstance(learning, dict) or not learning:
        return ""
    lessons = learning.get("lessons") or []
    if not isinstance(lessons, list) or not lessons:
        return ""
    score = learning.get("previous_score")
    attempt = learning.get("attempt")
    threshold = learning.get("threshold", QUALITY_REDO_THRESHOLD)
    lines = [
        "=== APRENDIZADO DA AVALIAÇÃO DE QUALIDADE (OBRIGATÓRIO CORRIGIR) ===",
        f"Tentativa anterior #{attempt}: nota {score}/100 "
        f"(limiar para aceitar sem refazer: {threshold}).",
        "Regras a aplicar nesta reexecução:",
    ]
    for i, lesson in enumerate(lessons, start=1):
        text = str(lesson or "").strip()
        if text:
            lines.append(f"{i}. {text}")
    lines.append(
        "Não repita os mesmos defeitos. Se um campo era vazio/fallback, "
        "agora entregue conteúdo completo e verificável."
    )
    lines.append("=== FIM DO APRENDIZADO ===")
    return "\n".join(lines)


def attach_quality_score(artifact: Any, score: int) -> dict[str, Any]:
    """Anexa quality_score ao envelope do artefato (top-level + meta)."""
    data = dict(artifact) if isinstance(artifact, dict) else {"artifact_data": artifact}
    data["quality_score"] = int(score)
    meta = dict(data["meta"]) if isinstance(data.get("meta"), dict) else {}
    meta["quality_score"] = int(score)
    data["meta"] = meta
    return data
