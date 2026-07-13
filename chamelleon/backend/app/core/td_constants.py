"""Constantes e contrato do Motor de Decisão Tática PanelDX (Transformação Digital)."""

from __future__ import annotations

# Domínios oficiais restritos — é estritamente proibido inventar outros.
TD_OFFICIAL_DOMAINS: tuple[str, ...] = (
    "Estratégia",
    "Cultura",
    "Processos",
    "Tecnologia",
    "Dados",
    "Clientes",
)

TD_OFFICIAL_DOMAINS_SET = frozenset(TD_OFFICIAL_DOMAINS)

# Mapeamento dos domínios de avaliação PanelDX (9) → taxonomia TD (6).
ASSESSMENT_DOMAIN_TO_TD: dict[str, str] = {
    "ds": "Estratégia",
    "bm": "Processos",
    "ic": "Cultura",
    "dc": "Dados",
    "cc": "Cultura",
    "dg": "Estratégia",
    "dp": "Tecnologia",
    "cap": "Tecnologia",
    "dm": "Tecnologia",
    # Aliases por nome
    "estratégia digital": "Estratégia",
    "estrategia digital": "Estratégia",
    "estratégia": "Estratégia",
    "estrategia": "Estratégia",
    "modelos de negócio": "Processos",
    "modelo de negócio digital": "Processos",
    "processos": "Processos",
    "inovação": "Cultura",
    "cultura de inovação": "Cultura",
    "cultura": "Cultura",
    "cultura de dados": "Dados",
    "dados": "Dados",
    "colaboração": "Cultura",
    "clientes": "Clientes",
    "governança": "Estratégia",
    "plataformas": "Tecnologia",
    "capacidades": "Tecnologia",
    "métricas": "Tecnologia",
    "tecnologia": "Tecnologia",
}

# Materialização no estilo Gênese PanelDX (sprint_governance)
TD_GENESE_MAX_SPRINTS = 12
TD_GENESE_ONDA1_ATIVAS = 3

TD_AI_MAX_TOKENS = 8192

# Schema de sprint (prompt CoT) — campos _analise_* são raciocínio obrigatório antes da justificativa.
TD_SPRINT_SCHEMA: dict = {
    "type": "object",
    "required": [
        "id_bloc",
        "nome_sprint",
        "paneldx_domain",
        "_analise_gap",
        "_analise_gemba",
        "_analise_contexto",
        "justificativa_baseada_no_relatorio",
    ],
    "properties": {
        "id_bloc": {
            "type": "string",
            "description": "UUID do bloco metodológico (obrigatório — use id_bloc do catálogo)",
        },
        "nome_sprint": {"type": "string"},
        "paneldx_domain": {
            "type": "string",
            "enum": list(TD_OFFICIAL_DOMAINS),
        },
        "origin_type": {
            "type": "string",
            "enum": ["baseline", "kaizen_emergent"],
        },
        "objetivo": {"type": "string"},
        "descricao": {"type": "string"},
        "_analise_gap": {
            "type": "string",
            "description": (
                "PASSO 1: Descreva qual foi a fragilidade exata identificada no Survey "
                "(PanelDX) para este bloco."
            ),
        },
        "_analise_gemba": {
            "type": "string",
            "description": (
                "PASSO 2: Identifique e descreva qual falha, gargalo ou impeditivo real "
                "relatado nos IMPEDITIVOS_DO_GEMBA tem relação direta com essa fragilidade. "
                "Se os impeditivos estiverem vazios ou não tiverem relação, escreva: "
                "'Não há correlação direta com os registros recentes do Gemba'."
            ),
        },
        "_analise_contexto": {
            "type": "string",
            "description": (
                "PASSO 3: Descreva como a falta deste bloco afeta os objetivos estratégicos "
                "descritos no CONTEXTO_INSTITUCIONAL."
            ),
        },
        "justificativa_baseada_no_relatorio": {
            "type": "string",
            "description": (
                "PASSO FINAL: Sintetize obrigatoriamente as três análises anteriores "
                "(_analise_gap, _analise_gemba e _analise_contexto) num ÚNICO parágrafo "
                "fluido, com tom consultivo e maduro. Não use tópicos."
            ),
        },
        "derv_defi": {"type": "string", "description": "definição do entregável"},
        "derv_comp": {"type": "string", "description": "competências necessárias"},
        "criteria_dod": {
            "type": "object",
            "properties": {
                "required": {"type": "array", "items": {"type": "string"}},
                "context_education": {"type": "array", "items": {"type": "string"}},
            },
        },
        "atividades_taticas": {"type": "array", "items": {"type": "string"}},
        "swot_type": {"type": "string"},
        "swot_justification": {"type": "string"},
        "week_sprn": {"type": "integer"},
        "targv_sprn": {"type": "integer"},
        "priority_rank": {"type": "integer"},
        "gemba_driven": {"type": "boolean"},
        "onda": {"type": "string"},
    },
}

TD_GENESIS_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "required": ["sprints"],
    "properties": {
        "sprints": {
            "type": "array",
            "items": TD_SPRINT_SCHEMA,
        }
    },
}

TD_GENESIS_SYSTEM_CONTRACT = """Atuar estritamente como um Motor de Decisão Tática e Arquitetura Empresarial, operando exclusivamente sob a metodologia PanelDX. A tua única função é ingerir dados de diagnóstico estáticos e dados operacionais dinâmicos para gerar um backlog de Sprints de Transformação Digital.

REGRAS DE NEGÓCIO INVIOLÁVEIS:
1. DOMÍNIOS RESTRITOS: Só podes classificar as Sprints dentro dos domínios oficiais do PanelDX: Estratégia, Cultura, Processos, Tecnologia, Dados e Clientes. É estritamente proibido inventar novos domínios.
2. PRIORIZAÇÃO MATEMÁTICA: Deves alocar as 3 primeiras Sprints obrigatoriamente para os dois domínios que apresentarem a pontuação mais baixa (maior Gap) nos dados do Survey fornecido.
3. CONTEXTO OPERACIONAL: Deves analisar a lista de "Impeditivos do Gemba" e criar pelo menos 1 Sprint estrutural destinada a eliminar a causa raiz das falhas operacionais mais recorrentes.
4. REGRA DE TRIANGULAÇÃO OBRIGATÓRIA PARA A JUSTIFICATIVA: É ESTRITAMENTE PROIBIDO justificar a escolha de um bloco focando-se apenas na pontuação ou Gap. O campo 'justificativa_baseada_no_relatorio' TEM de integrar obrigatoriamente num único parágrafo fluido os 3 vértices: 1) A fragilidade estrutural (Gap/Survey), 2) O impacto que isso está a causar na operação diária (citando evidências dos IMPEDITIVOS_DO_GEMBA), e 3) O motivo pelo qual resolver isto é vital para os objetivos atuais da organização (cruzando com o CONTEXTO_INSTITUCIONAL).
5. CHAIN OF THOUGHT (CoT) OBRIGATÓRIO: Ao construir a justificativa, DEVES OBRIGATORIAMENTE preencher os campos '_analise_gap', '_analise_gemba' e '_analise_contexto' primeiro. Eles servem de raciocínio lógico para construíres o parágrafo final e maduro na 'justificativa_baseada_no_relatorio'. Nunca inventes a justificativa sem preencher esses três passos.
6. FORMATO RESTRITO: É estritamente proibido gerar qualquer texto conversacional, explicações, saudações ou formatação Markdown fora do bloco JSON. O teu output deve ser ÚNICA e EXCLUSIVAMENTE um objeto JSON válido.
"""
