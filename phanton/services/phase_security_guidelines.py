"""Capability: security_guidelines — diretrizes de segurança por padrão de mercado."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
for _path in (str(_ROOT), str(_BACKEND)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from database import SessionLocal  # noqa: E402
from services.build_order import (  # noqa: E402
    extract_build_order_from_inputs,
    normalize_build_order,
)
from services.gemini_client import extract_json_payload, generate_content  # noqa: E402
from services.phase_context import (  # noqa: E402
    load_dependency_artifacts,
    phase_cfg,
    phase_description,
    pipeline_label,
    resolve_depends_on,
)
from services.context_consistency import (  # noqa: E402
    contexto_tipo_from_spec,
    enforce_security_context_consistency,
)
from services.security_domain import (  # noqa: E402
    classify_sensitive_domain,
    general_guidelines_for_domain,
    module_guidelines_hint,
    standards_for_domain,
)
from services.structured_requirements import (  # noqa: E402
    format_structured_requirements_block,
)


def _normalize_security_payload(
    parsed: dict[str, Any],
    *,
    domain_id: Optional[str],
    build_order: list[dict[str, Any]],
) -> dict[str, Any]:
    standards = parsed.get("standards_aplicados") or parsed.get("standards") or []
    if isinstance(standards, str):
        standards = [standards]
    if not isinstance(standards, list) or not standards:
        standards = standards_for_domain(domain_id)

    gerais = parsed.get("diretrizes_gerais") or parsed.get("general") or []
    if isinstance(gerais, str):
        gerais = [gerais]
    if not isinstance(gerais, list) or not gerais:
        gerais = general_guidelines_for_domain(domain_id)

    por_mod_raw = (
        parsed.get("diretrizes_por_modulo")
        or parsed.get("modules")
        or parsed.get("por_modulo")
        or {}
    )
    por_mod: dict[str, list[str]] = {}
    if isinstance(por_mod_raw, dict):
        for key, value in por_mod_raw.items():
            name = str(key).strip()
            if not name:
                continue
            if isinstance(value, list):
                items = [str(v).strip() for v in value if str(v).strip()]
            elif isinstance(value, str) and value.strip():
                items = [value.strip()]
            else:
                items = []
            if items:
                por_mod[name] = items

    # Garante cobertura de todos os módulos do build_order
    for entry in build_order:
        modulo = entry.get("modulo") or ""
        if not modulo:
            continue
        if modulo not in por_mod:
            # try case-insensitive
            found = next(
                (k for k in por_mod if k.lower() == modulo.lower()),
                None,
            )
            if found:
                por_mod[modulo] = por_mod.pop(found)
            else:
                por_mod[modulo] = module_guidelines_hint(
                    domain_id, modulo, entry.get("escopo") or ""
                )

    return {
        "domain": domain_id,
        "standards_aplicados": [str(s).strip() for s in standards if str(s).strip()],
        "diretrizes_gerais": [str(g).strip() for g in gerais if str(g).strip()],
        "diretrizes_por_modulo": por_mod,
    }


def _fallback_security(
    *,
    domain_id: Optional[str],
    build_order: list[dict[str, Any]],
    reason: str,
) -> dict[str, Any]:
    por_mod = {
        entry["modulo"]: module_guidelines_hint(
            domain_id, entry["modulo"], entry.get("escopo") or ""
        )
        for entry in build_order
        if entry.get("modulo")
    }
    payload = _normalize_security_payload(
        {
            "standards_aplicados": standards_for_domain(domain_id),
            "diretrizes_gerais": general_guidelines_for_domain(domain_id),
            "diretrizes_por_modulo": por_mod,
        },
        domain_id=domain_id,
        build_order=build_order,
    )
    payload["meta_fallback_reason"] = reason
    return payload


def _build_security_prompt(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
    *,
    domain_id: str,
    build_order: list[dict[str, Any]],
) -> str:
    pedido = str(
        spec.get("user_prompt") or spec.get("description") or pipeline_label(spec)
    ).strip()
    standards = standards_for_domain(domain_id)
    descricao = phase_description(
        cfg,
        fallback=(
            "Gerar diretrizes de segurança baseadas em padrões de mercado "
            "aplicáveis ao domínio, gerais e por módulo."
        ),
    )
    req_block = format_structured_requirements_block(
        spec.get("structured_requirements") if isinstance(spec, dict) else None
    )
    tipo = contexto_tipo_from_spec(spec)
    single_rule = ""
    if tipo == "single_tenant":
        single_rule = (
            "\n- CONTEXTO SINGLE-TENANT: PROIBIDO mencionar tenant, multi-tenant, "
            "X-Tenant-ID, schema por tenant, isolamento entre organizações/"
            "empresas. Fale apenas em authz por papel/usuário na mesma org."
        )
    return f"""
Atue como arquiteto de segurança de aplicações (AppSec).

Domínio classificado: {domain_id}
Standards de mercado que DEVEM fundamentar a resposta (não invente nomes):
{json.dumps(standards, ensure_ascii=False)}

Pipeline: {pipeline_label(spec)}
Fase: {cfg.get("name") or phase_id}
Pedido: {pedido}

Instruções:
{descricao}

{req_block}

=== build_order (módulos) ===
{json.dumps(build_order, ensure_ascii=False, indent=2)}

=== Artefatos de entrada (SDD/PRD resumidos) ===
{json.dumps(inputs, ensure_ascii=False, default=str)[:28_000]}

Produza diretrizes CONCRETAS e acionáveis, citando o standard (ex.: ASVS V4,
FAPI 2.0 PAR+PKCE, OWASP API Top 10, LGPD). Não use frases vagas como
"seguir boas práticas".

Responda APENAS com JSON válido:
{{
  "standards_aplicados": ["..."],
  "diretrizes_gerais": ["..."],
  "diretrizes_por_modulo": {{
    "nome-do-modulo": ["..."]
  }}
}}

Regras:
- standards_aplicados deve refletir o domínio ({domain_id}).
- diretrizes_por_modulo DEVE cobrir TODOS os módulos do build_order.
- Se build_order estiver vazio, ainda assim preencha diretrizes_gerais.
{single_rule}
""".strip()


def _generate_security_safe(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
    *,
    domain_id: str,
    build_order: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    errors: list[str] = []
    meta: dict[str, Any] = {"domain": domain_id}
    prompt = _build_security_prompt(
        inputs, spec, phase_id, cfg, domain_id=domain_id, build_order=build_order
    )
    for as_json, temperature, max_tokens in (
        (True, 0.25, 6144),
        (True, 0.2, 4096),
        (False, 0.15, 3072),
    ):
        try:
            raw_text, meta = generate_content(
                prompt,
                enable_google_search=False,
                response_json=as_json,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            parsed = extract_json_payload(raw_text)
            if isinstance(parsed, dict):
                normalized = _normalize_security_payload(
                    parsed, domain_id=domain_id, build_order=build_order
                )
                if normalized.get("diretrizes_gerais"):
                    return normalized, {
                        **meta,
                        "attempts": errors,
                        "domain": domain_id,
                    }
            errors.append(f"payload_incompleto(tokens={max_tokens})")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    return (
        _fallback_security(
            domain_id=domain_id,
            build_order=build_order,
            reason="; ".join(errors) or "modelo indisponivel",
        ),
        {**meta, "fallback": True, "attempts": errors, "domain": domain_id},
    )


async def execute_phase_security_guidelines(
    run_id: str,
    spec: dict[str, Any],
    db_session: Optional[Session] = None,
    phase_id: str = "security_guidelines",
) -> dict[str, Any]:
    owns_session = db_session is None
    session = db_session or SessionLocal()
    spec = spec if isinstance(spec, dict) else {}
    cfg = phase_cfg(spec, phase_id)
    pedido = str(
        spec.get("user_prompt") or spec.get("description") or pipeline_label(spec)
    )
    domain_id = classify_sensitive_domain(pedido) or "financeiro"

    try:
        try:
            inputs = load_dependency_artifacts(session, run_id, spec, phase_id) or {}
            build_order = extract_build_order_from_inputs(inputs)
            if not build_order:
                # SDD pode estar no depends_on sem build_order estruturado
                for payload in inputs.values():
                    if isinstance(payload, dict):
                        build_order = normalize_build_order(
                            payload.get("build_order")
                        )
                        if build_order:
                            break

            parsed, meta = await asyncio.to_thread(
                _generate_security_safe,
                inputs,
                spec,
                phase_id,
                cfg,
                domain_id=domain_id,
                build_order=build_order,
            )
            parsed, ctx_avisos = await asyncio.to_thread(
                enforce_security_context_consistency,
                parsed,
                spec,
                build_order=build_order,
                domain_id=domain_id,
            )
            if ctx_avisos:
                meta = {
                    **meta,
                    "context_consistency_warnings": ctx_avisos,
                }
            return {
                "status": "success",
                "phase": phase_id,
                "capability": "security_guidelines",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": parsed,
                "standards_aplicados": parsed.get("standards_aplicados"),
                "diretrizes_gerais": parsed.get("diretrizes_gerais"),
                "diretrizes_por_modulo": parsed.get("diretrizes_por_modulo"),
                "context_consistency_warnings": parsed.get(
                    "context_consistency_warnings"
                )
                or ctx_avisos,
                "depends_on": resolve_depends_on(spec, phase_id),
                "inputs_used": list(inputs.keys()),
                "meta": meta,
            }
        except Exception as exc:
            try:
                inputs = load_dependency_artifacts(session, run_id, spec, phase_id) or {}
            except Exception:
                inputs = {}
            build_order = extract_build_order_from_inputs(inputs)
            parsed = _fallback_security(
                domain_id=domain_id,
                build_order=build_order,
                reason=str(exc),
            )
            return {
                "status": "success",
                "phase": phase_id,
                "capability": "security_guidelines",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": parsed,
                "standards_aplicados": parsed.get("standards_aplicados"),
                "diretrizes_gerais": parsed.get("diretrizes_gerais"),
                "diretrizes_por_modulo": parsed.get("diretrizes_por_modulo"),
                "meta": {"fallback": True, "error": str(exc), "domain": domain_id},
            }
    finally:
        if owns_session:
            session.close()
