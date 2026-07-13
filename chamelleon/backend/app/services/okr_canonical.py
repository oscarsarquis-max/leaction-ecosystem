"""Matriz canônica PanelDX — 5 Direcionadores × Objetivos × KRs × KPIs.

Esta matriz é o padrão de onboarding de TODOS os clientes e indústrias:
aplicada na criação do tenant (cadastro) e em backfill na subida da API.
O gestor pode alterar/criar itens depois; o seed só corre se o tenant
ainda não tiver direcionadores.
"""

from __future__ import annotations

# Cada item: (nome_direcionador, objetivo, [(kr_desc, target, unit)], [(kpi_name, is_financial, unit)])
CANONICAL_OKR_MATRIX: list[dict] = [
    {
        "name": "Digitalização Organizacional",
        "sort_order": 1,
        "objective": (
            "Automatizar e digitalizar o fluxo de valor para reduzir desperdícios "
            "operacionais e acelerar a entrega."
        ),
        "key_results": [
            {"description": "Reduzir o Lead Time em 25%", "target_value": 25.0, "metric_unit": "%"},
            {
                "description": "Atingir 90% dos processos Paperless",
                "target_value": 90.0,
                "metric_unit": "%",
            },
        ],
        "kpis": [
            {"name": "Lead Time (dias)", "is_financial": False, "metric_unit": "dias"},
            {"name": "Redução de OPEX", "is_financial": True, "metric_unit": "R$"},
        ],
    },
    {
        "name": "Desenvolvimento Sustentável",
        "sort_order": 2,
        "objective": (
            "Otimizar o uso de recursos físicos e lógicos, alinhando eficiência com metas ESG."
        ),
        "key_results": [
            {
                "description": "Reduzir consumo de insumos em 20%",
                "target_value": 20.0,
                "metric_unit": "%",
            },
            {
                "description": "Eliminar 100% dos servidores físicos obsoletos",
                "target_value": 100.0,
                "metric_unit": "%",
            },
        ],
        "kpis": [
            {"name": "Pegada de Carbono", "is_financial": False, "metric_unit": "tCO2e"},
            {
                "name": "Economia direta com infraestrutura",
                "is_financial": True,
                "metric_unit": "R$",
            },
        ],
    },
    {
        "name": "Capacitação da Equipe",
        "sort_order": 3,
        "objective": (
            "Elevar a maturidade digital dos talentos para acelerar a adoção de tecnologias."
        ),
        "key_results": [
            {
                "description": "100% dos operadores retreinados nos novos POPs",
                "target_value": 100.0,
                "metric_unit": "%",
            },
            {
                "description": "Aumentar proficiência em softwares em 30%",
                "target_value": 30.0,
                "metric_unit": "%",
            },
        ],
        "kpis": [
            {"name": "Horas de Treinamento", "is_financial": False, "metric_unit": "h"},
            {
                "name": "Aumento da Receita por Colaborador",
                "is_financial": True,
                "metric_unit": "R$",
            },
        ],
    },
    {
        "name": "Prontidão Tecnológica",
        "sort_order": 4,
        "objective": (
            "Modernizar a arquitetura de sistemas para suportar alta disponibilidade "
            "e integração em tempo real."
        ),
        "key_results": [
            {
                "description": "Migrar 100% dos sistemas legados para nuvem",
                "target_value": 100.0,
                "metric_unit": "%",
            },
            {
                "description": "Alcançar 99.9% de Uptime",
                "target_value": 99.9,
                "metric_unit": "%",
            },
        ],
        "kpis": [
            {
                "name": "MTTR - Tempo Médio de Recuperação",
                "is_financial": False,
                "metric_unit": "min",
            },
            {"name": "Redução do TCO de TI", "is_financial": True, "metric_unit": "R$"},
        ],
    },
    {
        "name": "Concorrência e Novos Modelos de Negócio",
        "sort_order": 5,
        "objective": "Redesenhar a jornada do cliente e lançar novos serviços digitais.",
        "key_results": [
            {
                "description": "Lançar 2 novos serviços digitais",
                "target_value": 2.0,
                "metric_unit": "un",
            },
            {
                "description": "Aumentar CSAT em 15 pontos",
                "target_value": 15.0,
                "metric_unit": "pts",
            },
        ],
        "kpis": [
            {"name": "NPS - Net Promoter Score", "is_financial": False, "metric_unit": "pts"},
            {
                "name": "Aumento do Faturamento Bruto",
                "is_financial": True,
                "metric_unit": "R$",
            },
        ],
    },
]
