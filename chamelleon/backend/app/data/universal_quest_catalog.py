"""Catálogo universal de assessment — 4 dimensões fixas da metodologia Chamelleon."""

from __future__ import annotations

from typing import Any

# Mapeamento id_dime → dimensão universal
# 1=SV, 2=HC, 3=FS, 5=DA (4=LA é setorial — excluída do legado universal)
DIMENSION_META: dict[str, dict[str, str]] = {
    "SV": {
        "name": "Shared Vision",
        "label": "Visão Compartilhada",
        "legacy_id_dime": "1",
    },
    "HC": {
        "name": "Heart Connection",
        "label": "Coração e Conexão",
        "legacy_id_dime": "2",
    },
    "FS": {
        "name": "Fluid Structure",
        "label": "Estrutura Fluida",
        "legacy_id_dime": "3",
    },
    "DA": {
        "name": "Digital Architecture",
        "label": "Arquitetura Digital",
        "legacy_id_dime": "5",
    },
}

DOMAIN_META: dict[str, dict[str, str]] = {
    "ds": {"name": "Digital Strategy", "label": "Estratégia Digital"},
    "bm": {"name": "Digital Business Models", "label": "Modelos de Negócio"},
    "ic": {"name": "Innovation Culture", "label": "Inovação"},
    "dc": {"name": "Data Culture", "label": "Cultura de Dados"},
    "cc": {"name": "Collaboration Culture", "label": "Colaboração"},
    "dg": {"name": "Digital Governance", "label": "Governança"},
    "dp": {"name": "Digital Platforms", "label": "Plataformas"},
    "cap": {"name": "Digital Capabilities", "label": "Capacidades"},
    "dm": {"name": "Digital Metrics", "label": "Métricas"},
}

from app.data.rubric_patterns import default_maturity_options

# Questões universais — uma representativa por domínio nas 4 dimensões fixas.
UNIVERSAL_ASSESSMENT_ITEMS: list[dict[str, Any]] = [
    {
        "dimension_key": "SV",
        "domain_key": "ds",
        "question_text": (
            "A organização possui uma visão digital compartilhada, com cenários futuros "
            "mapeados e iniciativas estratégicas priorizadas no backlog?"
        ),
        "source": "universal:SV/ds — Cenário Prospectivo, Missão Digital",
    },
    {
        "dimension_key": "SV",
        "domain_key": "bm",
        "question_text": (
            "Existem modelos de negócio digital formalizados, com análise de clientes, "
            "concorrência e roadmap de produtos/serviços digitais?"
        ),
        "source": "universal:SV/bm — Business Model Canvas, Roadmap de Produtos",
    },
    {
        "dimension_key": "SV",
        "domain_key": "ic",
        "question_text": (
            "A inovação digital está institucionalizada com processos para identificar, "
            "priorizar e incubar novas oportunidades?"
        ),
        "source": "universal:SV/ic — Backlog de Iniciativas Estratégicas",
    },
    {
        "dimension_key": "HC",
        "domain_key": "dc",
        "question_text": (
            "A cultura orientada a dados está disseminada, com literacia analítica e "
            "decisões baseadas em evidências?"
        ),
        "source": "universal:HC/dc — Analítica de Desenvolvimento Humano",
    },
    {
        "dimension_key": "HC",
        "domain_key": "cc",
        "question_text": (
            "Há práticas estruturadas de colaboração digital entre áreas, com comunidades "
            "e canais de engajamento ativos?"
        ),
        "source": "universal:HC/cc — Comunidades e Engajamento",
    },
    {
        "dimension_key": "HC",
        "domain_key": "dg",
        "question_text": (
            "A governança digital (políticas, papéis, comitês) está definida e operando "
            "com ritos de acompanhamento?"
        ),
        "source": "universal:HC/dg — Governança de Comunicação e Programas",
    },
    {
        "dimension_key": "FS",
        "domain_key": "dp",
        "question_text": (
            "As plataformas digitais corporativas estão integradas e suportam jornadas "
            "operacionais ponta a ponta?"
        ),
        "source": "universal:FS/dp — Canais de Parceria, Plataformas",
    },
    {
        "dimension_key": "FS",
        "domain_key": "cap",
        "question_text": (
            "As capacidades digitais (talentos, competências, onboarding) são mapeadas, "
            "desenvolvidas e realocadas de forma ágil?"
        ),
        "source": "universal:FS/cap — Onboarding, Mobilidade Interna",
    },
    {
        "dimension_key": "FS",
        "domain_key": "dm",
        "question_text": (
            "Métricas digitais de desempenho operacional são coletadas, validadas e "
            "utilizadas em ciclos de melhoria?"
        ),
        "source": "universal:FS/dm — Validação do Negócio",
    },
    {
        "dimension_key": "DA",
        "domain_key": "dg",
        "question_text": (
            "A arquitetura de segurança, identidade, privacidade (LGPD) e resiliência "
            "está documentada e auditável?"
        ),
        "source": "universal:DA/dg — Segurança, Privacidade, Acessibilidade",
    },
    {
        "dimension_key": "DA",
        "domain_key": "dp",
        "question_text": (
            "Existe um mapa de tecnologia com padrões corporativos, nuvem, interoperabilidade "
            "e arquitetura modular definidos?"
        ),
        "source": "universal:DA/dp — Mapa de Tecnologia, Interoperabilidade",
    },
]


def axis_label(dimension_key: str, domain_key: str) -> str:
    dim = DIMENSION_META[dimension_key]
    dom = DOMAIN_META[domain_key]
    return f"{dimension_key} — {dim['name']} / {dom['label']}"


def get_universal_assessment_items() -> list[dict[str, Any]]:
    """Retorna itens prontos para inserção em AssessmentItem."""
    items: list[dict[str, Any]] = []
    for entry in UNIVERSAL_ASSESSMENT_ITEMS:
        dim_key = entry["dimension_key"]
        dom_key = entry["domain_key"]
        items.append(
            {
                "axis": axis_label(dim_key, dom_key),
                "question_text": entry["question_text"],
                "question_type": "multiple_choice",
                "options": default_maturity_options(),
                "metadata": {
                    "dimension_key": dim_key,
                    "domain_key": dom_key,
                    "legacy_source": entry["source"],
                    "origin": "universal_catalog",
                },
            }
        )
    return items
