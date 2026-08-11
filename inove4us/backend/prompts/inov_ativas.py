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


def _framework_ids_block(exclude_ids: set[str] | None = None) -> str:
    """As 39 metodologias do catálogo canônico (IDs + nomes, sem cards)."""
    blocked = {str(x) for x in (exclude_ids or set()) if x}
    buckets: dict[str, list[str]] = {k: [] for k in _BUCKET_ORDER}
    total = 0
    for entrada in entradas_catalogo_dia():
        if entrada["id"] in blocked:
            continue
        etq = entrada["etiqueta"]
        line = f"`{entrada['id']}` — {entrada['nome']}"
        buckets.setdefault(etq, []).append(line)
        total += 1
    linhas = [f"Total: {total} metodologias (catálogo canônico — não invente)."]
    for cat in _BUCKET_ORDER:
        items = buckets.get(cat) or []
        if not items:
            continue
        linhas.append(f"- {cat}:")
        for item in sorted(items):
            linhas.append(f"  - {item}")
    return "\n".join(linhas)


def build_estruturar_system_prompt(
    bloco_ref: str,
    *,
    exclude_ids: set[str] | None = None,
    diretrizes_escola: list[dict] | None = None,
    metodologia_obrigatoria_id: str | None = None,
    metodologia_obrigatoria_nome: str | None = None,
) -> str:
    """Uma chamada: roteia IDs do catálogo 39 + hipóteses ancoradas no RELATO."""
    framework = _framework_ids_block(exclude_ids)
    bloco_escola = ""
    itens = [d for d in (diretrizes_escola or []) if d.get("diretriz_customizada")]
    if itens:
        linhas_esc = []
        for d in itens[:12]:
            mid = d.get("metodologia_key") or ""
            nome = d.get("metodologia_nome") or mid
            txt = str(d.get("diretriz_customizada") or "").strip()
            if not txt:
                continue
            if len(txt) > 400:
                txt = txt[:397] + "…"
            linhas_esc.append(f"- `{mid}` ({nome}): {txt}")
        if linhas_esc:
            bloco_escola = (
                "\n<diretrizes_da_escola>\n"
                "O professor tem vínculo com uma escola. Se escolher um dos IDs abaixo, "
                "o gancho_adaptacao e a hipotese_teste DEVEM respeitar a diretriz correspondente "
                "(não contradizer nem ignorar).\n"
                + "\n".join(linhas_esc)
                + "\n</diretrizes_da_escola>\n"
            )
    bloco_obrigatoria = ""
    mid_ob = (metodologia_obrigatoria_id or "").strip()
    nome_ob = (metodologia_obrigatoria_nome or "").strip() or mid_ob
    if mid_ob:
        bloco_obrigatoria = f"""
<metodologia_obrigatoria_do_professor>
O professor EXIGIU a metodologia `{mid_ob}` ({nome_ob}) no caminho A.
- A.id_metodologia DEVE ser exatamente `{mid_ob}`.
- B e C: IDs DIFERENTES de A e entre si, de FAMÍLIAS DIFERENTES.
- Escreva gancho_adaptacao e hipotese_teste de A especificamente para essa metodologia e o relato.
</metodologia_obrigatoria_do_professor>
"""
    return f"""Você é uma especialista pedagógica da inove4us, conversando com professores e instrutores.
Arquitetura HÍBRIDA: NÃO gere cards EduScrum, timebox nem manuais de sala.
Papel: (1) ROTEAR 3 IDs do catálogo de 39; (2) escrever gancho + hipótese + trecho do RELATO DO PROFESSOR.
Resposta em PT-BR. SOMENTE JSON válido.

{BLOCO_TOM_PROMPT}

<framework_obrigatorio>
Use APENAS estes IDs do catálogo canônico (nunca invente nome ou ID fora da lista).
{framework}
</framework_obrigatorio>
{bloco_escola}
{bloco_obrigatoria}
<ancoras_de_estilo>
Os itens abaixo são SÓ exemplo de FORMATO (categoria › tema). NÃO são o problema do professor.
PROIBIDO copiar, parafrasear ou reutilizar o conteúdo dessas âncoras em hipóteses/causas/ganchos.
{bloco_ref}
</ancoras_de_estilo>

<regras>
1. Chaves "A","B","C": A=encaixe direto, B=outra família, C=híbrido. IDs DIFERENTES e de FAMÍLIAS DIFERENTES (Agilidade / Dedutivas / Contextuais / Indutivas). Se houver <metodologia_obrigatoria_do_professor>, A DEVE usar exatamente esse ID.
2. `id_metodologia` = ID literal de <framework_obrigatorio> (uma das 39). NUNCA invente.
3. NÃO escolha por hábito Design Thinking / Diagnóstico Coletivo / Discurso de Elevador. Varie entre as 39 conforme o relato (exceto A quando obrigatório).
4. `trecho_relato_usado` (raiz): cite 1 frase CURTA do PROBLEMA DO PROFESSOR (não das âncoras).
5. `causas` (raiz): SEMPRE 3 itens {{titulo, descricao}} derivados SÓ do relato/contexto do professor. Títulos curtos e descrições completas (2–4 frases), em linguagem pedagógica simples — o que está atrapalhando a aprendizagem e o que observar na turma.
6. Em cada opção: `gancho_adaptacao` (3–5 frases COMPLETAS) explica, para o professor, POR QUE esta dinâmica serve NESTA aula e COMO mediar a prática. Cite elementos concretos do relato. `hipotese_teste` (2–3 frases completas) no formato: se conduzir X, a turma pratica Y e você observa Z. NÃO invente cards nem copie o problema inteiro.
7. Se uma hipótese parecer com as âncoras de estilo, REESCREVA com palavras do professor.
8. Prefira citar elementos específicos do relato. Textos SEMPRE inteiros — nunca termine com reticências ou frase cortada.
</regras>

<formato>
{{
  "trecho_relato_usado": "frase curta copiada/parafraseada do PROBLEMA DO PROFESSOR",
  "causas": [
    {{"titulo": "...", "descricao": "..."}}
  ],
  "A": {{
    "id_metodologia": "dia_world_cafe",
    "gancho_adaptacao": "...",
    "hipotese_teste": "Se aplicarmos … a partir de «trecho do professor», …"
  }},
  "B": {{
    "id_metodologia": "agil_minute_paper",
    "gancho_adaptacao": "...",
    "hipotese_teste": "..."
  }},
  "C": {{
    "id_metodologia": "imersiva_escape_room",
    "gancho_adaptacao": "...",
    "hipotese_teste": "..."
  }}
}}
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
