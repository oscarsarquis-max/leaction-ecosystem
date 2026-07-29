"""Capability: prompt_cursor — prompt(s) executáveis para IDE a partir de PRD + SDD.

Se o SDD trouxer `build_order`, gera uma fila de prompts por módulo.
Caso contrário, mantém o comportamento legado: um único `cursor_prompt`.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

from google.genai import types
from sqlalchemy.orm import Session

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
for _path in (str(_ROOT), str(_BACKEND)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from database import SessionLocal  # noqa: E402
from services.build_order import (  # noqa: E402
    build_initial_queue,
    extract_build_order_from_inputs,
)
from services.context_consistency import (  # noqa: E402
    contexto_tipo_from_spec,
    find_forbidden_terms,
    regenerar_prompt_modulo_single_tenant,
    validar_consistencia_contexto,
)
from services.gemini_client import extract_json_payload, generate_content  # noqa: E402
from services.phase_context import (  # noqa: E402
    load_dependency_artifacts,
    phase_cfg,
    phase_description,
    pipeline_label,
    resolve_depends_on,
)
from services.security_domain import (  # noqa: E402
    append_security_section,
    extract_security_artifact,
)
from services.structured_requirements import (  # noqa: E402
    format_structured_requirements_block,
)

_MODULE_PROMPT_ITEM_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "modulo": types.Schema(type=types.Type.STRING),
        "prompt": types.Schema(type=types.Type.STRING),
        "testes_requeridos": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
        ),
    },
    required=["modulo", "prompt", "testes_requeridos"],
)

MODULE_QUEUE_RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "module_prompts": types.Schema(
            type=types.Type.ARRAY,
            items=_MODULE_PROMPT_ITEM_SCHEMA,
        ),
    },
    required=["module_prompts"],
)

_MAX_INPUT_CHARS = 56_000


def _compact_inputs(inputs: dict[str, Any], limit: int = _MAX_INPUT_CHARS) -> dict[str, Any]:
    serialized = json.dumps(inputs, ensure_ascii=False, default=str)
    if len(serialized) <= limit:
        return inputs
    compact: dict[str, Any] = {}
    budget = max(3000, limit // max(len(inputs), 1))
    for key, value in inputs.items():
        chunk = json.dumps(value, ensure_ascii=False, default=str)
        compact[key] = chunk[:budget] + ("…[truncado]" if len(chunk) > budget else "")
    return compact


def _extract_docs(inputs: dict[str, Any]) -> tuple[str, str]:
    prd = ""
    sdd = ""
    for payload in inputs.values():
        if not isinstance(payload, dict):
            continue
        if not prd and payload.get("prd_markdown"):
            prd = str(payload["prd_markdown"])
        if not sdd and payload.get("sdd_markdown"):
            sdd = str(payload["sdd_markdown"])
        nested = payload.get("artifact_data")
        if isinstance(nested, dict):
            if not prd and nested.get("prd_markdown"):
                prd = str(nested["prd_markdown"])
            if not sdd and nested.get("sdd_markdown"):
                sdd = str(nested["sdd_markdown"])
    return prd.strip(), sdd.strip()


def _build_cursor_prompt_request(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> str:
    inputs_json = json.dumps(inputs, ensure_ascii=False, indent=2, default=str)
    descricao = phase_description(
        cfg,
        fallback=(
            "Criar prompt de ação curto e executável para implementação no Cursor IDE."
        ),
    )
    deps = resolve_depends_on(spec, phase_id)
    pedido = str(
        spec.get("user_prompt") or spec.get("description") or pipeline_label(spec)
    ).strip()
    prd, sdd = _extract_docs(inputs)

    return f"""
Atue como Staff Engineer.

Você receberá o PRD e o SDD do projeto. Sua tarefa é criar um prompt de ação
executável, curto e direto, para o desenvolvedor colar no Cursor IDE.
O prompt deve instruir a IA codificadora (Claude 3.5 Sonnet / agente do Cursor)
a ler os arquivos PRD.md e SDD.md (que serão salvos na raiz do projeto) e
iniciar a implementação passo a passo respeitando a arquitetura definida.

Pipeline: {pipeline_label(spec)}
Fase: {cfg.get("name") or phase_id}
depends_on: {", ".join(deps) or "nenhuma"}

Pedido original do usuário:
{pedido}

Instruções desta fase:
{descricao}

=== PRD (resumo/fonte) ===
{prd[:20_000] if prd else "(não encontrado como prd_markdown — use artefatos abaixo)"}

=== SDD (resumo/fonte) ===
{sdd[:20_000] if sdd else "(não encontrado como sdd_markdown — use artefatos abaixo)"}

=== Artefatos brutos ===
{inputs_json}

Regras do cursor_prompt:
- Curto, direto, acionável (idealmente < 600 palavras).
- Assumir que PRD.md e SDD.md existem na raiz.
- Pedir implementação incremental, testes e respeito à arquitetura do SDD.
- Não reescrever o PRD/SDD inteiros dentro do prompt.

Responda APENAS com um único objeto JSON válido (UTF-8):
{{
  "cursor_prompt": "texto do prompt executável..."
}}
""".strip()


def _build_module_queue_request(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
    build_order: list[dict[str, Any]],
) -> str:
    pedido = str(
        spec.get("user_prompt") or spec.get("description") or pipeline_label(spec)
    ).strip()
    prd, sdd = _extract_docs(inputs)
    order_json = json.dumps(build_order, ensure_ascii=False, indent=2)
    modules_list = ", ".join(m["modulo"] for m in build_order)
    req_block = format_structured_requirements_block(
        spec.get("structured_requirements") if isinstance(spec, dict) else None
    )
    tipo = contexto_tipo_from_spec(spec)
    single_rule = ""
    if tipo == "single_tenant":
        single_rule = (
            "\n- SINGLE-TENANT: PROIBIDO tenant/multi-tenant/X-Tenant-ID/"
            "schema por tenant/isolamento entre organizações. Authz = papéis "
            "na mesma organização."
        )

    return f"""
Atue como Staff Engineer.

Crie UM prompt curto e executável por módulo da fila de implementação abaixo.
Cada prompt será colado no Cursor IDE para implementar APENAS aquele módulo,
respeitando PRD.md e SDD.md na raiz do projeto.

Pipeline: {pipeline_label(spec)}
Fase: {cfg.get("name") or phase_id}
Pedido: {pedido}

{req_block}

=== build_order (ordem e dependências) ===
{order_json}

=== PRD (fonte) ===
{prd[:12_000] if prd else "(ausente)"}

=== SDD (fonte) ===
{sdd[:16_000] if sdd else "(ausente)"}

Regras por prompt de módulo:
- Objetivo claro do módulo (1-2 frases).
- Requisitos / contratos mínimos a implementar agora.
- Fora de escopo (não implementar outros módulos desta fila).
- Assumir que dependências listadas em depende_de já existem (interfaces/stubs ok).
- Curto (< 350 palavras cada). Não reescrever PRD/SDD inteiros.
- testes_requeridos: array NÃO-VAZIO com testes AUTOMATIZADOS específicos das
  invariantes daquele módulo (ex.: trigger rejeita UPDATE, constraint de soma
  zero, authz por papel). NÃO use texto genérico como "escreva testes".
- NÃO inclua a seção ## Testes dentro de `prompt` — ela será anexada depois.
- Se o item tiver camada=frontend (ou nome *-frontend/*-player/*-ui): o prompt
  DEVE ser descritivo de UI — listar telas/rotas, componentes, integração com
  APIs já entregues, estados loading/erro/offline, CSP do SPA, e testes de
  render/interação. NÃO pedir só endpoints de backend.
- Se camada=backend: foque API/dados/testes de servidor.
{single_rule}

Módulos obrigatórios na resposta (nesta ordem): {modules_list}

O schema exige module_prompts[].testes_requeridos (mín. 2 itens concretos cada).
""".strip()


def _strip_testes_section(prompt: str) -> str:
    base = prompt or ""
    idx = base.find("## Testes")
    if idx >= 0:
        return base[:idx].rstrip()
    return base.rstrip()


def _append_testes_section(prompt: str, testes: list[str]) -> str:
    base = _strip_testes_section(prompt)
    lines = ["## Testes"]
    for item in testes:
        text = str(item).strip()
        if text:
            lines.append(f"- {text}")
    if len(lines) <= 1:
        raise ValueError("testes_requeridos vazio — seção ## Testes obrigatória")
    return f"{base}\n\n" + "\n".join(lines)


def _default_testes_for_module(entry: dict[str, Any]) -> list[str]:
    modulo = entry.get("modulo") or "modulo"
    escopo = entry.get("escopo") or ""
    camada = str(entry.get("camada") or "backend").lower()
    if camada == "frontend":
        return [
            f"Teste de render da tela principal de `{modulo}` (componente/rota monta sem erro).",
            f"Teste de interação/estado: loading ou erro de API tratado na UI de `{modulo}`.",
        ]
    return [
        f"Teste automatizado cobrindo o caminho feliz principal de `{modulo}` ({escopo or 'escopo do SDD'}).",
        f"Teste automatizado de falha/invariante de segurança ou integridade em `{modulo}` (rejeição explícita).",
    ]


def _parse_module_prompts_structured(
    parsed: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """{modulo: {prompt, testes_requeridos}} — exige testes não-vazios."""
    raw = parsed.get("module_prompts") or parsed.get("prompts") or []
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        modulo = str(item.get("modulo") or item.get("module") or "").strip()
        prompt = str(item.get("prompt") or item.get("cursor_prompt") or "").strip()
        testes = item.get("testes_requeridos") or item.get("tests") or []
        if isinstance(testes, str):
            testes = [testes]
        if not isinstance(testes, list):
            testes = []
        testes = [str(t).strip() for t in testes if str(t).strip()]
        if modulo and prompt and testes:
            out[modulo] = {"prompt": prompt, "testes_requeridos": testes}
    return out


def _normalize_cursor(parsed: dict[str, Any]) -> dict[str, Any]:
    text = (
        parsed.get("cursor_prompt")
        or parsed.get("prompt")
        or parsed.get("prompt_markdown")
        or ""
    )
    if isinstance(text, dict):
        text = text.get("content") or text.get("texto") or json.dumps(text, ensure_ascii=False)
    return {"cursor_prompt": str(text or "").strip()}


def _fallback_cursor(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    label = pipeline_label(spec)
    prd, sdd = _extract_docs(inputs)
    return {
        "cursor_prompt": f"""# Implementação — {label}

Você é um engenheiro sênior no Cursor IDE.

## Contexto
Os arquivos `PRD.md` e `SDD.md` estão na raiz do projeto. Leia-os por completo
antes de escrever código. (Geração em fallback: {reason})

## Objetivo
Implementar o MVP descrito no PRD respeitando a arquitetura e os contratos do SDD.

## Passo a passo
1. Confirme stack, pastas e modelo de dados do SDD.
2. Crie a estrutura mínima do projeto (sem over-engineering).
3. Implemente as entidades/APIs/componentes prioritários do MVP.
4. Adicione testes básicos e um README de execução local.
5. Pare e reporte o que falta após o primeiro incremento útil.

## Fontes
- PRD.md{" (presente no artefato)" if prd else ""}
- SDD.md{" (presente no artefato)" if sdd else ""}

Comece pelo passo 1.
""".strip()
    }


def _fallback_module_prompt(
    entry: dict[str, Any],
    spec: dict[str, Any],
    *,
    testes: Optional[list[str]] = None,
) -> str:
    label = pipeline_label(spec)
    modulo = entry.get("modulo") or "modulo"
    escopo = entry.get("escopo") or "implementar conforme SDD"
    deps = entry.get("depende_de") or []
    deps_txt = ", ".join(deps) if deps else "nenhuma"
    testes = testes or _default_testes_for_module(entry)
    base = f"""# Implementar módulo `{modulo}` — {label}

Leia `PRD.md` e `SDD.md` na raiz. Implemente APENAS este módulo.

## Objetivo
{escopo}

## Dependências já disponíveis
{deps_txt}

## Requisitos
- Respeitar contratos/interfaces do SDD para `{modulo}`.
- Código testável e incremental; sem over-engineering.
- Não implementar outros módulos da fila neste passo.

## Fora de escopo
Qualquer módulo fora de `{modulo}`.

Comece pela estrutura mínima e pelos contratos públicos do módulo.
""".strip()
    return _append_testes_section(base, testes)


def _generate_cursor_safe(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    errors: list[str] = []
    meta: dict[str, Any] = {}
    attempts = [
        (_compact_inputs(inputs, 56_000), True, 0.25, 4096),
        (_compact_inputs(inputs, 28_000), True, 0.2, 3072),
        (_compact_inputs(inputs, 14_000), False, 0.15, 2048),
    ]
    for compact, as_json, temperature, max_tokens in attempts:
        prompt = _build_cursor_prompt_request(compact, spec, phase_id, cfg)
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
                normalized = _normalize_cursor(parsed)
                if normalized.get("cursor_prompt"):
                    return normalized, {
                        **meta,
                        "attempts": errors,
                        "used_max_output_tokens": max_tokens,
                    }
            stripped = (raw_text or "").strip()
            if len(stripped) > 80 and not stripped.lstrip().startswith("{"):
                return {"cursor_prompt": stripped}, {
                    **meta,
                    "attempts": errors,
                    "raw_text": True,
                }
            errors.append(f"sem_cursor_prompt(tokens={max_tokens})")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    return (
        _fallback_cursor(inputs, spec, reason="; ".join(errors) or "modelo indisponível"),
        {**meta, "fallback": True, "attempts": errors},
    )


def _enforce_module_prompts_context(
    prompts_map: dict[str, str],
    testes_map: dict[str, list[str]],
    build_order: list[dict[str, Any]],
    spec: dict[str, Any],
    *,
    security: Optional[dict[str, Any]] = None,
) -> tuple[dict[str, str], dict[str, list[str]], list[dict[str, Any]]]:
    """Valida single_tenant nos prompts finais; regenera pontualmente se preciso."""
    tipo = contexto_tipo_from_spec(spec)
    if tipo != "single_tenant":
        return prompts_map, testes_map, []

    problemas = validar_consistencia_contexto(prompts_map, {"tipo": tipo})
    avisos: list[dict[str, Any]] = []
    escopo_by = {
        e["modulo"]: e.get("escopo") or ""
        for e in build_order
        if e.get("modulo")
    }
    for prob in problemas:
        modulo = prob["modulo"]
        termos = prob.get("termos") or []
        try:
            regen = regenerar_prompt_modulo_single_tenant(
                modulo=modulo,
                escopo=escopo_by.get(modulo, ""),
                prompt_atual=prompts_map.get(modulo, ""),
                termos_problema=termos,
                testes_requeridos=testes_map.get(modulo) or [],
            )
            new_prompt = regen["prompt"]
            new_testes = regen["testes_requeridos"]
            # Remove seção ## Testes antiga se o modelo devolveu prompt limpo
            rebuilt = _append_testes_section(new_prompt, new_testes)
            if security:
                # reanexa segurança (já filtrada na fase security) sem duplicar
                rebuilt = append_security_section(rebuilt, security, modulo=modulo)
            prompts_map[modulo] = rebuilt
            testes_map[modulo] = new_testes
            if find_forbidden_terms(prompts_map[modulo], contexto_tipo=tipo):
                raise ValueError("ainda contém termos proibidos após regen")
        except Exception as exc:
            avisos.append(
                {
                    "modulo": modulo,
                    "termos": termos,
                    "mensagem": (
                        "possível inconsistência de contexto — revisar "
                        f"manualmente ({exc})"
                    ),
                }
            )
    for prob in validar_consistencia_contexto(prompts_map, {"tipo": tipo}):
        mod = prob["modulo"]
        if not any(a.get("modulo") == mod for a in avisos):
            avisos.append(
                {
                    "modulo": mod,
                    "termos": prob.get("termos") or [],
                    "mensagem": (
                        "possível inconsistência de contexto — revisar manualmente"
                    ),
                }
            )
    return prompts_map, testes_map, avisos


def _generate_module_queue_safe(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
    build_order: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    errors: list[str] = []
    meta: dict[str, Any] = {}
    structured_map: dict[str, dict[str, Any]] = {}

    attempts = [
        (_compact_inputs(inputs, 48_000), 0.25, 8192),
        (_compact_inputs(inputs, 24_000), 0.2, 6144),
    ]
    for compact, temperature, max_tokens in attempts:
        prompt = _build_module_queue_request(
            compact, spec, phase_id, cfg, build_order
        )
        try:
            raw_text, meta = generate_content(
                prompt,
                enable_google_search=False,
                response_json=True,
                response_schema=MODULE_QUEUE_RESPONSE_SCHEMA,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            parsed = extract_json_payload(raw_text)
            if isinstance(parsed, dict):
                structured_map = _parse_module_prompts_structured(parsed)
                # Exige cobertura com testes — sem testes = erro de schema
                missing_tests = [
                    e["modulo"]
                    for e in build_order
                    if e.get("modulo")
                    and e["modulo"] not in structured_map
                ]
                if structured_map and not missing_tests:
                    break
                if structured_map and len(structured_map) >= max(1, len(build_order) // 2):
                    # parcial ok — completa faltantes depois; mas marca erro se
                    # algum item veio sem testes (já filtrado pelo parser)
                    break
                errors.append(
                    f"testes_requeridos_ausente_ou_parcial(tokens={max_tokens})"
                )
                structured_map = {}
            else:
                errors.append(f"sem_module_prompts(tokens={max_tokens})")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    prompts_map: dict[str, str] = {}
    testes_map: dict[str, list[str]] = {}
    fallback_modules: list[str] = []

    for entry in build_order:
        modulo = entry["modulo"]
        item = structured_map.get(modulo)
        if item and item.get("testes_requeridos"):
            try:
                prompts_map[modulo] = _append_testes_section(
                    item["prompt"], item["testes_requeridos"]
                )
                testes_map[modulo] = list(item["testes_requeridos"])
                continue
            except ValueError as exc:
                errors.append(f"{modulo}:{exc}")
        # Sem testes válidos → fallback explícito (nunca silencioso sem ## Testes)
        fallback_modules.append(modulo)
        testes = _default_testes_for_module(entry)
        prompts_map[modulo] = _fallback_module_prompt(entry, spec, testes=testes)
        testes_map[modulo] = testes
        errors.append(f"testes_requeridos_fallback:{modulo}")

    security = extract_security_artifact(inputs)
    if security:
        prompts_map = {
            modulo: append_security_section(prompt, security, modulo=modulo)
            for modulo, prompt in prompts_map.items()
        }

    prompts_map, testes_map, ctx_avisos = _enforce_module_prompts_context(
        prompts_map,
        testes_map,
        build_order,
        spec,
        security=security,
    )

    # Anexa flag de aviso no item da fila quando houver inconsistência
    warn_by_mod = {a["modulo"]: a for a in ctx_avisos}
    queue = build_initial_queue(build_order, prompts_map)
    for row in queue:
        mod = row.get("modulo")
        if mod in warn_by_mod:
            row["context_consistency_warning"] = warn_by_mod[mod].get("mensagem")
            row["context_forbidden_terms"] = warn_by_mod[mod].get("termos") or []
        if mod in testes_map:
            row["testes_requeridos"] = testes_map[mod]

    first_liberado = next((q for q in queue if q.get("status") == "liberado"), None)
    return (
        {
            "mode": "module_queue",
            "module_prompts": queue,
            "build_order": build_order,
            "cursor_prompt": (first_liberado or {}).get("prompt") or "",
            "security_applied": bool(security),
            "context_consistency_warnings": ctx_avisos,
        },
        {
            **meta,
            "attempts": errors,
            "queue_size": len(queue),
            "security_applied": bool(security),
            "fallback_modules": fallback_modules,
            "context_consistency_warnings": ctx_avisos,
            "structured_output": True,
        },
    )


async def execute_phase_prompt_cursor(
    run_id: str,
    spec: dict[str, Any],
    db_session: Optional[Session] = None,
    phase_id: str = "prompt_cursor",
) -> dict[str, Any]:
    owns_session = db_session is None
    session = db_session or SessionLocal()
    spec = spec if isinstance(spec, dict) else {}
    cfg = phase_cfg(spec, phase_id)

    try:
        try:
            inputs = load_dependency_artifacts(session, run_id, spec, phase_id)
            if not inputs:
                raise RuntimeError(
                    f"Nenhum artefato de entrada para '{phase_id}'. "
                    "Aprove PRD e SDD (depends_on) antes do prompt Cursor."
                )

            build_order = extract_build_order_from_inputs(inputs)
            if build_order:
                parsed, meta = await asyncio.to_thread(
                    _generate_module_queue_safe,
                    inputs,
                    spec,
                    phase_id,
                    cfg,
                    build_order,
                )
            else:
                parsed, meta = await asyncio.to_thread(
                    _generate_cursor_safe, inputs, spec, phase_id, cfg
                )
                security = extract_security_artifact(inputs)
                if security and parsed.get("cursor_prompt"):
                    parsed["cursor_prompt"] = append_security_section(
                        parsed["cursor_prompt"], security
                    )
                    parsed["security_applied"] = True
                    meta = {**meta, "security_applied": True}

            return {
                "status": "success",
                "phase": phase_id,
                "capability": "prompt_cursor",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": parsed,
                "cursor_prompt": parsed.get("cursor_prompt"),
                "module_prompts": parsed.get("module_prompts"),
                "context_consistency_warnings": parsed.get(
                    "context_consistency_warnings"
                ),
                "format": "markdown",
                "inputs_used": list(inputs.keys()),
                "meta": meta,
            }
        except Exception as exc:
            try:
                inputs = load_dependency_artifacts(session, run_id, spec, phase_id) or {}
            except Exception:
                inputs = {}
            if inputs:
                build_order = extract_build_order_from_inputs(inputs)
                if build_order:
                    prompts_map = {
                        e["modulo"]: _fallback_module_prompt(e, spec)
                        for e in build_order
                    }
                    queue = build_initial_queue(build_order, prompts_map)
                    for row in queue:
                        row["testes_requeridos"] = _default_testes_for_module(
                            next(
                                (e for e in build_order if e.get("modulo") == row.get("modulo")),
                                {"modulo": row.get("modulo"), "escopo": ""},
                            )
                        )
                    first = next((q for q in queue if q.get("status") == "liberado"), None)
                    parsed = {
                        "mode": "module_queue",
                        "module_prompts": queue,
                        "build_order": build_order,
                        "cursor_prompt": (first or {}).get("prompt") or "",
                    }
                else:
                    parsed = _fallback_cursor(inputs, spec, reason=str(exc))
                return {
                    "status": "success",
                    "phase": phase_id,
                    "capability": "prompt_cursor",
                    "run_id": run_id,
                    "pipeline_name": pipeline_label(spec),
                    "artifact_data": parsed,
                    "cursor_prompt": parsed.get("cursor_prompt"),
                    "module_prompts": parsed.get("module_prompts"),
                    "format": "markdown",
                    "inputs_used": list(inputs.keys()),
                    "meta": {"fallback": True, "error": str(exc)},
                }
            return {
                "status": "error",
                "phase": phase_id,
                "capability": "prompt_cursor",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": {"erro": str(exc)},
            }
    finally:
        if owns_session:
            session.close()
