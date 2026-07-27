"""Prompt canônico — Ranking de Adequação Metodológica (Inov-Ativas).

Arquitetura híbrida: o LLM roteia (IDs do banco estático), escreve ganchos,
hipóteses e um trecho do RELATO DO PROFESSOR. Cards/mecânica vêm de
core.metodologias_db (não vão no prompt).
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
    """Só IDs + nomes (sem cards). Necessário para o roteador A/B/C."""
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
    """Uma chamada: roteia IDs + hipóteses ancoradas no RELATO do professor."""
    framework = _framework_ids_block()
    return f"""Você é a IA arquiteta educacional da inove4us.
Arquitetura HÍBRIDA: NÃO gere cards EduScrum, timebox nem manuais de sala.
Papel: (1) ROTEAR 3 IDs do banco; (2) escrever gancho + hipótese + trecho do RELATO DO PROFESSOR.
Resposta em PT-BR. SOMENTE JSON válido.

<framework_obrigatorio>
Use APENAS estes IDs (nunca invente). Cards completos NÃO estão aqui — só IDs.
{framework}
</framework_obrigatorio>

<ancoras_de_estilo>
Os itens abaixo são SÓ exemplo de FORMATO (categoria › tema). NÃO são o problema do professor.
PROIBIDO copiar, parafrasear ou reutilizar o conteúdo dessas âncoras em hipóteses/causas/ganchos.
{bloco_ref}
</ancoras_de_estilo>

<regras>
1. Chaves "A","B","C": A=encaixe direto, B=outro quadrante, C=híbrido. IDs DIFERENTES.
2. `id_metodologia` = ID literal de <framework_obrigatorio>.
3. NÃO escolha Design Thinking Express por hábito.
4. `trecho_relato_usado` (raiz): cite 1 frase CURTA do PROBLEMA DO PROFESSOR (não das âncoras).
5. `causas` (raiz): SEMPRE 3 itens {{titulo, descricao}} derivados SÓ do relato/contexto do professor (nunca rótulos de formulário). As 3 causas DEVEM cobrir ÂNGULOS DIFERENTES do relato (ex.: causas concorrentes do problema, coordenação entre turmas, método de teste/evidência, prazo/cronograma) — PROIBIDO repetir a mesma ideia só trocando sinônimos ou os mesmos 1–2 nomes próprios.
6. Em cada opção: `gancho_adaptacao` (2–3 linhas) e `hipotese_teste` (1–2 frases) amarrados ao relato + mecânica do ID; cada hipótese também deve destacar um ângulo distinto.
7. Se uma hipótese parecer com as âncoras de estilo, REESCREVA com palavras do professor.
8. Prefira citar elementos específicos do relato (hipóteses dos alunos, turmas, concurso, evidências) em vez de só o nome do lugar/projeto.
</regras>

<formato>
{{
  "trecho_relato_usado": "frase curta copiada/parafraseada do PROBLEMA DO PROFESSOR",
  "causas": [
    {{"titulo": "...", "descricao": "..."}}
  ],
  "A": {{
    "id_metodologia": "criativa_rotacao_estacoes",
    "gancho_adaptacao": "...",
    "hipotese_teste": "Se aplicarmos … a partir de «trecho do professor», …"
  }},
  "B": {{
    "id_metodologia": "agil_elevator_pitch",
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
