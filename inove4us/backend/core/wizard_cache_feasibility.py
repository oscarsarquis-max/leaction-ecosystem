"""Diagnóstico de viabilidade de Prompt Caching (Bedrock) — NÃO altera produção.

Analisa a ordem real do system prompt do wizard e compara o prefixo estático
com os requisitos do model ID efetivo. Nenhum `cache_control` é aplicado aqui.
"""

from __future__ import annotations

from typing import Any

# Requisitos oficiais (model card AWS Bedrock — Claude Sonnet 4, 20250514):
# https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-4.html
CACHE_SPECS_BY_MODEL_PREFIX: dict[str, dict[str, Any]] = {
    # Claude Sonnet 4 (base e inference profile us./eu./apac./global.)
    "anthropic.claude-sonnet-4-20250514": {
        "cache_supported": True,
        "min_checkpoint_tokens": 1024,
        "max_checkpoints": 4,
        "ttl": "5 minutes",
        "ttl_options": ["5 minutes"],
        "checkpoint_fields": ["system", "messages", "tools"],
        "invoke_model_supported": True,
        "source": "AWS model card Claude Sonnet 4",
    },
}

# Fallback conservador para IDs da família Sonnet 4.x (se não casar o prefixo acima).
CACHE_SPEC_SONNET4_FAMILY_DEFAULT = {
    "cache_supported": True,
    "min_checkpoint_tokens": 1024,
    "max_checkpoints": 4,
    "ttl": "5 minutes",
    "ttl_options": ["5 minutes"],
    "checkpoint_fields": ["system", "messages", "tools"],
    "invoke_model_supported": True,
    "source": "AWS samples / family Sonnet 4 (confirmar model card)",
}

# Campos usage InvokeModel (Anthropic) — instrumentação atual do wizard.
INVOKE_MODEL_CACHE_USAGE_KEYS = (
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)
# Nomes Converse (não usados na produção atual; só referência).
CONVERSE_CACHE_USAGE_KEYS = (
    "cacheWriteInputTokens",
    "cacheReadInputTokens",
)


def resolve_cache_spec(model_id: str) -> dict[str, Any]:
    mid = (model_id or "").strip()
    # Remove prefixo de inference profile (us. / eu. / apac. / global.)
    bare = mid
    for pfx in ("us.", "eu.", "apac.", "global."):
        if bare.startswith(pfx):
            bare = bare[len(pfx) :]
            break
    for key, spec in CACHE_SPECS_BY_MODEL_PREFIX.items():
        if bare.startswith(key) or mid.startswith(key):
            out = dict(spec)
            out["model_id_resolved"] = mid
            out["model_id_bare"] = bare
            return out
    if "claude-sonnet-4" in bare or "claude-sonnet-4" in mid:
        out = dict(CACHE_SPEC_SONNET4_FAMILY_DEFAULT)
        out["model_id_resolved"] = mid
        out["model_id_bare"] = bare
        out["cache_supported_confidence"] = "family_match"
        return out
    return {
        "cache_supported": False,
        "min_checkpoint_tokens": None,
        "max_checkpoints": None,
        "ttl": None,
        "ttl_options": [],
        "checkpoint_fields": [],
        "invoke_model_supported": False,
        "source": "unknown model — not in local table",
        "model_id_resolved": mid,
        "model_id_bare": bare,
    }


def split_system_prompt_blocks(system_prompt: str) -> dict[str, str]:
    """Parte o system REAL pelos marcadores atuais (sem reordenar)."""
    text = system_prompt or ""
    i_fw = text.find("<framework_obrigatorio>")
    i_fw_end = text.find("</framework_obrigatorio>")
    i_anc = text.find("<ancoras_de_estilo>")
    i_reg = text.find("<regras>")
    i_fmt = text.find("<formato>")

    if i_fw < 0:
        return {
            "intro": text,
            "framework_section": "",
            "mid_diretrizes_obrigatoria": "",
            "ancoras_section": "",
            "regras_section": "",
            "formato_section": "",
        }

    intro = text[:i_fw]
    fw_close = i_fw_end + len("</framework_obrigatorio>") if i_fw_end >= 0 else len(text)
    framework_section = text[i_fw:fw_close]

    mid_end = i_anc if i_anc >= 0 else (i_reg if i_reg >= 0 else len(text))
    mid_diretrizes_obrigatoria = text[fw_close:mid_end]

    if i_anc >= 0:
        anc_end = i_reg if i_reg >= 0 else len(text)
        ancoras_section = text[i_anc:anc_end]
    else:
        ancoras_section = ""

    if i_reg >= 0:
        reg_end = i_fmt if i_fmt >= 0 else len(text)
        regras_section = text[i_reg:reg_end]
    else:
        regras_section = ""

    formato_section = text[i_fmt:] if i_fmt >= 0 else ""

    return {
        "intro": intro,
        "framework_section": framework_section,
        "mid_diretrizes_obrigatoria": mid_diretrizes_obrigatoria,
        "ancoras_section": ancoras_section,
        "regras_section": regras_section,
        "formato_section": formato_section,
    }


def analyze_cache_feasibility(
    *,
    model_id: str,
    system_prompt: str,
    user_content: str = "",
    candidate_catalog_chars: int | None = None,
    measured_input_tokens: int | None = None,
) -> dict[str, Any]:
    """Análise determinística offline (chars + spec). Tokens reais só se fornecidos."""
    spec = resolve_cache_spec(model_id)
    blocks = split_system_prompt_blocks(system_prompt)
    intro_c = len(blocks["intro"])
    fw_c = len(blocks["framework_section"])
    mid_c = len(blocks["mid_diretrizes_obrigatoria"])
    anc_c = len(blocks["ancoras_section"])
    reg_c = len(blocks["regras_section"])
    fmt_c = len(blocks["formato_section"])
    system_total = len(system_prompt or "")
    user_c = len(user_content or "")

    # Prefixo estático REAL = só o intro (antes do Top 8 / framework).
    static_prefix_chars = intro_c
    # Conteúdo fixo global que HOJE vem DEPOIS do Top 8 (não é prefixo).
    static_suffix_chars = reg_c + fmt_c
    # Se reorganizasse (NÃO feito): intro + regras + formato como prefixo.
    static_if_reorganized_chars = intro_c + reg_c + fmt_c
    dynamic_system_chars = fw_c + mid_c + anc_c

    min_tok = spec.get("min_checkpoint_tokens")
    # Derivação a partir de usage real conhecido (opcional), marcada como derivada.
    derived_system_tokens = None
    derived_static_prefix_tokens = None
    derived_static_reorg_tokens = None
    derived_note = None
    if (
        measured_input_tokens is not None
        and system_total > 0
        and measured_input_tokens > 0
    ):
        # Atribuição proporcional chars→tokens do usage total (não é tokenizer).
        total_chars = system_total + user_c + 1  # + prefill "{"
        if total_chars > 0:
            derived_system_tokens = round(
                measured_input_tokens * (system_total / total_chars)
            )
            derived_static_prefix_tokens = round(
                measured_input_tokens * (static_prefix_chars / total_chars)
            )
            derived_static_reorg_tokens = round(
                measured_input_tokens * (static_if_reorganized_chars / total_chars)
            )
            derived_note = (
                "tokens_derivados = input_tokens_medidos * (chars_bloco / chars_total); "
                "não é CountTokens nativo"
            )

    def _meets(tokens_or_none: int | None, chars: int) -> str:
        if min_tok is None:
            return "indeterminado"
        if tokens_or_none is not None:
            return "SIM" if tokens_or_none >= int(min_tok) else "NÃO"
        # Sem tokens: só chars — insuficiente para afirmar SIM.
        # Heurística fraca: se chars << 4*min, claramente NÃO; senão indeterminado.
        if chars < int(min_tok):  # nem 1 char/token
            return "NÃO"
        if chars < int(min_tok) * 3:
            return "NÃO (chars << mínimo típico ~3–4 chars/token)"
        return "indeterminado (sem tokens nativos)"

    checkpoint_before_candidates = _meets(
        derived_static_prefix_tokens, static_prefix_chars
    )
    # Após candidatos: prefixo incluiria Top 8 → instável entre desafios.
    checkpoint_after_candidates_stable = False
    meets_reorg = _meets(derived_static_reorg_tokens, static_if_reorganized_chars)
    meets_full_system = _meets(derived_system_tokens, system_total)

    # Classificação
    if not spec.get("cache_supported"):
        classification = "D"
        recommendation = (
            "Modelo atual sem suporte documentado a Prompt Caching. "
            "Não implementar cache_control."
        )
    elif checkpoint_before_candidates.startswith("SIM"):
        classification = "A"
        recommendation = (
            "Prefixo estático atual atinge o mínimo. "
            "Checkpoint no fim do intro (antes do Top 8)."
        )
    elif meets_reorg.startswith("SIM") and not checkpoint_before_candidates.startswith(
        "SIM"
    ):
        classification = "B"
        recommendation = (
            "Mover <regras>+<formato> para ANTES de METODOLOGIAS DISPONÍVEIS / "
            "diretrizes / obrigatória / âncoras; checkpoint ao fim do bloco fixo."
        )
    elif meets_full_system.startswith("NÃO") or (
        derived_system_tokens is not None
        and min_tok is not None
        and derived_system_tokens < int(min_tok)
    ):
        classification = "C"
        recommendation = (
            "Modelo suporta caching, mas o system inteiro (~tokens derivados) "
            f"fica abaixo do mínimo ({min_tok}). Reorganizar não basta sem "
            "aumentar o prompt (proibido). Preferir outras otimizações "
            "(latência de output / max_tokens / dados de produção)."
        )
    elif meets_reorg.startswith("NÃO") or checkpoint_before_candidates.startswith("NÃO"):
        classification = "C"
        recommendation = (
            "Prefixo estático atual (~209 chars) e mesmo o bloco fixo se "
            f"reorganizado (~{static_if_reorganized_chars} chars) não atingem "
            f"o mínimo de {min_tok} tokens com margem. Top 8 dinâmico impede "
            "cache global útil na ordem atual."
        )
    else:
        classification = "C"
        recommendation = (
            "Suporte técnico existe, mas utilidade prática é baixa com Top 8 "
            "e system compacto atual."
        )

    return {
        "model_id": model_id,
        "cache_supported": bool(spec.get("cache_supported")),
        "min_checkpoint_tokens": min_tok,
        "max_checkpoints": spec.get("max_checkpoints"),
        "ttl": spec.get("ttl"),
        "ttl_options": spec.get("ttl_options"),
        "checkpoint_fields": spec.get("checkpoint_fields"),
        "invoke_model_supported": spec.get("invoke_model_supported"),
        "spec_source": spec.get("source"),
        "static_prefix_chars": static_prefix_chars,
        "static_suffix_chars": static_suffix_chars,
        "static_if_reorganized_chars": static_if_reorganized_chars,
        "system_total_chars": system_total,
        "candidate_catalog_chars": candidate_catalog_chars
        if candidate_catalog_chars is not None
        else fw_c,
        "dynamic_system_chars": dynamic_system_chars,
        "user_chars": user_c,
        "blocks_chars": {
            "intro": intro_c,
            "framework": fw_c,
            "diretrizes_obrigatoria": mid_c,
            "ancoras": anc_c,
            "regras": reg_c,
            "formato": fmt_c,
        },
        "static_prefix_tokens_derived": derived_static_prefix_tokens,
        "static_reorg_tokens_derived": derived_static_reorg_tokens,
        "system_tokens_derived": derived_system_tokens,
        "tokens_derivation_note": derived_note,
        "measured_input_tokens": measured_input_tokens,
        "checkpoint_before_candidates_valid": checkpoint_before_candidates.startswith(
            "SIM"
        ),
        "checkpoint_before_candidates_status": checkpoint_before_candidates,
        "checkpoint_after_candidates_stable": checkpoint_after_candidates_stable,
        "reorganized_prefix_meets_min_status": meets_reorg,
        "full_system_meets_min_status": meets_full_system,
        "classification": classification,
        "recommendation": recommendation,
        "invoke_model_cache_usage_keys": list(INVOKE_MODEL_CACHE_USAGE_KEYS),
        "converse_cache_usage_keys_reference": list(CONVERSE_CACHE_USAGE_KEYS),
        "block_order_real": [
            "intro (FIXO GLOBAL)",
            "framework / METODOLOGIAS DISPONÍVEIS Top N (DINÂMICO MATCHER)",
            "diretrizes_escola (POR ESCOLA, opcional)",
            "metodologia_obrigatoria (POR REQUEST, opcional)",
            "ancoras_de_estilo (POR REQUEST)",
            "regras (FIXO GLOBAL — hoje DEPOIS do dinâmico)",
            "formato (FIXO GLOBAL — hoje DEPOIS do dinâmico)",
            "messages.user_content (POR REQUEST)",
            "messages.assistant_prefill '{' (FIXO)",
        ],
    }


def format_cache_feasibility_report(analysis: dict[str, Any]) -> str:
    lines = [
        "CACHE FEASIBILITY",
        f"model_id: {analysis.get('model_id')}",
        f"cache_supported: {analysis.get('cache_supported')}",
        f"min_checkpoint_tokens: {analysis.get('min_checkpoint_tokens')}",
        f"max_checkpoints: {analysis.get('max_checkpoints')}",
        f"ttl: {analysis.get('ttl')}",
        f"checkpoint_fields: {analysis.get('checkpoint_fields')}",
        f"spec_source: {analysis.get('spec_source')}",
        f"static_prefix_chars: {analysis.get('static_prefix_chars')}",
        f"static_prefix_tokens_derived: {analysis.get('static_prefix_tokens_derived')}",
        f"static_if_reorganized_chars: {analysis.get('static_if_reorganized_chars')}",
        f"static_reorg_tokens_derived: {analysis.get('static_reorg_tokens_derived')}",
        f"system_total_chars: {analysis.get('system_total_chars')}",
        f"system_tokens_derived: {analysis.get('system_tokens_derived')}",
        f"candidate_catalog_chars: {analysis.get('candidate_catalog_chars')}",
        f"dynamic_system_chars: {analysis.get('dynamic_system_chars')}",
        f"user_chars: {analysis.get('user_chars')}",
        f"checkpoint_before_candidates_valid: {analysis.get('checkpoint_before_candidates_valid')}",
        f"checkpoint_before_candidates_status: {analysis.get('checkpoint_before_candidates_status')}",
        f"checkpoint_after_candidates_stable: {analysis.get('checkpoint_after_candidates_stable')}",
        f"reorganized_prefix_meets_min_status: {analysis.get('reorganized_prefix_meets_min_status')}",
        f"full_system_meets_min_status: {analysis.get('full_system_meets_min_status')}",
        f"classification: {analysis.get('classification')}",
        f"recommendation: {analysis.get('recommendation')}",
    ]
    if analysis.get("tokens_derivation_note"):
        lines.append(f"note: {analysis['tokens_derivation_note']}")
    return "\n".join(lines)
