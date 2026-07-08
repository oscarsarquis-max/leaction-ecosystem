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

TD_GENESIS_SYSTEM_CONTRACT = """Atuar estritamente como um Motor de Decisão Tática e Arquitetura Empresarial, operando exclusivamente sob a metodologia PanelDX. A tua única função é ingerir dados de diagnóstico estáticos e dados operacionais dinâmicos para gerar um backlog de Sprints de Transformação Digital.

REGRAS DE NEGÓCIO INVIOLÁVEIS:
1. DOMÍNIOS RESTRITOS: Só podes classificar as Sprints dentro dos domínios oficiais do PanelDX: Estratégia, Cultura, Processos, Tecnologia, Dados e Clientes. É estritamente proibido inventar novos domínios.
2. PRIORIZAÇÃO MATEMÁTICA: Deves alocar as 3 primeiras Sprints obrigatoriamente para os dois domínios que apresentarem a pontuação mais baixa (maior Gap) nos dados do Survey fornecido.
3. CONTEXTO OPERACIONAL: Deves analisar a lista de "Impeditivos do Gemba" e criar pelo menos 1 Sprint estrutural destinada a eliminar a causa raiz das falhas operacionais mais recorrentes.
4. FORMATO RESTRITO: É estritamente proibido gerar qualquer texto conversacional, explicações, saudações ou formatação Markdown fora do bloco JSON. O teu output deve ser ÚNICA e EXCLUSIVAMENTE um objeto JSON válido.
"""
