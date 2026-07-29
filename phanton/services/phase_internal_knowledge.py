"""Capability: context7_search — memoria organizacional (RAG) via provider plugavel.

Contrato de artefato (L3 / UI): search_keywords, context7_hits[], source.
Origem dos hits: CONTEXT7_PROVIDER=mock|http|pgvector (default mock).
"""

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
from services.context7 import (  # noqa: E402
    get_context7_provider,
    get_context7_top_k,
)
from services.context7.fallback import (  # noqa: E402
    build_fallback_result,
    extract_keywords_from_text,
)
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


def _artifact_from_result(result: Any) -> dict[str, Any]:
    return {
        "search_keywords": list(result.keywords or []),
        "context7_hits": result.hits_as_dicts(),
        "source": result.source,
    }


def _search_via_provider(
    challenge: str,
    *,
    top_k: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    keywords = extract_keywords_from_text(challenge)
    provider = get_context7_provider()
    result = provider.search(
        keywords,
        top_k=top_k,
        filtros=None,
        challenge=challenge,
    )
    parsed = _artifact_from_result(result)
    meta = {
        **(result.meta or {}),
        "provider": getattr(provider, "name", type(provider).__name__),
    }
    return parsed, meta


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
    top_k = get_context7_top_k(2)

    try:
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

        try:
            parsed, meta = await asyncio.to_thread(
                _search_via_provider, challenge, top_k=top_k
            )
        except Exception as exc:
            fb = build_fallback_result(
                challenge, reason=str(exc), top_k=top_k
            )
            parsed = _artifact_from_result(fb)
            meta = {**(fb.meta or {}), "fallback": True, "error": str(exc)}

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
        fallback = build_fallback_result(
            _challenge_text(spec, cfg), reason=str(exc), top_k=top_k
        )
        parsed = _artifact_from_result(fallback)
        return {
            "status": "success",
            "phase": phase_id,
            "capability": "context7_search",
            "run_id": run_id,
            "pipeline_name": pipeline_label(spec),
            "artifact_data": parsed,
            "context7_hits": parsed.get("context7_hits"),
            "search_keywords": parsed.get("search_keywords"),
            "meta": {"fallback": True, "error": str(exc)},
        }
    finally:
        if owns_session:
            session.close()
