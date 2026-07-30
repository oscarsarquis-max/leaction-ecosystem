"""Provider mock: Gemini inventa keywords + hits (comportamento legado)."""

from __future__ import annotations

from typing import Any, Optional

from services.context7.fallback import (
    build_fallback_result,
    extract_keywords_from_text,
    normalize_keyword_list,
)
from services.context7.provider_base import (
    Context7SearchResult,
    Hit,
    hit_from_mapping,
)
from services.llm.json_utils import extract_json_payload
from services.llm.runtime import generate_content


def _build_keywords_prompt(challenge: str, *, phase_hint: str = "") -> str:
    return f"""
Atue como bibliotecario tecnico da base interna context7 (PRDs e SDDs historicos).

{phase_hint}

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


class MockContext7Provider:
    """Inventa hits via Gemini; fallback local se o modelo falhar."""

    name = "mock"

    def search(
        self,
        keywords: list[str],
        *,
        top_k: int = 2,
        filtros: Optional[dict[str, Any]] = None,
        challenge: str = "",
    ) -> Context7SearchResult:
        _ = filtros  # mock nao filtra por tipo ainda
        text = (challenge or " ".join(keywords)).strip() or "busca generica context7"
        seed_keywords = list(keywords) if keywords else extract_keywords_from_text(text)
        phase_hint = (
            "Instrucoes: Buscar na base interna context7 PRDs e SDDs historicos "
            "similares ao desafio atual."
        )
        if seed_keywords:
            phase_hint += "\nKeywords sugeridas: " + ", ".join(seed_keywords[:12])

        prompt = _build_keywords_prompt(text, phase_hint=phase_hint)
        errors: list[str] = []
        meta: dict[str, Any] = {}

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
                if not isinstance(parsed, dict):
                    errors.append(f"json_invalido(tokens={max_tokens})")
                    continue

                kws = normalize_keyword_list(
                    parsed.get("search_keywords") or parsed.get("keywords")
                )
                if not kws:
                    kws = seed_keywords

                raw_hits = parsed.get("context7_hits") or parsed.get("hits") or []
                if not isinstance(raw_hits, list):
                    raw_hits = []

                hits: list[Hit] = []
                for item in raw_hits[:6]:
                    if isinstance(item, dict):
                        hits.append(hit_from_mapping(item))

                if not hits:
                    errors.append(f"hits_insuficientes(tokens={max_tokens})")
                    continue

                if len(hits) == 1 and top_k >= 2:
                    fb = build_fallback_result(
                        text, reason="completar_segundo_hit", keywords=kws, top_k=2
                    )
                    hits.append(fb.hits[1])

                return Context7SearchResult(
                    hits=hits[: max(1, top_k)],
                    keywords=kws,
                    source="context7_mock",
                    meta={
                        **meta,
                        "attempts": errors,
                        "used_max_output_tokens": max_tokens,
                    },
                )
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")

        return build_fallback_result(
            text,
            reason="; ".join(errors) or "modelo indisponivel",
            source="context7_mock_fallback",
            keywords=seed_keywords,
            top_k=top_k,
        )
