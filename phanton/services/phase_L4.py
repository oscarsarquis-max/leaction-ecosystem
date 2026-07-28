"""Capability: prompt/delivery — entrega final solicitada pelo usuário (não um prompt de IDE)."""

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

_MAX_INPUT_CHARS = 72_000

_PRESENTATION_RE = re.compile(
    r"\b(apresenta[cç][aã]o|slides?|pitch|deck|powerpoint|keynote|slide\s*deck)\b",
    re.I,
)
_HTML_DOC_RE = re.compile(r"^\s*(<!DOCTYPE\s+html|<html\b)", re.I)

_INTERACT_STYLE_MARKER = 'data-phanton-interact="1"'
_TAB_SCRIPT_MARKER = 'data-phanton-tabs="1"'
_INTERACT_STYLE_BLOCK = f"""
<style {_INTERACT_STYLE_MARKER}>
/* Phanton: overlays decorativos não roubam clique; controles sempre clicáveis */
body::before, body::after, html::before, html::after {{
  pointer-events: none !important;
}}
.overlay, .backdrop, .bg-overlay, .background-overlay, .hero-overlay,
.glow, .particles, .bg-layer, [aria-hidden="true"] {{
  pointer-events: none !important;
}}
button, a, input, select, textarea, summary,
[role="button"], [onclick], [tabindex]:not([tabindex="-1"]),
nav, .btn, .card, .tab, .nav-btn, .axis-card, .method-card, .tab-btn {{
  pointer-events: auto !important;
  position: relative;
  z-index: 5;
  cursor: pointer;
}}
.tab-content.hidden {{ display: none !important; }}
.tab-content.block {{ display: block !important; }}
.tab-btn.is-active, .tab-btn[aria-selected="true"] {{
  background: #fff !important;
  color: #0369a1 !important;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}}
</style>
""".strip()

_TAB_SWITCH_SCRIPT = f"""
<script {_TAB_SCRIPT_MARKER}>
(function () {{
  function switchTab(id) {{
    var key = String(id || "");
    document.querySelectorAll(".tab-content").forEach(function (el) {{
      var match =
        el.id === "content-" + key ||
        el.id === "panel-" + key ||
        el.getAttribute("data-tab") === key;
      el.classList.toggle("hidden", !match);
      el.classList.toggle("block", !!match);
      el.hidden = !match;
    }});
    document.querySelectorAll(".tab-btn, [data-tab-target]").forEach(function (btn) {{
      var btnKey =
        (btn.getAttribute("data-tab-target") || "") ||
        String(btn.id || "").replace(/^tab-/, "");
      var active = btnKey === key;
      btn.setAttribute("aria-selected", active ? "true" : "false");
      btn.classList.toggle("is-active", active);
    }});
  }}
  window.switchTab = switchTab;
  window.showSlide = window.showSlide || function (n) {{
    var slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));
    if (!slides.length) return;
    var i = ((n % slides.length) + slides.length) % slides.length;
    slides.forEach(function (s, idx) {{ s.classList.toggle("active", idx === i); }});
  }};
}})();
</script>
""".strip()

_HTML_INTERACTIVITY_RULES = """
INTERATIVIDADE (obrigatório — cliques DEVEM funcionar)
- Qualquer camada decorativa (gradient, ::before/::after, .overlay, backdrop)
  com position fixed/absolute cobrindo a tela DEVE ter pointer-events: none.
- NÃO cubra botões/cards com um div transparente full-screen.
- Controles clicáveis (botões, cards, tabs, nav) com cursor:pointer e
  listeners reais (click / keydown). Ao clicar, a UI DEVE mudar (painel,
  slide, seção ativa, etc.).
- Evite pointer-events: none em containers que envolvem botões.
- A página deve funcionar isolada (arquivo único), preferindo CSS/JS inline
  (sem CDN). Se usar onclick="foo()", a function foo DEVE existir no HTML.
- OBRIGATÓRIO: HTML completo até </body></html>. Nunca corte no meio de uma tag.
- Prefira página enxuta e 100% funcional a página longa e truncada.
"""


def _html_is_truncated(html: str) -> bool:
    text = html or ""
    if not _HTML_DOC_RE.match(text):
        return False
    if not re.search(r"</html\s*>", text, flags=re.I):
        return True
    called = set(re.findall(r"""\bonclick\s*=\s*["']\s*([A-Za-z_][\w]*)\s*\(""", text))
    defined = set(re.findall(r"\bfunction\s+([A-Za-z_][\w]*)\s*\(", text))
    defined |= set(
        re.findall(r"\b(?:const|let|var)\s+([A-Za-z_][\w]*)\s*=\s*(?:async\s*)?function", text)
    )
    defined |= set(re.findall(r"\b(?:const|let|var)\s+([A-Za-z_][\w]*)\s*=\s*(?:async\s*)?\(", text))
    return bool(called - defined)


def _close_truncated_html(html: str) -> str:
    text = html or ""
    if re.search(r"</html\s*>", text, flags=re.I):
        return text
    open_divs = len(re.findall(r"<div\b", text, flags=re.I)) - len(
        re.findall(r"</div\s*>", text, flags=re.I)
    )
    open_divs = max(0, min(open_divs, 60))
    parts = [text.rstrip()]
    if open_divs:
        parts.append("\n" + ("</div>\n" * open_divs))
    if not re.search(r"</body\s*>", text, flags=re.I):
        parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts)


def _inject_before_body_end(html: str, snippet: str) -> str:
    if re.search(r"</body\s*>", html, flags=re.I):
        return re.sub(
            r"</body\s*>",
            snippet + "\n</body>",
            html,
            count=1,
            flags=re.I,
        )
    if re.search(r"</html\s*>", html, flags=re.I):
        return re.sub(
            r"</html\s*>",
            snippet + "\n</html>",
            html,
            count=1,
            flags=re.I,
        )
    return html.rstrip() + "\n" + snippet + "\n"


def _inject_style_block(html: str, style_block: str, marker: str) -> str:
    if marker in html:
        return html
    if re.search(r"</head\s*>", html, flags=re.I):
        return re.sub(
            r"</head\s*>",
            style_block + "\n</head>",
            html,
            count=1,
            flags=re.I,
        )
    if re.search(r"<body\b", html, flags=re.I):
        return re.sub(
            r"<body\b([^>]*)>",
            lambda m: f"<body{m.group(1)}>\n{style_block}",
            html,
            count=1,
            flags=re.I,
        )
    return style_block + "\n" + html


def _ensure_html_clickable(html: str) -> str:
    """Fecha HTML truncado, injeta switchTab se faltar e CSS anti-overlay."""
    text = (html or "").strip()
    if not text or not _HTML_DOC_RE.match(text):
        return text

    text = _close_truncated_html(text)

    needs_tabs = (
        "switchTab(" in text
        and "function switchTab" not in text
        and f"{_TAB_SCRIPT_MARKER}" not in text
    ) or (
        bool(re.search(r"""\bonclick\s*=\s*["']\s*switchTab\s*\(""", text))
        and f"{_TAB_SCRIPT_MARKER}" not in text
    )
    if needs_tabs:
        text = _inject_before_body_end(text, _TAB_SWITCH_SCRIPT)

    return _inject_style_block(text, _INTERACT_STYLE_BLOCK, _INTERACT_STYLE_MARKER)


def _compact_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    serialized = json.dumps(inputs, ensure_ascii=False, default=str)
    if len(serialized) <= _MAX_INPUT_CHARS:
        return inputs

    compact: dict[str, Any] = {}
    budget = _MAX_INPUT_CHARS // max(len(inputs), 1)
    for key, value in inputs.items():
        chunk = json.dumps(value, ensure_ascii=False, default=str)
        if len(chunk) > budget:
            compact[key] = chunk[:budget] + "\n…[truncado]"
        else:
            compact[key] = value
    return compact


def _user_request(spec: dict[str, Any], cfg: dict[str, Any]) -> str:
    parts = [
        str(spec.get("description") or "").strip(),
        str(spec.get("user_prompt") or spec.get("pedido") or "").strip(),
        phase_description(cfg, fallback=""),
        str(cfg.get("name") or "").strip(),
    ]
    return "\n".join(p for p in parts if p)


def _wants_presentation(spec: dict[str, Any], cfg: dict[str, Any]) -> bool:
    blob = _user_request(spec, cfg)
    return bool(_PRESENTATION_RE.search(blob))


def _strip_tool_mentions(text: str) -> str:
    """Remove menções a IDEs/ferramentas de código no texto final.

    Não altera CSS (`cursor: pointer`) nem atributos HTML genéricos.
    """
    cleaned = text or ""
    patterns = [
        r"(?i)\bcursor\s*ide\b",
        r"(?i)\bno\s+cursor\b",
        r"(?i)\bpara\s+o\s+cursor\b",
        r"(?i)\bao\s+cursor\b",
        # Evita quebrar CSS: só "Cursor" como produto/marca (maiúscula ou contexto IDE)
        r"(?<![.\w-])(?i:Cursor)(?!\s*:)",
        r"(?i)\bvs\s*code\b",
        r"(?i)\bvisual\s+studio\s+code\b",
        r"(?i)\bcopilot\b",
        r"(?i)\bwindsurf\b",
        r"(?i)\bclaude\s+code\b",
    ]
    for pat in patterns:
        cleaned = re.sub(pat, "assistente de implementação", cleaned)
    # Títulos legados
    cleaned = re.sub(
        r"(?im)^#\s*Prompt para implementação no Cursor\s*$",
        "# Entrega final",
        cleaned,
    )
    cleaned = re.sub(
        r"(?im)^##\s*14\.\s*Primeira mensagem sugerida ao Cursor\s*$",
        "## 14. Próximos passos sugeridos",
        cleaned,
    )
    cleaned = re.sub(
        r"(?im)^##\s*9\.\s*Plano de implementação step-by-step \(para o Cursor executar\)\s*$",
        "## 9. Plano de implementação step-by-step",
        cleaned,
    )
    cleaned = re.sub(
        r"(?im)^##\s*4\.\s*Instruções Step-by-step para o Cursor\s*$",
        "## 4. Plano step-by-step",
        cleaned,
    )
    return cleaned


def _build_delivery_prompt(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> str:
    inputs_json = json.dumps(inputs, ensure_ascii=False, indent=2, default=str)
    pedido = _user_request(spec, cfg) or phase_description(
        cfg,
        fallback="Produzir a entrega final solicitada pelo usuário.",
    )
    deps = resolve_depends_on(spec, phase_id)
    pipeline = pipeline_label(spec)
    fase_nome = cfg.get("name") or phase_id
    presentation = _wants_presentation(spec, cfg)

    if presentation:
        format_rules = f"""
FORMATO DA ENTREGA (apresentação)
- Produza uma APRESENTAÇÃO COMPLETA e utilizável agora — NÃO um prompt, NÃO um roteiro
  para outra ferramenta gerar os slides.
- Preferência forte: um único documento HTML autocontido (<!DOCTYPE html>…</html>)
  com slides navegáveis (teclado/setas ou botões), tipografia legível e layout clean.
- Inclua JavaScript inline funcional (navegação entre slides, botões, teclado).
  A interatividade DEVE funcionar ao abrir o arquivo/HTML isolado.
{_HTML_INTERACTIVITY_RULES}
- Inclua título, seções/slides com conteúdo real (não placeholders tipo “Slide 1…”).
- Use o material das fases anteriores como fonte da verdade (metodologia, pesquisas, síntese).
- Idioma: português do Brasil.
- NÃO cite ferramentas de IDE (Cursor, VS Code, Copilot, etc.).
- NÃO diga “cole isto em…” / “use o seguinte prompt…”.
- ÚNICA saída: o HTML completo (ou Markdown de slides se HTML for impossível).
  Sem prefácio (“claro,” “aqui está”).
"""
    else:
        format_rules = f"""
FORMATO DA ENTREGA
- Produza a ENTREGA FINAL pedida pelo usuário — o artefato em si, pronto para uso.
- NÃO produza um “prompt para implementar depois”.
- NÃO produza meta-instruções do tipo “abra a ferramenta X e cole…”.
- Escolha o formato mais adequado ao pedido:
  • documento / plano / roteiro → Markdown completo
  • página / protótipo visual → HTML autocontido (CSS+JS inline)
  • checklist / playbook → Markdown estruturado
- Se a entrega for HTML interativo: JavaScript real para clique/navegação.
{_HTML_INTERACTIVITY_RULES}
- Conteúdo denso e específico; incorpore pesquisas e síntese.
- Idioma: português do Brasil.
- NÃO cite ferramentas de IDE (Cursor, VS Code, Copilot, etc.).
- ÚNICA saída: o artefato final. Sem prefácio.
"""

    return f"""
Você é um especialista sênior em entrega de produtos de conhecimento e soluções.

MISSÃO
O pipeline Phanton já produziu metodologia, pesquisas e síntese.
Sua tarefa é GERAR A ENTREGA FINAL pedida pelo usuário — o resultado concreto,
não um intermediário.

PEDIDO ORIGINAL DO USUÁRIO (obrigatório honrar isto):
{pedido}

CONTEXTO DO PIPELINE
- Nome: {pipeline}
- Fase de entrega: {fase_nome}
- depends_on / entradas: {", ".join(deps) or "nenhuma"}

=== ARTEFATOS DAS FASES ANTERIORES (fonte da verdade) ===
{inputs_json}

{format_rules}

Comece AGORA na primeira linha do artefato final.
""".strip()


def _strip_outer_fence(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned.startswith("```"):
        return cleaned
    lines = cleaned.splitlines()
    if lines:
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _dict_to_delivery(data: dict[str, Any]) -> str:
    preferred_keys = (
        "delivery",
        "entrega",
        "html_code",
        "html",
        "presentation",
        "apresentacao",
        "markdown",
        "documento",
        "content",
        "texto",
        "prompt",
        "cursor_prompt",
    )
    for key in preferred_keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            nested = _dict_to_delivery(value)
            if nested:
                return nested

    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def coerce_to_delivery(raw_text: str) -> str:
    """Normaliza a resposta do modelo para o artefato final (HTML ou Markdown)."""
    text = _strip_tool_mentions(_strip_outer_fence(raw_text))
    if not text:
        raise ValueError("Resposta vazia na fase de entrega")

    current: Any = text
    for _ in range(4):
        if isinstance(current, dict):
            md = _dict_to_delivery(current)
            return _strip_tool_mentions(_strip_outer_fence(md))

        if not isinstance(current, str):
            current = json.dumps(current, ensure_ascii=False, indent=2, default=str)

        candidate = _strip_tool_mentions(_strip_outer_fence(current)).strip()
        if _HTML_DOC_RE.match(candidate):
            return candidate
        if candidate.startswith("#") or re.search(r"^##\s+", candidate, re.M):
            if not candidate.lstrip().startswith("{"):
                return candidate

        if candidate.lstrip().startswith("{") or candidate.lstrip().startswith("["):
            try:
                current = extract_json_payload(candidate)
                continue
            except Exception:
                return candidate

        if candidate:
            return candidate
        return candidate

    if isinstance(current, str) and current.strip():
        return _strip_tool_mentions(current.strip())
    raise ValueError("Não foi possível converter a resposta em entrega final")


def _package_delivery(content: str) -> dict[str, Any]:
    cleaned = _strip_tool_mentions((content or "").strip())
    is_html = bool(_HTML_DOC_RE.match(cleaned))
    if is_html:
        cleaned = _ensure_html_clickable(cleaned)
    package: dict[str, Any] = {
        "delivery": cleaned,
        "format": "html" if is_html else "markdown",
    }
    if is_html:
        package["html_code"] = cleaned
    else:
        # Compat UI antiga que lia cursor_prompt como Markdown
        package["cursor_prompt"] = cleaned
    return package


def _success_payload(
    *,
    run_id: str,
    phase_id: str,
    spec: dict[str, Any],
    package: dict[str, Any],
    inputs: dict[str, Any],
    meta: dict[str, Any],
) -> dict[str, Any]:
    """Monta resposta da fase: HTML → html_code; Markdown → delivery (sem forçar cursor_prompt no topo)."""
    payload: dict[str, Any] = {
        "status": "success",
        "phase": phase_id,
        "capability": "prompt",
        "run_id": run_id,
        "pipeline_name": pipeline_label(spec),
        "delivery": package["delivery"],
        "format": package.get("format") or "markdown",
        "artifact_data": package,
        "inputs_used": list(inputs.keys()),
        "meta": meta,
    }
    if package.get("format") == "html" and package.get("html_code"):
        payload["html_code"] = package["html_code"]
    elif package.get("cursor_prompt"):
        # Só em Markdown: campo legado para UIs antigas
        payload["cursor_prompt"] = package["cursor_prompt"]
    return payload


def _call_gemini_prompt(
    prompt: str,
    *,
    max_output_tokens: int = 8192,
    temperature: float = 0.4,
) -> tuple[str, dict[str, Any]]:
    return generate_content(
        prompt,
        enable_google_search=False,
        response_json=False,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )


def _fallback_delivery_from_inputs(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
    *,
    reason: str,
) -> str:
    deps = resolve_depends_on(spec, phase_id)
    pedido = _user_request(spec, cfg) or (spec.get("description") or pipeline_label(spec))
    body = json.dumps(inputs, ensure_ascii=False, indent=2, default=str)
    if len(body) > 24_000:
        body = body[:24_000] + "\n…[truncado]"

    if _wants_presentation(spec, cfg):
        # HTML mínimo navegável a partir dos artefatos (fallback)
        safe_title = (
            str(spec.get("name") or "Apresentação")
            .replace("<", "")
            .replace(">", "")[:80]
        )
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title}</title>
  <style>
    :root {{ font-family: system-ui, sans-serif; color: #0f172a; }}
    body {{ margin: 0; background: #0f172a; }}
    .slide {{
      min-height: 100vh; box-sizing: border-box; padding: 8vh 10vw;
      background: linear-gradient(160deg, #fff7ed, #ffedd5 55%, #fed7aa);
      display: none; flex-direction: column; justify-content: center;
    }}
    .slide.active {{ display: flex; }}
    h1 {{ font-size: clamp(1.8rem, 4vw, 3rem); margin: 0 0 1rem; }}
    h2 {{ font-size: clamp(1.3rem, 3vw, 2rem); margin: 0 0 .75rem; }}
    p, li {{ font-size: clamp(1rem, 2vw, 1.25rem); line-height: 1.5; }}
    nav {{
      position: fixed; bottom: 1rem; right: 1rem; display: flex; gap: .5rem;
    }}
    button {{
      border: 0; border-radius: .75rem; padding: .6rem 1rem; font-weight: 700;
      background: #ea580c; color: white; cursor: pointer;
    }}
    .note {{ opacity: .75; font-size: .85rem; }}
    pre {{
      white-space: pre-wrap; background: rgba(255,255,255,.7);
      border-radius: .75rem; padding: 1rem; max-height: 45vh; overflow: auto;
      font-size: .8rem;
    }}
  </style>
</head>
<body>
  <section class="slide active">
    <h1>{safe_title}</h1>
    <p>{pedido}</p>
    <p class="note">Gerado em modo fallback ({reason}). Use as setas ou os botões para navegar.</p>
  </section>
  <section class="slide">
    <h2>Contexto do pipeline</h2>
    <p>Pipeline: <strong>{pipeline_label(spec)}</strong></p>
    <p>Fase: <strong>{cfg.get("name") or phase_id}</strong></p>
    <p>Entradas: {", ".join(deps) or "fases anteriores"}</p>
  </section>
  <section class="slide">
    <h2>Material das fases anteriores</h2>
    <pre>{body.replace("<", "&lt;")}</pre>
  </section>
  <nav>
    <button type="button" id="prev">Anterior</button>
    <button type="button" id="next">Próximo</button>
  </nav>
  <script>
    const slides = [...document.querySelectorAll('.slide')];
    let i = 0;
    function show(n) {{
      i = (n + slides.length) % slides.length;
      slides.forEach((s, idx) => s.classList.toggle('active', idx === i));
    }}
    document.getElementById('prev').onclick = () => show(i - 1);
    document.getElementById('next').onclick = () => show(i + 1);
    window.addEventListener('keydown', (e) => {{
      if (e.key === 'ArrowRight' || e.key === 'PageDown') show(i + 1);
      if (e.key === 'ArrowLeft' || e.key === 'PageUp') show(i - 1);
    }});
  </script>
</body>
</html>
""".strip()

    return f"""# Entrega final

## Pedido atendido
{pedido}

## Pipeline
- Nome: **{pipeline_label(spec)}**
- Fase: **{cfg.get("name") or phase_id}**
- Entradas: {", ".join(deps) or "fases anteriores"}

> Nota: entrega gerada em modo fallback ({reason}). O conteúdo abaixo consolida
> os artefatos das fases anteriores na forma de entrega utilizável.

## Conteúdo consolidado

```json
{body}
```

## Próximos passos
1. Revisar os pontos da síntese e das pesquisas acima.
2. Transformar os requisitos em ações concretas no seu fluxo de trabalho.
3. Validar com stakeholders antes de expandir o escopo.
""".strip()


def _generate_delivery_safe(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    meta: dict[str, Any] = {}
    errors: list[str] = []

    attempts = [
        (_compact_inputs(inputs), 16384, 0.3),
        (_compact_inputs(inputs), 8192, 0.25),
    ]
    tiny: dict[str, Any] = {}
    for key, value in inputs.items():
        chunk = json.dumps(value, ensure_ascii=False, default=str)
        tiny[key] = chunk[:6000] + ("…[truncado]" if len(chunk) > 6000 else "")
    attempts.append((tiny, 8192, 0.2))

    for compact, max_tokens, temperature in attempts:
        prompt = _build_delivery_prompt(compact, spec, phase_id, cfg)
        try:
            raw_text, meta = _call_gemini_prompt(
                prompt,
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
            if not (raw_text or "").strip():
                errors.append(f"vazio(tokens={max_tokens})")
                continue
            try:
                delivery = coerce_to_delivery(raw_text)
            except Exception as coerce_exc:
                errors.append(f"coerce:{type(coerce_exc).__name__}: {coerce_exc}")
                stripped = _strip_tool_mentions((raw_text or "").strip())
                if _HTML_DOC_RE.match(stripped) or stripped.startswith("#"):
                    delivery = stripped
                else:
                    continue
            if delivery and delivery.strip():
                # HTML cortado no meio (sem </html> / sem funções onclick) → tenta de novo
                if _HTML_DOC_RE.match(delivery) and _html_is_truncated(delivery):
                    errors.append(f"html_truncado(tokens={max_tokens})")
                    # ainda assim guarda o melhor candidato para repair no package
                    meta = {
                        **meta,
                        "attempts": errors,
                        "used_max_output_tokens": max_tokens,
                        "delivery_format": "html",
                        "html_truncated_before_repair": True,
                    }
                    # se for a última tentativa, aceita e repara; senão continua
                    if (compact, max_tokens, temperature) != attempts[-1]:
                        continue
                meta = {
                    **meta,
                    "attempts": errors,
                    "used_max_output_tokens": max_tokens,
                    "delivery_format": "html"
                    if _HTML_DOC_RE.match(delivery)
                    else "markdown",
                }
                return delivery.strip(), meta
            errors.append(f"coerce_vazio(tokens={max_tokens})")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    fallback = _fallback_delivery_from_inputs(
        inputs,
        spec,
        phase_id,
        cfg,
        reason="; ".join(errors) or "modelo indisponível",
    )
    return fallback, {
        **meta,
        "fallback": True,
        "attempts": errors,
        "model": meta.get("model") or resolve_model_safe(),
        "delivery_format": "html" if _HTML_DOC_RE.match(fallback) else "markdown",
    }


def resolve_model_safe() -> str:
    try:
        from services.gemini_client import resolve_model

        return resolve_model()
    except Exception:
        return "unknown"


async def execute_phase_L4(
    run_id: str,
    spec: dict[str, Any],
    db_session: Optional[Session] = None,
    phase_id: str = "entrega_final",
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
                    f"Nenhum artefato de entrada encontrado para '{phase_id}'. "
                    "Aprove as fases anteriores antes de gerar a entrega final."
                )

            delivery, meta = await asyncio.to_thread(
                _generate_delivery_safe,
                inputs,
                spec,
                phase_id,
                cfg,
            )
            package = _package_delivery(delivery)
            return _success_payload(
                run_id=run_id,
                phase_id=phase_id,
                spec=spec,
                package=package,
                inputs=inputs,
                meta=meta,
            )
        except Exception as exc:
            try:
                inputs = load_dependency_artifacts(session, run_id, spec, phase_id) or {}
            except Exception:
                inputs = {}
            if inputs:
                delivery = _fallback_delivery_from_inputs(
                    inputs, spec, phase_id, cfg, reason=str(exc)
                )
                package = _package_delivery(delivery)
                return _success_payload(
                    run_id=run_id,
                    phase_id=phase_id,
                    spec=spec,
                    package=package,
                    inputs=inputs,
                    meta={"fallback": True, "error": str(exc)},
                )
            return {
                "status": "error",
                "phase": phase_id,
                "capability": "prompt",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": {"erro": str(exc)},
            }
    finally:
        if owns_session:
            session.close()
