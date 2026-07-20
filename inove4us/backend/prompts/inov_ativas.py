"""Prompt canônico — Ranking de Adequação Metodológica (Inov-Ativas).

Arquitetura híbrida: o LLM só roteia (escolhe IDs do banco estático) e
escreve ganchos de adaptação. Cards/mecânica vêm de core.metodologias_db.
"""

from __future__ import annotations

from core.metodologias_db import METODOLOGIAS_DB

METODOLOGIAS_PERMITIDAS = {
    "criativas": [
        "Narrativas Transmídia",
        "Rotação por Estações",
        "Painel de Diversidade",
        "Caso Empático",
        "Design Thinking Express",
    ],
    "ageis": [
        "Minute Paper",
        "Pecha Kucha",
        "Elevator Pitch",
    ],
    "imersivas": [
        "Escape Room Educacional",
        "Roleplaying",
        "Gamificação Estrutural/Conteúdo",
        "Realidade Aumentada",
        "Jogos Sérios 3D",
    ],
    "analiticas": [
        "Learning Analytics",
        "Diagnóstico Coletivo",
        "Trilhas de Aprendizagem Adaptativas",
    ],
}

LISTA_FLAT = (
    METODOLOGIAS_PERMITIDAS["criativas"]
    + METODOLOGIAS_PERMITIDAS["ageis"]
    + METODOLOGIAS_PERMITIDAS["imersivas"]
    + METODOLOGIAS_PERMITIDAS["analiticas"]
)

# IDs canônicos do banco estático (única fonte de verdade para o roteador).
IDS_METODOLOGIA_DB: tuple[str, ...] = tuple(sorted(METODOLOGIAS_DB.keys()))

VERBOS_DT_PROIBIDOS = (
    "empatizar",
    "sintetizar",
    "idear",
    "prototipar",
    "definir o problema",
    "testar o protótipo",
)


def _framework_ids_block() -> str:
    """Lista IDs do METODOLOGIAS_DB agrupados por categoria (para o system prompt)."""
    buckets: dict[str, list[str]] = {
        "ÁGEIS": [],
        "CRI-ATIVAS": [],
        "IMERSIVAS": [],
        "ANALÍTICAS": [],
    }
    for mid, meta in METODOLOGIAS_DB.items():
        cat = str(meta.get("categoria") or "").strip().upper()
        nome = str(meta.get("nome") or mid).strip()
        line = f"`{mid}` — {nome}"
        if cat.startswith("ÁG") or cat.startswith("AG"):
            buckets["ÁGEIS"].append(line)
        elif cat.startswith("CRI"):
            buckets["CRI-ATIVAS"].append(line)
        elif cat.startswith("IMER"):
            buckets["IMERSIVAS"].append(line)
        elif cat.startswith("ANAL"):
            buckets["ANALÍTICAS"].append(line)
        else:
            buckets.setdefault(cat or "OUTRAS", []).append(line)
    linhas = []
    for cat, items in buckets.items():
        if not items:
            continue
        linhas.append(f"- {cat}:")
        for item in sorted(items):
            linhas.append(f"  - {item}")
    return "\n".join(linhas)


def build_estruturar_system_prompt(bloco_ref: str) -> str:
    """Roteador + adaptador: escolhe IDs do DB e escreve gancho_adaptacao (sem cards)."""
    framework = _framework_ids_block()
    return f"""Você é a IA arquiteta educacional da plataforma inove4us / mativas.
Arquitetura HÍBRIDA: você NÃO gera cards, passos EduScrum, timebox nem manuais de sala.
Seu único papel: (1) ROTEAR — escolher 3 IDs do banco estático; (2) ADAPTAR — escrever o gancho_adaptacao.
Resposta em PT-BR. SOMENTE JSON válido (sem markdown, sem texto fora do JSON).

<framework_obrigatorio>
Use APENAS estes IDs exatos (copiados do banco Python `METODOLOGIAS_DB`). Nunca invente IDs nem nomes livres.
{framework}
</framework_obrigatorio>

<base_de_problemas>
{bloco_ref}
</base_de_problemas>

<regras_de_roteamento>
1. Devolva EXATAMENTE as chaves "A", "B" e "C" (nesta ordem semântica: A=encaixe direto, B=alternativa de outro quadrante/família, C=híbrido criativo).
2. Em cada opção, `id_metodologia` DEVE ser um ID literal de <framework_obrigatorio> (ex.: `agil_elevator_pitch`). Proibido nome amigável no lugar do ID.
3. A, B e C devem usar IDs DIFERENTES. Prefira diversificar categorias (ÁGEIS / CRI-ATIVAS / IMERSIVAS / ANALÍTICAS) quando fizer sentido pedagógico.
4. NÃO escolha `criativa_design_thinking_express` por hábito — só se a mecânica DT for realmente a melhor para o problema.
5. NÃO gere campos extras (sem plano_eduscrum, sem dinamica_passo_a_passo, sem causas_raiz, sem resumo_analise). O Python monta os cards a partir do ID.
6. `gancho_adaptacao`: um parágrafo de 3 a 4 linhas, criativo e concreto, explicando como o TEMA/problema do professor se encaixa na MECÂNICA da metodologia escolhida (o que muda na sala, qual o "coração" da aula, como os alunos vivem o conteúdo).
</regras_de_roteamento>

<formato_de_saida>
Responda ESTRITAMENTE com este JSON (e nada mais):
{{
  "A": {{
    "id_metodologia": "criativa_rotacao_estacoes",
    "gancho_adaptacao": "O tema de descarte de lixo será o coração desta rotação..."
  }},
  "B": {{
    "id_metodologia": "agil_elevator_pitch",
    "gancho_adaptacao": "Os grupos terão 1 minuto para vender a solução urbana..."
  }},
  "C": {{
    "id_metodologia": "imersiva_escape_room",
    "gancho_adaptacao": "A sala será transformada em um laboratório tóxico onde..."
  }}
}}
</formato_de_saida>
""".strip()


def build_ganchos_system_prompt(metodologia: str, cards_resumo: list[dict]) -> str:
    """Fase 2 leve: só ganchos de adaptação — mecânica vem do banco estático."""
    linhas = []
    for i, c in enumerate(cards_resumo):
        tit = (c.get("titulo") or c.get("titulo_do_card") or f"Etapa {i + 1}").strip()
        obj = (c.get("objetivo") or "").strip()
        linhas.append(f"{i}. {tit} — {obj}")
    lista = "\n".join(linhas) or "(sem cards)"
    return f"""Você é designer instrucional da inove4us.
A mecânica da metodologia "{metodologia}" JÁ ESTÁ FIXA nos cards abaixo.
Sua ÚNICA tarefa: escrever um gancho_adaptacao curto por card, plugando o problema do professor.
Resposta em PT-BR. SOMENTE JSON válido.

<cards_fixos_imutaveis>
{lista}
</cards_fixos_imutaveis>

<regras>
1. Devolva EXATAMENTE 1 gancho por card, na mesma ordem (indice 0..N-1).
2. Cada gancho_adaptacao: 1–2 frases (≤ 280 caracteres). Cite o problema/contexto do professor.
3. NÃO reescreva a mecânica, NÃO invente novos cards, NÃO use etapas genéricas de DT
   (proibido: {", ".join(VERBOS_DT_PROIBIDOS)}) salvo se a metodologia for Design Thinking Express.
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
para a metodologia "{metodologia}" (quadrante {quadrante}).
Resposta em PT-BR. SOMENTE JSON válido.

<regras_de_execucao>
1. PLANO EDUSCRUM COMPLETO E DETALHADO (O 'COMO FAZER'): Os cards em `dinamica_passo_a_passo` não podem ser apenas títulos. O campo `como_executar_detalhado` deve conter instruções diretas e minuciosas (ex: como dividir a turma, o que falar, duração — mín. 3 frases densas, estilo manual). NÃO limite a 2 ou 3 passos. Gere entre 4 e 7 cards cobrindo início, meio, fim e avaliação da aula.
2. TEMPO POR CARD: cada card DEVE ter `duracao_minutos` (inteiro). Aula padrão em sala ≈ 50 min no total, MAS se houver campo/saída/atividade externa ou projeto multi-aula, ESTIME o tempo real necessário (pode ser 80, 100, 150+ min). Some em `duracao_total_estimada_min`. Informe `contexto_execucao`: "sala" | "campo" | "misto".
3. FIDELIDADE MECÂNICA: NÃO use etapas genéricas de Design Thinking (Empatizar, Definir, Idear, Prototipar), salvo se a metodologia for literalmente Design Thinking Express. Proibido: {", ".join(VERBOS_DT_PROIBIDOS)}.
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
