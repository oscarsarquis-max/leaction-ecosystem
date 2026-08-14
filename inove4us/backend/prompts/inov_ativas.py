"""Prompt canônico — Ranking de Adequação Metodológica (Inov-Ativas).

Arquitetura híbrida: o LLM roteia IDs do catálogo canônico de 39 metodologias
(mesmo do Dia a Dia), escreve ganchos/hipóteses e um trecho do RELATO.
Cards/mecânica detalhada vêm do backend quando houver id_db — nunca inventados no prompt.
"""

from __future__ import annotations

from core.catalogo_metodologias_dia import (
    ETIQUETA_AGILIDADE,
    ETIQUETA_CONTEXTUAIS,
    ETIQUETA_DEDUTIVAS,
    ETIQUETA_INDUTIVAS,
    entradas_catalogo_dia,
)
from core.tom_pedagogico import BLOCO_TOM_PROMPT

_BUCKET_ORDER = (
    ETIQUETA_INDUTIVAS,
    ETIQUETA_AGILIDADE,
    ETIQUETA_CONTEXTUAIS,
    ETIQUETA_DEDUTIVAS,
)

METODOLOGIAS_PERMITIDAS = {
    "indutivas": [],
    "agilidade": [],
    "contextuais": [],
    "dedutivas": [],
}
for _e in entradas_catalogo_dia():
    etq = _e["etiqueta"]
    if etq == ETIQUETA_INDUTIVAS:
        METODOLOGIAS_PERMITIDAS["indutivas"].append(_e["nome"])
    elif etq == ETIQUETA_AGILIDADE:
        METODOLOGIAS_PERMITIDAS["agilidade"].append(_e["nome"])
    elif etq == ETIQUETA_CONTEXTUAIS:
        METODOLOGIAS_PERMITIDAS["contextuais"].append(_e["nome"])
    elif etq == ETIQUETA_DEDUTIVAS:
        METODOLOGIAS_PERMITIDAS["dedutivas"].append(_e["nome"])

LISTA_FLAT = (
    METODOLOGIAS_PERMITIDAS["indutivas"]
    + METODOLOGIAS_PERMITIDAS["agilidade"]
    + METODOLOGIAS_PERMITIDAS["contextuais"]
    + METODOLOGIAS_PERMITIDAS["dedutivas"]
)

IDS_METODOLOGIA_CATALOGO: tuple[str, ...] = tuple(
    e["id"] for e in entradas_catalogo_dia()
)
# Compat: nome antigo usado em testes/scripts
IDS_METODOLOGIA_DB = IDS_METODOLOGIA_CATALOGO

VERBOS_DT_PROIBIDOS = (
    "empatizar",
    "sintetizar",
    "idear",
    "prototipar",
    "definir o problema",
    "testar o protótipo",
)


def _framework_ids_block(
    exclude_ids: set[str] | None = None,
    *,
    candidate_ids: list[str] | None = None,
) -> str:
    """Metodologias disponíveis — formato compacto `id|Nome`.

    Sem `candidate_ids`: catálogo completo permitido (menos bloqueios).
    Com `candidate_ids`: somente esse subconjunto (ainda respeita exclude_ids).
    """
    blocked = {str(x) for x in (exclude_ids or set()) if x}
    by_id = {e["id"]: e for e in entradas_catalogo_dia()}
    ordered_entradas: list[dict] = []
    if candidate_ids is not None:
        seen: set[str] = set()
        for mid in candidate_ids:
            mid = str(mid).strip()
            if not mid or mid in blocked or mid in seen:
                continue
            entrada = by_id.get(mid)
            if not entrada:
                continue
            seen.add(mid)
            ordered_entradas.append(entrada)
    else:
        for entrada in entradas_catalogo_dia():
            if entrada["id"] in blocked:
                continue
            ordered_entradas.append(entrada)

    buckets: dict[str, list[str]] = {k: [] for k in _BUCKET_ORDER}
    for entrada in ordered_entradas:
        etq = entrada["etiqueta"]
        buckets.setdefault(etq, []).append(f"{entrada['id']}|{entrada['nome']}")
    total = sum(len(v) for v in buckets.values())
    linhas = [
        "METODOLOGIAS DISPONÍVEIS",
        f"{total} IDs (escolha só entre estes; não invente):",
    ]
    for cat in _BUCKET_ORDER:
        items = buckets.get(cat) or []
        if not items:
            continue
        if candidate_ids is None:
            items = sorted(items)
        linhas.append(f"{cat}: " + "; ".join(items))
    return "\n".join(linhas)


def _bloco_diretrizes_escola(diretrizes_escola: list[dict] | None) -> str:
    """Bloco opcional de diretrizes — mesma montagem usada no system prompt."""
    bloco_escola = ""
    itens = [d for d in (diretrizes_escola or []) if d.get("diretriz_customizada")]
    if not itens:
        return bloco_escola
    linhas_esc = []
    for d in itens[:12]:
        mid = d.get("metodologia_key") or ""
        nome = d.get("metodologia_nome") or mid
        txt = str(d.get("diretriz_customizada") or "").strip()
        if not txt:
            continue
        if len(txt) > 400:
            txt = txt[:397] + "…"
        linhas_esc.append(f"- {mid} ({nome}): {txt}")
    if linhas_esc:
        bloco_escola = (
            "\n<diretrizes_da_escola>\n"
            "Se usar um ID abaixo, gancho_adaptacao e hipotese_teste DEVEM respeitar a diretriz.\n"
            + "\n".join(linhas_esc)
            + "\n</diretrizes_da_escola>\n"
        )
    return bloco_escola


def _bloco_metodologia_obrigatoria(
    metodologia_obrigatoria_id: str | None,
    metodologia_obrigatoria_nome: str | None,
) -> str:
    mid_ob = (metodologia_obrigatoria_id or "").strip()
    nome_ob = (metodologia_obrigatoria_nome or "").strip() or mid_ob
    if not mid_ob:
        return ""
    return f"""
<metodologia_obrigatoria_do_professor>
O professor EXIGIU a metodologia {mid_ob} ({nome_ob}) no caminho A.
A.id_metodologia DEVE ser exatamente {mid_ob}.
B e C: IDs distintos de A e entre si, de famílias distintas.
gancho_adaptacao e hipotese_teste de A: específicos dessa metodologia e do relato.
</metodologia_obrigatoria_do_professor>
"""


def medir_componentes_entrada_prompt(
    bloco_ref: str,
    *,
    exclude_ids: set[str] | None = None,
    diretrizes_escola: list[dict] | None = None,
    metodologia_obrigatoria_id: str | None = None,
    metodologia_obrigatoria_nome: str | None = None,
    system_prompt: str = "",
    user_content: str = "",
    ancoras_count: int | None = None,
    candidate_ids: list[str] | None = None,
) -> dict:
    """Métricas de tamanho (chars) das entradas reais do prompt — sem alterar o texto.

    `system_catalogo_chars` / `system_ancoras_chars` / `system_diretrizes_chars` medem
    os componentes de entrada usados na montagem (não necessariamente uma partição
    exata da string final do system, que também inclui regras/formato).
    """
    catalogo = _framework_ids_block(exclude_ids, candidate_ids=candidate_ids)
    bloco_escola = _bloco_diretrizes_escola(diretrizes_escola)
    bloco_obrigatoria = _bloco_metodologia_obrigatoria(
        metodologia_obrigatoria_id, metodologia_obrigatoria_nome
    )
    ref = bloco_ref or ""
    return {
        "system_total_chars": len(system_prompt or ""),
        "system_catalogo_chars": len(catalogo),
        "system_ancoras_chars": len(ref),
        "system_diretrizes_chars": len(bloco_escola),
        "system_obrigatoria_chars": len(bloco_obrigatoria),
        "user_content_chars": len(user_content or ""),
        "ancoras_count": int(ancoras_count) if ancoras_count is not None else 0,
        "candidate_catalog_chars": len(catalogo),
        "matcher_candidate_count": len(candidate_ids) if candidate_ids is not None else 0,
    }


def build_estruturar_system_prompt(
    bloco_ref: str,
    *,
    exclude_ids: set[str] | None = None,
    diretrizes_escola: list[dict] | None = None,
    metodologia_obrigatoria_id: str | None = None,
    metodologia_obrigatoria_nome: str | None = None,
    candidate_ids: list[str] | None = None,
) -> str:
    """Uma chamada: roteia IDs disponíveis + hipóteses ancoradas no RELATO.

    `candidate_ids=None` → catálogo completo permitido.
    `candidate_ids=[...]` → subconjunto (Top N do matcher).
    """
    framework = _framework_ids_block(exclude_ids, candidate_ids=candidate_ids)
    bloco_escola = _bloco_diretrizes_escola(diretrizes_escola)
    bloco_obrigatoria = _bloco_metodologia_obrigatoria(
        metodologia_obrigatoria_id, metodologia_obrigatoria_nome
    )
    # Compacto: sem BLOCO_TOM_PROMPT (persona longa); regras funcionais preservadas.
    return f"""Roteador inove4us. PT-BR. JSON válido apenas.
HÍBRIDO: NÃO gere cards/plano/cronograma/materiais/avaliação/EduScrum (backend).
Tarefa: 3 IDs + trecho + 3 causas + gancho/hipótese (1 frase boa, curta e contextualizada).

<framework_obrigatorio>
{framework}
</framework_obrigatorio>
{bloco_escola}
{bloco_obrigatoria}
<ancoras_de_estilo>
Só formato. NÃO são o problema. PROIBIDO copiar em causas/ganchos/hipóteses.
{bloco_ref}
</ancoras_de_estilo>

<regras>
1. A,B,C: IDs distintos e famílias distintas (Agilidade/Dedutivas/Contextuais/Indutivas). A=encaixe; B=outra família; C=híbrido. Se existir bloco metodologia_obrigatoria_do_professor, A.id_metodologia = esse ID.
2. id_metodologia = ID literal de METODOLOGIAS DISPONÍVEIS. Nunca invente.
3. Evite hábito Design Thinking express / Diagnóstico coletivo / Pitch de elevador; varie pelo relato (exceto A obrigatório).
4. trecho_relato_usado: menor fragmento reconhecível do PROBLEMA (~40–90 chars); sem título/objetivo/contexto inteiro; sem âncoras.
5. causas: 3 {{titulo, descricao}}; título curto; descricao = 1 frase causal (~70–120 chars), uma ideia, só do relato; sem justificativa/plano.
6. gancho_adaptacao: 1 frase (~70–110 chars) com elemento do relato + como a dinâmica entra; sem explicar metodologia nem repetir a hipótese.
7. hipotese_teste: 1 frase (~90–130 chars), testável (ação → efeito → evidência); um pouco mais rica que o gancho; sem mini-plano.
8. PROIBIDO: genéricos ("aplicar a metodologia"), plano/materiais, frase sem elemento do relato. Frases completas; se parecer âncora, reescreva.
</regras>

<formato>
{{"trecho_relato_usado":"fragmento curto","causas":[{{"titulo":"...","descricao":"1 frase causal"}},{{"titulo":"...","descricao":"1 frase causal"}},{{"titulo":"...","descricao":"1 frase causal"}}],"A":{{"id_metodologia":"dia_world_cafe","gancho_adaptacao":"frase curta do relato","hipotese_teste":"Se…, então…; observa…"}},"B":{{"id_metodologia":"agil_minute_paper","gancho_adaptacao":"...","hipotese_teste":"..."}},"C":{{"id_metodologia":"imersiva_escape_room","gancho_adaptacao":"...","hipotese_teste":"..."}}}}
</formato>
""".strip()


def build_ganchos_system_prompt(metodologia: str, cards_resumo: list[dict]) -> str:
    """Fase 2 leve (legado/raro): só ganchos — mecânica vem do banco estático."""
    linhas = []
    for i, c in enumerate(cards_resumo):
        tit = (c.get("titulo") or c.get("titulo_do_card") or f"Etapa {i + 1}").strip()
        obj = (c.get("objetivo") or "").strip()
        linhas.append(f"{i}. {tit} — {obj}")
    lista = "\n".join(linhas) or "(sem cards)"
    return f"""Você é designer instrucional da inove4us, falando com professores.
A mecânica da metodologia "{metodologia}" JÁ ESTÁ FIXA nos cards abaixo.
Sua ÚNICA tarefa: escrever um gancho_adaptacao completo por card, plugando o problema do professor.
Resposta em PT-BR. SOMENTE JSON válido.

{BLOCO_TOM_PROMPT}

<cards_fixos_imutaveis>
{lista}
</cards_fixos_imutaveis>

<regras>
1. Devolva EXATAMENTE 1 gancho por card, na mesma ordem (indice 0..N-1).
2. Cada gancho_adaptacao: 2–4 frases COMPLETAS, linguagem pedagógica simples. Cite o problema/contexto do professor. Não corte a frase.
3. NÃO reescreva a mecânica, NÃO invente novos cards, NÃO use etapas genéricas de DT
   (proibido: {", ".join(VERBOS_DT_PROIBIDOS)}) salvo se a metodologia for Design Thinking.
4. contexto_execucao: "sala" | "campo" | "misto" (só se o problema exigir campo/saída).
</regras>

<formato_json_esperado>
{{
  "contexto_execucao": "sala|campo|misto",
  "ganchos": [
    {{"indice": 0, "gancho_adaptacao": "..."}},
    {{"indice": 1, "gancho_adaptacao": "..."}}
  ]
}}
</formato_json_esperado>
""".strip()


def build_cards_system_prompt(metodologia: str, quadrante: str) -> str:
    """Fallback raro: gera cards densos quando a metodologia não está no DB estático."""
    return f"""Você é designer instrucional da inove4us. Gere o plano de execução em cards Kanban
para a metodologia "{metodologia}" (família {quadrante}).
Resposta em PT-BR. SOMENTE JSON válido.

<regras_de_execucao>
1. PLANO EDUSCRUM COMPLETO E DETALHADO (O 'COMO FAZER'): Os cards em `dinamica_passo_a_passo` não podem ser apenas títulos. O campo `como_executar_detalhado` deve conter instruções diretas e minuciosas (ex: como dividir a turma, o que falar, duração — mín. 3 frases densas, estilo manual). NÃO limite a 2 ou 3 passos. Gere entre 4 e 7 cards cobrindo início, meio, fim e avaliação da aula.
2. TEMPO POR CARD: cada card DEVE ter `duracao_minutos` (inteiro). Aula padrão em sala ≈ 50 min no total, MAS se houver campo/saída/atividade externa ou projeto multi-aula, ESTIME o tempo real necessário (pode ser 80, 100, 150+ min). Some em `duracao_total_estimada_min`. Informe `contexto_execucao`: "sala" | "campo" | "misto".
3. FIDELIDADE MECÂNICA: NÃO use etapas genéricas de Design Thinking (Empatizar, Definir, Idear, Prototipar), salvo se a metodologia for literalmente Design Thinking. Proibido: {", ".join(VERBOS_DT_PROIBIDOS)}.
4. ANTI-GENÉRICO: cada card precisa de `foco_da_metodologia_escolhida` específico da mecânica de "{metodologia}".
5. DIDÁTICA: quem fala, quem escuta, o que escrevem, papéis na equipe, entrega. Amarre ao tema do professor.
6. Os 3 primeiros itens do exemplo abaixo são ilustrativos — CONTINUE até 4–7 cards reais.
</regras_de_execucao>

<formato_json_esperado>
{{
  "contexto_execucao": "sala|campo|misto",
  "duracao_total_estimada_min": 50,
  "dinamica_passo_a_passo": [
    {{
      "titulo_do_card": "[Ação inicial específica da mecânica]",
      "objetivo": "...",
      "como_executar_detalhado": "[Instrução detalhada...]",
      "dica_de_facilitacao": "...",
      "foco_da_metodologia_escolhida": "...",
      "duracao_minutos": 10
    }}
  ]
}}
</formato_json_esperado>
""".strip()
