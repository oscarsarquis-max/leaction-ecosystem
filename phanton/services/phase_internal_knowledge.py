"""Capability: context7_search — memoria organizacional (RAG) na base interna context7.

Sem conexao real ao BD ainda: gera keywords via Gemini e simula 2 hits
(PRD + SDD historicos) alinhados ao desafio atual.
"""

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
from services.gemini_client import extract_json_payload, generate_content  # noqa: E402
from services.phase_context import (  # noqa: E402
    load_dependency_artifacts,
    phase_cfg,
    phase_description,
    pipeline_label,
    resolve_depends_on,
)


def _challenge_text(spec: dict[str, Any], cfg: dict[str, Any]) -> str:
    parts = [
        str(spec.get("user_prompt") or "").strip(),
        str(spec.get("description") or "").strip(),
        phase_description(cfg, fallback=""),
        str(cfg.get("name") or "").strip(),
    ]
    return "\n".join(p for p in parts if p)


def _build_keywords_prompt(
    challenge: str,
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> str:
    descricao = phase_description(
        cfg,
        fallback=(
            "Buscar na base interna context7 PRDs e SDDs historicos similares "
            "ao desafio atual."
        ),
    )
    return f"""
Atue como bibliotecario tecnico da base interna context7 (PRDs e SDDs historicos).

Pipeline: {pipeline_label(spec)}
Fase: {cfg.get("name") or phase_id}

Instrucoes da fase:
{descricao}

=== Desafio / pedido atual ===
{challenge[:6000]}

Tarefa:
1) Extraia 5 a 10 keywords de busca (portugues e ingles quando fizer sentido).
2) Simule a consulta a context7 e retorne EXATAMENTE 2 documentos relevantes:
   - 1 fragmento de PRD historico
   - 1 fragmento de SDD historico
   de projetos similares (invente titulos realistas de projetos anteriores do
   ecossistema LeAction / educacao / SaaS B2B, coerentes com as keywords).

Responda APENAS com JSON valido:
{{
  "search_keywords": ["kw1", "kw2"],
  "context7_hits": [
    {{
      "titulo": "string",
      "tipo": "PRD",
      "resumo": "resumo das regras de negocio / jornadas (3-6 frases)",
      "score": 0.0
    }},
    {{
      "titulo": "string",
      "tipo": "SDD",
      "resumo": "resumo da arquitetura / stack / contratos (3-6 frases)",
      "score": 0.0
    }}
  ]
}}
""".strip()


def _normalize_hits(parsed: dict[str, Any]) -> dict[str, Any]:
    keywords = parsed.get("search_keywords") or parsed.get("keywords") or []
    if not isinstance(keywords, list):
        keywords = [str(keywords)] if keywords else []
    keywords = [str(k).strip() for k in keywords if str(k).strip()][:12]

    raw_hits = parsed.get("context7_hits") or parsed.get("hits") or []
    if not isinstance(raw_hits, list):
        raw_hits = []

    hits: list[dict[str, Any]] = []
    for item in raw_hits[:6]:
        if not isinstance(item, dict):
            continue
        tipo = str(item.get("tipo") or item.get("type") or "DOC").strip().upper()
        if tipo not in {"PRD", "SDD", "DOC", "PLAYBOOK", "ADR"}:
            tipo = "DOC"
        try:
            score = float(item.get("score") if item.get("score") is not None else 0.75)
        except (TypeError, ValueError):
            score = 0.75
        hits.append(
            {
                "titulo": str(item.get("titulo") or item.get("title") or "Documento").strip(),
                "tipo": tipo,
                "resumo": str(
                    item.get("resumo")
                    or item.get("summary")
                    or item.get("arquitetura")
                    or ""
                ).strip(),
                "score": max(0.0, min(1.0, score)),
            }
        )

    return {
        "search_keywords": keywords,
        "context7_hits": hits,
        "source": "context7_mock",
    }


def _fallback_hits(challenge: str, *, reason: str) -> dict[str, Any]:
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]{4,}", challenge or "")
    keywords = []
    seen = set()
    for w in words:
        key = w.lower()
        if key in seen:
            continue
        seen.add(key)
        keywords.append(w)
        if len(keywords) >= 8:
            break
    if not keywords:
        keywords = ["SaaS", "educacao", "MVP", "API", "multi-tenant"]

    theme = " / ".join(keywords[:4])
    return {
        "search_keywords": keywords,
        "context7_hits": [
            {
                "titulo": f"PRD historico — Plataforma educacional ({theme})",
                "tipo": "PRD",
                "resumo": (
                    "Padrao ouro de produto B2B educacao: personas gestor/professor/aluno, "
                    "onboarding freemium, RBAC por instituicao, jornadas de agenda e "
                    "acompanhamento de OKRs. Regras: isolamento por tenant, consentimento LGPD, "
                    "MVP com creditos de IA e criterios de aceite mensuraveis. "
                    f"(mock context7; motivo={reason})"
                ),
                "score": 0.82,
            },
            {
                "titulo": f"SDD historico — Arquitetura Hub + apps ({theme})",
                "tipo": "SDD",
                "resumo": (
                    "Arquitetura em camadas: frontend Vite/React, API Flask/Node, Postgres "
                    "compartilhado (Docker), autenticacao via Action Hub, contratos REST "
                    "versionados e filas leves para webhooks. Modelo de dados com "
                    "instituicoes, usuarios, planos e eventos de agenda. "
                    f"(mock context7; motivo={reason})"
                ),
                "score": 0.8,
            },
        ],
        "source": "context7_mock_fallback",
    }


def _search_context7_safe(
    challenge: str,
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    errors: list[str] = []
    meta: dict[str, Any] = {}
    prompt = _build_keywords_prompt(challenge, spec, phase_id, cfg)

    for as_json, temperature, max_tokens in (
        (True, 0.35, 3072),
        (True, 0.2, 2048),
        (False, 0.15, 2048),
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
                normalized = _normalize_hits(parsed)
                if len(normalized.get("context7_hits") or []) >= 1:
                    # Garante 2 hits quando o modelo devolver so 1
                    if len(normalized["context7_hits"]) == 1:
                        fb = _fallback_hits(challenge, reason="completar_segundo_hit")
                        normalized["context7_hits"].append(fb["context7_hits"][1])
                    return normalized, {
                        **meta,
                        "attempts": errors,
                        "used_max_output_tokens": max_tokens,
                    }
            errors.append(f"hits_insuficientes(tokens={max_tokens})")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    return (
        _fallback_hits(challenge, reason="; ".join(errors) or "modelo indisponivel"),
        {**meta, "fallback": True, "attempts": errors},
    )


async def execute_phase_context7_search(
    run_id: str,
    spec: dict[str, Any],
    db_session: Optional[Session] = None,
    phase_id: str = "context7_search",
) -> dict[str, Any]:
    """Handler async da capability context7_search."""
    owns_session = db_session is None
    session = db_session or SessionLocal()
    spec = spec if isinstance(spec, dict) else {}
    cfg = phase_cfg(spec, phase_id)

    try:
        # depends_on opcional (fase inicial); se houver, enriquece o desafio
        try:
            inputs = load_dependency_artifacts(session, run_id, spec, phase_id) or {}
        except Exception:
            inputs = {}

        challenge = _challenge_text(spec, cfg)
        if inputs:
            challenge = (
                challenge
                + "\n\n=== Contexto de fases anteriores ===\n"
                + json.dumps(inputs, ensure_ascii=False, default=str)[:8000]
            )
        if not challenge.strip():
            challenge = f"Pipeline {pipeline_label(spec)} — busca generica context7"

        parsed, meta = await asyncio.to_thread(
            _search_context7_safe, challenge, spec, phase_id, cfg
        )

        return {
            "status": "success",
            "phase": phase_id,
            "capability": "context7_search",
            "run_id": run_id,
            "pipeline_name": pipeline_label(spec),
            "artifact_data": parsed,
            "context7_hits": parsed.get("context7_hits"),
            "search_keywords": parsed.get("search_keywords"),
            "inputs_used": list(inputs.keys()) if inputs else [],
            "depends_on": resolve_depends_on(spec, phase_id),
            "meta": meta,
        }
    except Exception as exc:
        fallback = _fallback_hits(
            _challenge_text(spec, cfg), reason=str(exc)
        )
        return {
            "status": "success",
            "phase": phase_id,
            "capability": "context7_search",
            "run_id": run_id,
            "pipeline_name": pipeline_label(spec),
            "artifact_data": fallback,
            "context7_hits": fallback.get("context7_hits"),
            "search_keywords": fallback.get("search_keywords"),
            "meta": {"fallback": True, "error": str(exc)},
        }
    finally:
        if owns_session:
            session.close()
