"""Capability: prompt — Prompt Engineer para Cursor a partir dos depends_on."""

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


def _build_cursor_prompt(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> str:
    inputs_json = json.dumps(inputs, ensure_ascii=False, indent=2, default=str)
    descricao = phase_description(
        cfg,
        fallback=(
            "Gerar o prompt técnico detalhado e no estado da arte para ser "
            "utilizado no Cursor IDE para a implementação do sistema."
        ),
    )
    deps = resolve_depends_on(spec, phase_id)
    pipeline = pipeline_label(spec)
    fase_nome = cfg.get("name") or phase_id
    spec_resumo = json.dumps(
        {
            "name": spec.get("name"),
            "description": spec.get("description"),
            "version": spec.get("version"),
        },
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    return f"""
Você é um Staff/Principal Engineer e um dos melhores Prompt Engineers do mundo
para IAs codificadoras (Cursor IDE + Claude Sonnet/Opus).

MISSÃO
O pipeline Phanton já investiu esforço real em metodologia, pesquisas e síntese.
Sua tarefa é DESTILAR 100% desse esforço em UM ÚNICO prompt Markdown — o mais
completo, preciso e acionável possível — para o desenvolvedor colar no Cursor
e implementar o sistema SEM alucinar e SEM pedir o que já está decidido.

REGRAS DE SAÍDA (obrigatórias)
- ÚNICA saída: o prompt Markdown final, pronto para colar no Cursor.
- NÃO retorne JSON. NÃO retorne HTML. NÃO escreva prefácio (“claro,” “aqui está”).
- NÃO envolva o documento inteiro em cercas ```.
- Seja denso e específico: prefira requisitos testáveis a frases genéricas.
- NÃO descarte achados das pesquisas nem decisões da síntese — incorpore-os.
- Quando houver tensão entre fontes, escolha a opção mais implementável e diga por quê.
- Idioma: português do Brasil (termos técnicos podem ficar em inglês).

CONTEXTO DO PIPELINE
- Nome: {pipeline}
- Fase de entrega: {fase_nome}
- depends_on / entradas: {", ".join(deps) or "nenhuma"}
- Instrução desta fase: {descricao}

Meta da Spec:
{spec_resumo}

=== ARTEFATOS DAS FASES ANTERIORES (fonte da verdade) ===
{inputs_json}

COMO USAR OS ARTEFATOS
1. Metodologia → princípios, papéis, ritmo, restrições pedagógicas/processuais.
2. Pesquisas/grounding → casos reais, URLs, padrões, libs e práticas a citar.
3. Síntese → plano integrado, cards/passos, requisitos; isso é o backlog principal.
4. Se faltar stack explícita, proponha a MELHOR stack para o caso e justifique
   com base nos artefatos (não invente domínio que contradiga as entradas).

QUALIDADE ESPERADA DO PROMPT (estado da arte)
- Auto-contido: o Cursor não precisa de outro documento.
- Determinístico: nomes de arquivos, endpoints, entidades e contratos explícitos.
- Anti-alucinação: “implemente APENAS o escopo abaixo”; “não invente APIs”.
- Ordem de implementação segura (fundações → domínio → API → UI → testes).
- Exemplos mínimos de payload/schema quando fizer sentido.
- Acessibilidade, offline/baixa conectividade, segurança e DX se o contexto pedir.
- Critérios de aceite verificáveis (checkbox).

ESTRUTURA OBRIGATÓRIA DO MARKDOWN (use estes headings nesta ordem):

# Prompt para implementação no Cursor

## 0. Papel e modo de trabalho
(quem o Cursor deve ser; regras duras: não alucinar, perguntar só se bloqueado,
entregar código completo por arquivo, não omitir imports)

## 1. Objetivo do produto
(1–2 parágrafos + bullets de valor; amarrado à Spec e à síntese)

## 2. Contexto de negócio, usuários e metodologia
(público-alvo, restrições, metodologia/processo vindos das fases anteriores)

## 3. Evidências e referências a preservar
(liste 3–8 achados das pesquisas com título + URL/fonte quando existir, e como
cada um influencia a implementação)

## 4. Escopo
### 4.1 Incluído (MVP)
### 4.2 Explicitamente fora de escopo

## 5. Stack tecnológica e justificativa
(runtime, framework, UI, dados, auth, testes, deploy local; versões se possível)

## 6. Arquitetura
(componentes, fluxos, diagramas em Mermaid se ajudar, decisões-chave)

## 7. Modelo de dados / contratos
(entidades, campos, relações; exemplos JSON de request/response se houver API)

## 8. Estrutura de arquivos esperada
(árvore completa do monorepo/app; indique arquivos críticos)

## 9. Plano de implementação step-by-step (para o Cursor executar)
(passos numerados, pequenos e verificáveis; cada passo diz O QUE criar/alterar
e COMO validar antes do próximo)

## 10. UX / fluxos de tela (se houver frontend)
(rotas, estados vazios/erro/loading, acessibilidade)

## 11. Não-funcionais
(performance, segurança, i18n/pt-BR, offline/baixa conexão, observabilidade)

## 12. Testes e validação
(unit/integration/e2e mínimos; comandos para rodar)

## 13. Critérios de aceite (Definition of Done)
(checklist markdown `- [ ] ...`)

## 14. Primeira mensagem sugerida ao Cursor
(um parágrafo curto que o usuário pode colar junto, dizendo “execute o passo 1”)

Comece AGORA na primeira linha com:
# Prompt para implementação no Cursor
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


def _dict_to_markdown_prompt(data: dict[str, Any]) -> str:
    """Converte JSON estruturado acidental em prompt Markdown utilizável."""
    preferred_keys = (
        "cursor_prompt",
        "prompt",
        "markdown",
        "prompt_markdown",
        "texto",
        "content",
    )
    for key in preferred_keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            nested = _dict_to_markdown_prompt(value)
            if nested:
                return nested

    sections: list[str] = ["# Prompt para implementação no Cursor", ""]
    mapping = [
        (("contexto", "business_context", "metodologia", "context"), "## 1. Contexto de Negócio e Metodologia"),
        (("stack", "tech_stack", "tecnologias"), "## 2. Stack Tecnológico Sugerido"),
        (("estrutura", "file_structure", "arquivos", "estrutura_arquivos"), "## 3. Estrutura de Arquivos Esperada"),
        (("passos", "steps", "step_by_step", "instrucoes"), "## 4. Instruções Step-by-step para o Cursor"),
        (("aceite", "acceptance", "criterios", "definition_of_done"), "## 5. Critérios de Aceite"),
    ]
    used = set()
    for keys, heading in mapping:
        for key in keys:
            if key in data and data[key] not in (None, "", [], {}):
                sections.append(heading)
                sections.append("")
                value = data[key]
                if isinstance(value, str):
                    sections.append(value.strip())
                else:
                    sections.append(
                        json.dumps(value, ensure_ascii=False, indent=2, default=str)
                    )
                sections.append("")
                used.add(key)
                break

    leftovers = {k: v for k, v in data.items() if k not in used and k not in preferred_keys}
    if leftovers and len(sections) <= 2:
        sections.append("## Conteúdo")
        sections.append("")
        sections.append(json.dumps(leftovers, ensure_ascii=False, indent=2, default=str))

    return "\n".join(sections).strip()


def coerce_to_cursor_prompt(raw_text: str) -> str:
    """Garante Markdown de prompt, mesmo se o modelo devolver JSON."""
    text = _strip_outer_fence(raw_text)
    if not text:
        raise ValueError("Resposta vazia ao extrair cursor_prompt")

    current: Any = text
    for _ in range(4):
        if isinstance(current, dict):
            md = _dict_to_markdown_prompt(current)
            if md and not md.lstrip().startswith("{"):
                return md
            # se ainda parece envelope, tenta valores string
            for key in ("cursor_prompt", "prompt", "markdown"):
                if isinstance(current.get(key), str):
                    current = current[key]
                    break
            else:
                return md
            continue

        if not isinstance(current, str):
            current = json.dumps(current, ensure_ascii=False, indent=2, default=str)

        candidate = _strip_outer_fence(current).strip()
        # Parece Markdown de prompt
        if candidate.startswith("#") or re.search(r"^##\s+", candidate, re.M):
            # Ainda pode ser JSON dentro de cerca
            if not candidate.lstrip().startswith("{"):
                return candidate

        if candidate.lstrip().startswith("{") or candidate.lstrip().startswith("["):
            try:
                current = extract_json_payload(candidate)
                continue
            except Exception:
                # JSON quebrado/vazio: devolve o texto bruto como Markdown útil
                return (
                    "# Prompt para implementação no Cursor\n\n"
                    "## Conteúdo gerado\n\n"
                    f"{candidate}"
                )

        # Texto livre (não JSON): é o prompt Markdown esperado
        if candidate:
            return candidate
        return candidate

    if isinstance(current, str) and current.strip():
        return current.strip()
    raise ValueError("Não foi possível converter a resposta em prompt Markdown")


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


def _fallback_prompt_from_inputs(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
    *,
    reason: str,
) -> str:
    """Garante entrega útil mesmo se o Gemini falhar/devolver vazio."""
    deps = resolve_depends_on(spec, phase_id)
    body = json.dumps(inputs, ensure_ascii=False, indent=2, default=str)
    if len(body) > 24_000:
        body = body[:24_000] + "\n…[truncado]"

    return f"""# Prompt para implementação no Cursor

## 0. Papel e modo de trabalho
Atue como Staff Engineer no Cursor IDE. Implemente o sistema descrito abaixo de
forma completa e verificável. Não invente requisitos fora deste documento.
Se algo estiver ambíguo, escolha a opção mais simples e documente a decisão.

> Nota Phanton: prompt gerado em modo fallback ({reason}). Use os artefatos
> das fases anteriores como fonte da verdade.

## 1. Objetivo do produto
{spec.get("description") or pipeline_label(spec)}

## 2. Contexto de negócio, usuários e metodologia
Pipeline: **{pipeline_label(spec)}**
Fase de entrega: **{cfg.get("name") or phase_id}**
Entradas (`depends_on`): {", ".join(deps) or "todas as fases anteriores"}

## 3. Evidências e artefatos das fases anteriores
Use integralmente o material a seguir (metodologia, pesquisas e síntese) para
definir escopo, stack, UX e plano de implementação:

```json
{body}
```

## 4. Escopo
### 4.1 Incluído (MVP)
- Implementar o que a síntese e a metodologia descrevem como entregável principal
- Cobrir fluxos essenciais end-to-end (dados → lógica → interface, se aplicável)

### 4.2 Explicitamente fora de escopo
- Features não mencionadas nos artefatos
- Integrações externas não citadas nas pesquisas/síntese

## 5. Stack tecnológica e justificativa
Escolha a stack mais adequada aos artefatos (preferir FastAPI/React/Postgres
quando o domínio for web; script Python quando for automação). Justifique no README.

## 6. Arquitetura
Separe domínio, API/adapters e UI. Mantenha configuração por `.env` e README com
comandos de setup local.

## 7. Modelo de dados / contratos
Derive entidades e contratos a partir da síntese. Documente schemas e exemplos
mínimos de request/response.

## 8. Estrutura de arquivos esperada
Crie uma árvore clara (`backend/`, `frontend/` ou equivalente) e mantenha
consistência de imports.

## 9. Plano de implementação step-by-step (para o Cursor executar)
1. Scaffold do projeto + README + `.env.example`
2. Modelo de dados / contratos
3. Regras de domínio e serviços
4. API ou interface principal
5. UI (se houver) conectada aos contratos
6. Testes mínimos + checklist de aceite

## 10. UX / fluxos de tela (se houver frontend)
Siga os cards/passos da síntese; estados vazios, loading e erro obrigatórios.

## 11. Não-funcionais
pt-BR, acessibilidade básica, segurança de inputs, e restrições citadas nos
artefatos (ex.: baixa conectividade/offline).

## 12. Testes e validação
Inclua pelo menos testes do fluxo principal e comandos para executar localmente.

## 13. Critérios de aceite (Definition of Done)
- [ ] Setup documentado e executável
- [ ] Fluxo principal funciona de ponta a ponta
- [ ] Contratos/dados alinhados à síntese
- [ ] Testes mínimos passando
- [ ] README com como rodar

## 14. Primeira mensagem sugerida ao Cursor
Execute o passo 1 do plano de implementação deste prompt e pare para eu revisar
antes do passo 2.
""".strip()


def _generate_cursor_prompt_safe(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Tenta Gemini (com retry); se falhar, monta prompt a partir dos artefatos."""
    meta: dict[str, Any] = {}
    errors: list[str] = []

    attempts = [
        (_compact_inputs(inputs), 8192, 0.4),
        (_compact_inputs(inputs), 4096, 0.3),
    ]
    # Terceira tentativa: entradas bem menores
    tiny: dict[str, Any] = {}
    for key, value in inputs.items():
        chunk = json.dumps(value, ensure_ascii=False, default=str)
        tiny[key] = chunk[:6000] + ("…[truncado]" if len(chunk) > 6000 else "")
    attempts.append((tiny, 4096, 0.2))

    for compact, max_tokens, temperature in attempts:
        prompt = _build_cursor_prompt(compact, spec, phase_id, cfg)
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
                cursor_prompt = coerce_to_cursor_prompt(raw_text)
            except Exception as coerce_exc:
                # Nunca propaga JSONDecodeError cru para a UI
                errors.append(f"coerce:{type(coerce_exc).__name__}: {coerce_exc}")
                # Se o modelo já devolveu Markdown, usa direto
                stripped = (raw_text or "").strip()
                if stripped.startswith("#") or re.search(r"^##\s+", stripped, re.M):
                    cursor_prompt = stripped
                else:
                    continue
            if cursor_prompt and cursor_prompt.strip():
                meta = {
                    **meta,
                    "attempts": errors,
                    "used_max_output_tokens": max_tokens,
                }
                return cursor_prompt.strip(), meta
            errors.append(f"coerce_vazio(tokens={max_tokens})")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    fallback = _fallback_prompt_from_inputs(
        inputs,
        spec,
        phase_id,
        cfg,
        reason="; ".join(errors) or "gemini indisponível",
    )
    return fallback, {
        **meta,
        "fallback": True,
        "attempts": errors,
        "model": meta.get("model") or resolve_model_safe(),
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
                    f"Nenhum artefato de entrada encontrado para '{phase_id}'. "
                    "Aprove as fases anteriores antes de gerar o prompt para o Cursor."
                )

            cursor_prompt, meta = await asyncio.to_thread(
                _generate_cursor_prompt_safe,
                inputs,
                spec,
                phase_id,
                cfg,
            )

            return {
                "status": "success",
                "phase": phase_id,
                "capability": "prompt",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "cursor_prompt": cursor_prompt,
                "artifact_data": {"cursor_prompt": cursor_prompt},
                "inputs_used": list(inputs.keys()),
                "meta": meta,
            }
        except Exception as exc:
            # Último recurso: nunca devolver só o erro cru de JSON vazio.
            try:
                inputs = load_dependency_artifacts(session, run_id, spec, phase_id) or {}
            except Exception:
                inputs = {}
            if inputs:
                cursor_prompt = _fallback_prompt_from_inputs(
                    inputs, spec, phase_id, cfg, reason=str(exc)
                )
                return {
                    "status": "success",
                    "phase": phase_id,
                    "capability": "prompt",
                    "run_id": run_id,
                    "pipeline_name": pipeline_label(spec),
                    "cursor_prompt": cursor_prompt,
                    "artifact_data": {"cursor_prompt": cursor_prompt},
                    "inputs_used": list(inputs.keys()),
                    "meta": {"fallback": True, "error": str(exc)},
                }
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
