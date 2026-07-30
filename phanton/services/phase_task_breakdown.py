"""Capability: task_breakdown — fatia PRD+SDD em Epics/Issues (JSON Linear/Jira-ready)."""

from __future__ import annotations

import asyncio
import json
import re
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
from services.llm.json_utils import extract_json_payload  # noqa: E402
from services.llm.runtime import generate_content  # noqa: E402
from services.phase_context import (  # noqa: E402
    load_dependency_artifacts,
    phase_cfg,
    phase_description,
    pipeline_label,
    resolve_depends_on,
)

_MAX_PRD_CHARS = 10_000
_MAX_SDD_CHARS = 14_000
_ISSUE_TYPES = frozenset({"backend", "frontend", "infra", "qa"})

_SYSTEM_INSTRUCTION = """
Você é um Tech Lead sênior especializado em quebrar monolitos e PRDs/SDDs em
trabalho atômico exportável para Linear/Jira.

REGRA DE IDIOMA: Todo o conteúdo gerado, especialmente o campo
`description_micro_prompt`, DEVE ser escrito estritamente em Português do Brasil
(PT-BR). Mantenha em inglês apenas nomes de tecnologias ou variáveis literais.
(Títulos de épicos/issues também em PT-BR. Nunca gere descrições em inglês.)

Regras:
1. Responda APENAS com um único objeto JSON válido (UTF-8), sem markdown externo.
2. Cada Issue deve ser implementável por um desenvolvedor (ou agente de código)
   em uma sessão focada — sem épicos disfarçados de issue.
3. REGRA DE OURO — `description_micro_prompt`: NÃO é um resumo. É um
   Micro-Prompt para o Cursor/IDE: instruções técnicas diretas, stack a usar,
   arquivos/camadas afetados, contratos (API/UI/dados) e critério de pronto.
   Um humano deve poder copiar/colar esse campo no agente de código.
   O micro-prompt inteiro deve estar em PT-BR (exceto nomes técnicos literais).
4. `type` de cada issue: exatamente um de backend | frontend | infra | qa
   (esses valores de enum ficam em inglês; títulos e textos ficam em PT-BR).
5. `dependencies` referencia títulos (ou ids estáveis) de outras issues que
   bloqueiam esta; use [] se não houver. Títulos referenciados também em PT-BR.
6. Preferir 2–6 épicos e 3–8 issues por épico no MVP (ajuste se o SDD for mínimo).
7. Não invente stack que contradiga o SDD; se o SDD estiver vazio/fallback,
   derive do PRD com hipóteses explícitas no micro-prompt (em PT-BR).
""".strip()

_ISSUE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "type": {
            "type": "STRING",
            "enum": ["backend", "frontend", "infra", "qa"],
        },
        "description_micro_prompt": {"type": "STRING"},
        "dependencies": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
    },
    "required": ["title", "type", "description_micro_prompt", "dependencies"],
}

_EPIC_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "description": {"type": "STRING"},
        "issues": {
            "type": "ARRAY",
            "items": _ISSUE_SCHEMA,
        },
    },
    "required": ["title", "description", "issues"],
}

TASK_BREAKDOWN_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "epics": {
            "type": "ARRAY",
            "items": _EPIC_SCHEMA,
        },
    },
    "required": ["epics"],
}


def _extract_markdown_field(payload: Any, *keys: str) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    nested = payload.get("artifact_data")
    if isinstance(nested, dict):
        for key in keys:
            value = nested.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _pick_prd_sdd(inputs: dict[str, Any]) -> tuple[str, str, Optional[str], Optional[str]]:
    """Retorna (prd_md, sdd_md, prd_phase_id, sdd_phase_id)."""
    prd_text, prd_id = "", None
    sdd_text, sdd_id = "", None
    for phase_id, payload in (inputs or {}).items():
        if not isinstance(payload, dict):
            continue
        prd = _extract_markdown_field(payload, "prd_markdown", "prd", "markdown")
        sdd = _extract_markdown_field(payload, "sdd_markdown", "sdd")
        pid = str(phase_id)
        if prd and (not prd_text or "prd" in pid.lower()):
            prd_text, prd_id = prd, pid
        if sdd and (not sdd_text or "sdd" in pid.lower()):
            sdd_text, sdd_id = sdd, pid
    return (
        prd_text[:_MAX_PRD_CHARS],
        sdd_text[:_MAX_SDD_CHARS],
        prd_id,
        sdd_id,
    )


def _normalize_issue(raw: Any, *, index: int) -> Optional[dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or raw.get("name") or "").strip()
    if not title:
        return None
    itype = str(raw.get("type") or "backend").strip().lower()
    if itype not in _ISSUE_TYPES:
        # Heurística leve
        blob = f"{title} {raw.get('description_micro_prompt') or ''}".lower()
        if any(t in blob for t in ("react", "ui", "tela", "frontend", "css")):
            itype = "frontend"
        elif any(t in blob for t in ("docker", "ci", "deploy", "infra", "k8s")):
            itype = "infra"
        elif any(t in blob for t in ("test", "qa", "cypress", "playwright")):
            itype = "qa"
        else:
            itype = "backend"

    micro = (
        raw.get("description_micro_prompt")
        or raw.get("micro_prompt")
        or raw.get("description")
        or raw.get("prompt")
        or ""
    )
    micro = str(micro).strip()
    if not micro:
        micro = (
            f"Implemente a tarefa «{title}» alinhada ao SDD/PRD. "
            "Siga a stack do SDD, altere só o necessário e valide o critério de pronto."
        )

    deps_raw = raw.get("dependencies") or raw.get("depends_on") or []
    if isinstance(deps_raw, str):
        deps = [deps_raw] if deps_raw.strip() else []
    elif isinstance(deps_raw, list):
        deps = [str(d).strip() for d in deps_raw if str(d).strip()]
    else:
        deps = []

    issue_id = str(raw.get("id") or f"issue-{index}").strip()
    return {
        "id": issue_id,
        "title": title,
        "type": itype,
        "description_micro_prompt": micro,
        "dependencies": deps,
    }


def _normalize_epic(raw: Any, *, index: int) -> Optional[dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or raw.get("name") or "").strip()
    if not title:
        return None
    description = str(
        raw.get("description") or raw.get("objetivo") or raw.get("goal") or ""
    ).strip()
    if not description:
        description = f"Épico técnico: {title}."

    issues_in = raw.get("issues") or raw.get("tasks") or raw.get("stories") or []
    if not isinstance(issues_in, list):
        issues_in = []
    issues: list[dict[str, Any]] = []
    for i, item in enumerate(issues_in, start=1):
        normalized = _normalize_issue(item, index=i)
        if normalized:
            issues.append(normalized)

    return {
        "id": str(raw.get("id") or f"epic-{index}").strip(),
        "title": title,
        "description": description,
        "issues": issues,
    }


def _normalize_breakdown(parsed: dict[str, Any]) -> dict[str, Any]:
    epics_in = parsed.get("epics") or parsed.get("Epics") or []
    if not isinstance(epics_in, list):
        epics_in = []
    epics: list[dict[str, Any]] = []
    for i, item in enumerate(epics_in, start=1):
        epic = _normalize_epic(item, index=i)
        if epic:
            epics.append(epic)
    return {"epics": epics}


def _fallback_breakdown(
    *,
    spec: dict[str, Any],
    prd_text: str,
    sdd_text: str,
    reason: str,
) -> dict[str, Any]:
    label = pipeline_label(spec)
    stack_hint = "stack do SDD"
    if re.search(r"(?i)react", sdd_text or prd_text):
        stack_hint = "React + API conforme SDD"
    return {
        "epics": [
            {
                "id": "epic-1",
                "title": f"Fundação — {label}",
                "description": (
                    f"Bootstrap do MVP (fallback: {reason}). "
                    "Substituir por breakdown refinado após SDD/PRD completos."
                ),
                "issues": [
                    {
                        "id": "issue-1",
                        "title": "Scaffold do projeto e contratos mínimos",
                        "type": "backend",
                        "description_micro_prompt": (
                            f"Atue como engenheiro. Com base no PRD/SDD de «{label}», "
                            f"crie o scaffold mínimo ({stack_hint}): estrutura de pastas, "
                            "config de ambiente e um healthcheck. Não implemente features "
                            "de negócio ainda. Critério de pronto: app sobe localmente e "
                            "responde health OK."
                        ),
                        "dependencies": [],
                    },
                    {
                        "id": "issue-2",
                        "title": "Primeira tela/fluxo MVP",
                        "type": "frontend",
                        "description_micro_prompt": (
                            f"Implemente a primeira jornada MVP de «{label}» na UI "
                            f"({stack_hint}). Use apenas o necessário do SDD. "
                            "Critério de pronto: fluxo principal clicável end-to-end "
                            "com dados mock se a API ainda não existir."
                        ),
                        "dependencies": ["Scaffold do projeto e contratos mínimos"],
                    },
                ],
            }
        ]
    }


def _build_user_prompt(
    *,
    prd_text: str,
    sdd_text: str,
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
    prd_phase_id: Optional[str],
    sdd_phase_id: Optional[str],
) -> str:
    descricao = phase_description(
        cfg,
        fallback=(
            "Ler PRD e SDD e fatiar o MVP em Epics e Issues atômicas, "
            "com micro-prompts copiáveis para o agente de código."
        ),
    )
    deps = resolve_depends_on(spec, phase_id)
    pedido = str(
        spec.get("user_prompt") or spec.get("description") or pipeline_label(spec)
    ).strip()

    return f"""
Pipeline: {pipeline_label(spec)}
Fase: {cfg.get("name") or phase_id}
depends_on: {", ".join(deps) or "nenhuma"}
Fontes: PRD={prd_phase_id or "?"} | SDD={sdd_phase_id or "?"}

Pedido original:
{pedido}

Instruções da fase:
{descricao}

REGRA DE IDIOMA: Todo o conteúdo gerado, especialmente o campo
`description_micro_prompt`, DEVE ser escrito estritamente em Português do Brasil
(PT-BR). Mantenha em inglês apenas nomes de tecnologias ou variáveis literais.

=== PRD (contexto) ===
{prd_text or "(PRD ausente — derive com cautela do SDD/pedido)"}

=== SDD (fonte primária de arquitetura) ===
{sdd_text or "(SDD ausente — derive do PRD; declare hipóteses no micro-prompt)"}

Produza o JSON com a chave "epics" no schema exigido — todo texto narrativo em PT-BR.
""".strip()


def _generate_breakdown_safe(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    prd_text, sdd_text, prd_id, sdd_id = _pick_prd_sdd(inputs)
    errors: list[str] = []
    meta: dict[str, Any] = {
        "prd_phase_id": prd_id,
        "sdd_phase_id": sdd_id,
    }

    attempts = [
        (True, 0.25, 8192),
        (True, 0.2, 6144),
        (False, 0.15, 4096),
    ]
    for as_json, temperature, max_tokens in attempts:
        prompt = _build_user_prompt(
            prd_text=prd_text,
            sdd_text=sdd_text,
            spec=spec,
            phase_id=phase_id,
            cfg=cfg,
            prd_phase_id=prd_id,
            sdd_phase_id=sdd_id,
        )
        try:
            raw_text, call_meta = generate_content(
                prompt,
                system_instruction=_SYSTEM_INSTRUCTION,
                enable_google_search=False,
                response_json=as_json,
                response_schema=TASK_BREAKDOWN_RESPONSE_SCHEMA if as_json else None,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            meta = {**meta, **(call_meta or {})}
            parsed = extract_json_payload(raw_text)
            if isinstance(parsed, dict):
                normalized = _normalize_breakdown(parsed)
                if normalized.get("epics"):
                    return normalized, {
                        **meta,
                        "attempts": errors,
                        "used_max_output_tokens": max_tokens,
                    }
            errors.append(f"sem_epics(tokens={max_tokens})")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    return (
        _fallback_breakdown(
            spec=spec,
            prd_text=prd_text,
            sdd_text=sdd_text,
            reason="; ".join(errors) or "modelo indisponível",
        ),
        {**meta, "fallback": True, "attempts": errors},
    )


async def execute_phase_task_breakdown(
    run_id: str,
    spec: dict[str, Any],
    db_session: Optional[Session] = None,
    phase_id: str = "task_breakdown",
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
                    "Aprove PRD/SDD (depends_on) antes do task_breakdown."
                )
            parsed, meta = await asyncio.to_thread(
                _generate_breakdown_safe, inputs, spec, phase_id, cfg
            )
            return {
                "status": "success",
                "phase": phase_id,
                "capability": "task_breakdown",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": parsed,
                "epics": parsed.get("epics"),
                "inputs_used": list(inputs.keys()),
                "meta": meta,
            }
        except Exception as exc:
            try:
                inputs = load_dependency_artifacts(session, run_id, spec, phase_id) or {}
            except Exception:
                inputs = {}
            prd_text, sdd_text, _, _ = _pick_prd_sdd(inputs)
            if inputs:
                parsed = _fallback_breakdown(
                    spec=spec,
                    prd_text=prd_text,
                    sdd_text=sdd_text,
                    reason=str(exc),
                )
                return {
                    "status": "success",
                    "phase": phase_id,
                    "capability": "task_breakdown",
                    "run_id": run_id,
                    "pipeline_name": pipeline_label(spec),
                    "artifact_data": parsed,
                    "epics": parsed.get("epics"),
                    "inputs_used": list(inputs.keys()),
                    "meta": {"fallback": True, "error": str(exc)},
                }
            return {
                "status": "error",
                "phase": phase_id,
                "capability": "task_breakdown",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": {"erro": str(exc), "epics": []},
            }
    finally:
        if owns_session:
            session.close()


class TaskBreakdownPhase:
    """Fachada alinhada ao nome da capability (handlers reais são funções async)."""

    capability = "task_breakdown"

    @staticmethod
    async def execute(
        run_id: str,
        spec: dict[str, Any],
        db_session: Optional[Session] = None,
        phase_id: str = "task_breakdown",
    ) -> dict[str, Any]:
        return await execute_phase_task_breakdown(
            run_id, spec, db_session=db_session, phase_id=phase_id
        )
