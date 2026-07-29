"""Fallback local compartilhado (mesmo texto generico do mock antigo)."""

from __future__ import annotations

import re
from typing import Any

from services.context7.provider_base import Context7SearchResult, Hit


def extract_keywords_from_text(challenge: str, *, limit: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]{4,}", challenge or "")
    keywords: list[str] = []
    seen: set[str] = set()
    for w in words:
        key = w.lower()
        if key in seen:
            continue
        seen.add(key)
        keywords.append(w)
        if len(keywords) >= limit:
            break
    if not keywords:
        return ["SaaS", "educacao", "MVP", "API", "multi-tenant"]
    return keywords


def build_fallback_result(
    challenge: str,
    *,
    reason: str,
    source: str = "context7_mock_fallback",
    keywords: list[str] | None = None,
    top_k: int = 2,
) -> Context7SearchResult:
    kws = list(keywords) if keywords else extract_keywords_from_text(challenge)
    theme = " / ".join(kws[:4])
    hits = [
        Hit(
            titulo=f"PRD historico — Plataforma educacional ({theme})",
            tipo="PRD",
            resumo=(
                "Padrao ouro de produto B2B educacao: personas gestor/professor/aluno, "
                "onboarding freemium, RBAC por instituicao, jornadas de agenda e "
                "acompanhamento de OKRs. Regras: isolamento por tenant, consentimento LGPD, "
                "MVP com creditos de IA e criterios de aceite mensuraveis. "
                f"(mock context7; motivo={reason})"
            ),
            score=0.82,
        ),
        Hit(
            titulo=f"SDD historico — Arquitetura Hub + apps ({theme})",
            tipo="SDD",
            resumo=(
                "Arquitetura em camadas: frontend Vite/React, API Flask/Node, Postgres "
                "compartilhado (Docker), autenticacao via Action Hub, contratos REST "
                "versionados e filas leves para webhooks. Modelo de dados com "
                "instituicoes, usuarios, planos e eventos de agenda. "
                f"(mock context7; motivo={reason})"
            ),
            score=0.8,
        ),
    ]
    return Context7SearchResult(
        hits=hits[: max(1, top_k)],
        keywords=kws,
        source=source,
        meta={"fallback": True, "reason": reason},
    )


def normalize_keyword_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        if raw:
            return [str(raw).strip()] if str(raw).strip() else []
        return []
    return [str(k).strip() for k in raw if str(k).strip()][:12]
