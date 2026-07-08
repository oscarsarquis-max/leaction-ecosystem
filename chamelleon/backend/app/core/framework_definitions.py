"""Definições canônicas do framework PanelDX/Chamelleon — dimensões, domínios e taxonomia."""

from __future__ import annotations

from pathlib import Path
from typing import Any

UNIVERSAL_DIMENSION_KEYS: tuple[str, ...] = ("SV", "HC", "FS", "DA")

# Dimensão canônica de referência substituída pela 5ª dimensão setorial (ex.: TA em telecom).
SECTOR_DIMENSION_TEMPLATE_KEY = "LA"

# Os 9 domínios operacionais canônicos (chaves da 5ª dimensão / TA).
OPERATIONAL_DOMAINS: tuple[tuple[str, str], ...] = (
    ("ds", "Digital Strategy"),
    ("bm", "Digital Business Models"),
    ("ic", "Innovation Culture"),
    ("dc", "Data Culture"),
    ("cc", "Collaboration Culture"),
    ("dg", "Digital Governance"),
    ("dp", "Digital Platforms"),
    ("cap", "Digital Capabilities"),
    ("dm", "Digital Metrics"),
)

CANONICAL_DOMAIN_KEYS = frozenset(key for key, _ in OPERATIONAL_DOMAINS)

# Alias legado PanelDX presente em FRAMEWORK_KNOWLEDGE (ex.: dc_cap).
DOMAIN_KEY_ALIASES: dict[str, str] = {
    "dc_cap": "cap",
}

DOMAIN_NAMES_BY_KEY: dict[str, str] = dict(OPERATIONAL_DOMAINS)


def normalize_domain_key(domain_key: str | None) -> str:
    if not domain_key:
        return ""
    key = str(domain_key).strip().lower()
    return DOMAIN_KEY_ALIASES.get(key, key)


def is_valid_operational_domain_key(domain_key: str | None) -> bool:
    return normalize_domain_key(domain_key) in CANONICAL_DOMAIN_KEYS


def load_framework_definitions_source() -> str:
    return Path(__file__).resolve().read_text(encoding="utf-8")


def get_canonical_framework_knowledge() -> dict[str, Any]:
    """Parte canônica imutável do framework (4 dimensões universais)."""
    return {
        key: FRAMEWORK_KNOWLEDGE[key]
        for key in UNIVERSAL_DIMENSION_KEYS
        if key in FRAMEWORK_KNOWLEDGE
    }


def get_la_dimension_template() -> dict[str, Any]:
    """Template LA — substituído integralmente pela dimensão operacional setorial."""
    return dict(FRAMEWORK_KNOWLEDGE.get(SECTOR_DIMENSION_TEMPLATE_KEY) or {})


def get_framework_taxonomy_for_prompt() -> str:
    """Exporta taxonomia para o prompt da IA (canônico + template LA a substituir)."""
    import json

    payload = {
        "UNIVERSAL_DIMENSION_KEYS_IMMUTABLE": list(UNIVERSAL_DIMENSION_KEYS),
        "SECTOR_DIMENSION_TEMPLATE_KEY": SECTOR_DIMENSION_TEMPLATE_KEY,
        "SECTOR_DIMENSION_TEMPLATE_NOTE": (
            "A dimensão LA abaixo é o MODELO ESTRUTURAL completo (leaf_bloc/leaf_derv por domínio). "
            "Gere a 5ª dimensão setorial SUBSTITUINDO integralmente LA — mesmos domain_key, "
            "mesma granularidade de blocos e entregáveis, conteúdo adaptado ao setor."
        ),
        "CANONICAL_FRAMEWORK_KNOWLEDGE": get_canonical_framework_knowledge(),
        "SECTOR_DIMENSION_TEMPLATE_LA": get_la_dimension_template(),
        "OPERATIONAL_DOMAINS": [
            {"domain_key": key, "domain_name": name} for key, name in OPERATIONAL_DOMAINS
        ],
        "DOMAIN_KEY_ALIASES": DOMAIN_KEY_ALIASES,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


FRAMEWORK_KNOWLEDGE = {
    "SV": {
        "nome": "Visão Compartilhada (SV)",
        "dominios": {
            "ds": {
                "nome": "Digital Strategy",
                "blocos": {
                    "Cenário Prospectivo": "#### Mapa de Cenários Futuros (Future Scenarios Map)\n- Composição: Eixos de Incerteza, Quadrantes de Cenários, Narrativas Detalhadas, Plano de Contingência.",
                    "Análise de Contexto": "#### Matriz de Diagnóstico Digital (Digital Diagnostic Matrix)\n- Composição: Pilar Interno (SW), Pilar Externo (OT), Matriz de Ação (SO, WO, ST, WT).",
                    "Missão Digital": "#### Declaração e Carta de Missão Digital (Digital Mission Statement & Charter)\n- Composição: Propósito, Público-Alvo, Proposta de Valor, Princípios Orientadores.",
                    "Declaração e Matriz de P/O": "#### Matriz e Backlog de Problemas/Oportunidades (P/O Matrix & Backlog)\n- Composição: Declarações de P/O, Matriz de Priorização, Backlog de Iniciativas.",
                    "Backlog de Iniciativas": "#### Backlog de Iniciativas Estratégicas (Strategic Initiatives Backlog)\n- Composição: Iniciativa/Épico, Alinhamento Estratégico, Prioridade, Métricas de Sucesso."
                }
            },
            "bm": {
                "nome": "Digital Business Models",
                "blocos": {
                    "Entendendo as Necessidades de Clientes": "#### Mapa de Empatia e Jornada do Cliente (Empathy Map & Customer Journey Map)",
                    "Competidores e Substitutos": "#### Matriz de Análise Competitiva Digital (Digital Competitive Analysis Matrix)",
                    "Novos Modelos de Negócios": "#### Quadro de Modelo de Negócio Digital (Digital Business Model Canvas)",
                    "Estratégia de Produtos e Serviços Digitais": "#### Roadmap Estratégico de Produtos Digitais (Digital Product Strategic Roadmap)"
                }
            }
        }
    },
    "HC": {
        "nome": "Coração e Conexão (HC)",
        "dominios": {
            "ds": {"nome": "Digital Strategy", "blocos": {
                "Cultura e Clima Digital": "#### Relatório e Plano de Ação de Diagnóstico da Cultura Digital"}},
            "bm": {
                "nome": "Digital Business Models",
                "blocos": {
                    "Implementação de Projetos de Aprendizagem": "#### Plano Estratégico de Aprendizagem Digital",
                    "Programas de Aprendizagem Customizados (B2B)": "#### Portfólio de Ofertas de Treinamento B2B"
                }
            },
            "ic": {"nome": "Innovation Culture",
                   "blocos": {"Mapa da Cultura": "#### Mapa de Alinhamento Cultural (Cultural Alignment Map)"}},
            "dc": {"nome": "Data Culture", "blocos": {
                "Analítica de Desenvolvimento Humano": "#### Dashboard de Perfil e Proficiência (Profile & Proficiency Dashboard)"}},
            "cc": {
                "nome": "Collaboration Culture",
                "blocos": {
                    "Gerenciamento do Relacionamento com Aprendizes": "#### Plataforma de Engajamento e Comunidade (Engagement & Community Platform)",
                    "Gerenciamento de Mídias Sociais e Comunidades": "#### Plano Estratégico de Comunidade Digital (Digital Community Strategic Plan)",
                    "Comunidades de Aprendizes": "#### Plano de Estrutura e Dinamização da Comunidade de Aprendizagem",
                    "Engajamento Alumni": "#### Plano de Programa Alumni Digital (Digital Alumni Program Plan)"
                }
            },
            "dg": {
                "nome": "Digital Governance",
                "blocos": {
                    "Gerenciamento de Comunicação e Campanhas": "#### Plano de Governança de Comunicação Digital",
                    "Captação e Parcerias B2B": "#### Plano de Parcerias Estratégicas para Captação de Talentos",
                    "Programas de Bolsas de Estudo": "#### Manual de Governança do Programa de Bolsas de Estudo",
                    "Financiamento de Mensalidades": "#### Manual de Governança Financeira de Programas Educacionais",
                    "Arrecadação de Fundos e Doação": "#### Plano de Governança de Fundraising e Doações",
                    "Saúde e Bem-estar Mental": "#### Plano de Governança e Ação para Saúde Mental",
                    "Apoio e Retenção de Aprendizes": "#### Plataforma de Suporte e Acompanhamento do Aprendiz"
                }
            },
            "dp": {"nome": "Digital Platforms", "blocos": {
                "Portal de Integração dos Aprendizes": "#### Plataforma de Experiência do Aprendiz (LXP)"}},
            "dc_cap": {"nome": "Digital Capabilities",
                       "blocos": {"Mapa de Talentos": "#### Painel de Gestão Estratégica de Talentos",
                                  "Desenvolvimento Profissional de Docentes": "#### Programa de Excelência Pedagógica e Digital",
                                  "Letramento Digital": "#### Programa de Alfabetização Digital",
                                  "Empregabilidade": "#### Job-Readiness Program",
                                  "Alocação Externa": "#### Career Transition Support Program",
                                  "Educação Continuada": "#### Continuing Education Programs Portfolio"}},
            "dm": {"nome": "Digital Metrics",
                   "blocos": {"Validação de Prontidão Digital": "#### Índice de Maturidade e Prontidão Digital",
                              "Reconhecimento e Credenciamento": "#### Sistema de Certificação e Credenciamento",
                              "Sucesso do Estudante": "#### Dashboard de Sucesso e Impacto do Estudante"}}
        }
    },
    "FS": {
        "nome": "Estrutura Fluida (FS)",
        "dominios": {
            "ds": {"nome": "Digital Strategy",
                   "blocos": {"Caminhos de Crescimento": "#### Mapa Estratégico de Crescimento (C1, C2, C3)",
                              "Modelo Operacional": "#### Mapa do Modelo Operacional (Operating Model Map)"}},
            "bm": {"nome": "Digital Business Models",
                   "blocos": {"Teoria de Negócios": "#### Declaração de Teoria de Negócios (Business Theory Statement)",
                              "Avaliação de Projetos de Aprendizagem": "#### Framework de Avaliação de Impacto (Kirkpatrick)",
                              "Empreendedorismo e Startups": "#### Programa de Inovação Aberta (Open Innovation Program)"}},
            "ic": {"nome": "Innovation Culture",
                   "blocos": {"Times de Inovação": "#### Manual de Governança de Times de Inovação",
                              "Diretorias de Crescimento": "#### Carta de Missão e Framework de Crescimento"}},
            "dc": {"nome": "Data Culture", "blocos": {
                "Analítica de Gestão e Governança": "#### Painel de Controle Estratégico (Strategic Dashboard)"}},
            "cc": {"nome": "Collaboration Culture",
                   "blocos": {"Intercâmbios e Estágios": "#### Plano de Governança de Programas de Intercâmbio",
                              "Parcerias na Indústria": "#### Mapa e Plano Estratégico de Alianças",
                              "Associações Profissionais": "#### Plano de Engajamento em Associações",
                              "Redes de Mentoria": "#### Programa de Mentoria Estratégica"}},
            "dg": {"nome": "Digital Governance",
                   "blocos": {"Sistemas de Governança": "#### Framework de Governança Digital",
                              "Mapa de Processo": "#### Diagrama de Mapeamento de Fluxo de Valor (VSM)",
                              "Financiamento Iterativo": "#### Modelo de Governança de Financiamento Iterativo"}},
            "dp": {"nome": "Digital Platforms",
                   "blocos": {"Canais de Parceria": "#### Plataforma de Gestão de Parcerias"}},
            "dc_cap": {"nome": "Digital Capabilities", "blocos": {"Onboarding": "#### Plataforma de Onboarding Digital",
                                                                  "Simulação Espaço Trabalho": "#### Programa de Aprendizado Baseado em Projetos",
                                                                  "Planejamento Carreira": "#### Programa de Planejamento e Aconselhamento de Carreira",
                                                                  "Apoio Vagas": "#### Centro de Apoio à Carreira e Colocação",
                                                                  "Alocação Interna": "#### Plataforma de Mobilidade e Alocação Interna"}},
            "dm": {"nome": "Digital Metrics",
                   "blocos": {"Validação do Negócio": "#### Painel de Validação de Negócios"}}
        }
    },
    "LA": {
        "nome": "Aprendizagem em Ação (LA)",
        "dominios": {
            "ds": {"nome": "Digital Strategy",
                   "blocos": {"Seleção de Programas": "#### Framework de Curadoria de Aprendizagem",
                              "Promoção de Eventos": "#### Plano de Marketing para Eventos Educacionais",
                              "Análise Necessidades": "#### Relatório de Diagnóstico de Habilidades e Necessidades"}},
            "bm": {"nome": "Digital Business Models",
                   "blocos": {"Elaboração de Projetos": "#### Plano de Design Instrucional e de Negócios"}},
            "ic": {"nome": "Innovation Culture",
                   "blocos": {"Aprendizagem Experiencial": "#### Estrutura de Programa de Aprendizagem Experiencial",
                              "Experiências Digitais": "#### Plano de Design de Experiência de Aprendizagem (LXD Plan)",
                              "Testes e Exames": "#### Sistema de Avaliação Digital e Feedback (Formativa/Somativa)"}},
            "dc": {"nome": "Data Culture", "blocos": {
                "Analítica de Aprendizagem": "#### Plataforma de Analítica de Aprendizagem (Learning Analytics)"}},
            "cc": {"nome": "Collaboration Culture", "blocos": {
                "Integração de Conteúdo": "#### Framework de Curadoria e Análise de Conteúdo (Affordances)"}},
            "dg": {"nome": "Digital Governance",
                   "blocos": {"Aplicação e Admissão": "#### Plataforma de Inscrição e Admissão Digital",
                              "Reconhecimento Aprendizagem Anterior": "#### Manual de Governança de Reconhecimento de Aprendizagem Prévia",
                              "Licenciamento OER": "#### Manual de Governança de Conteúdo Educacional e OER"}},
            "dp": {"nome": "Digital Platforms",
                   "blocos": {"Ambientes AVA/LMS": "#### Plano de Implementação de Ecossistema de Aprendizagem Digital",
                              "Programas Híbridos": "#### Framework de Design Instrucional e Curadoria Híbrida",
                              "Conteúdo Imersivo": "#### Estratégia de Integração de Experiências Imersivas"}},
            "dc_cap": {"nome": "Digital Capabilities",
                       "blocos": {"Criação Conteúdo": "#### Manual de Produção de Conteúdo Digital",
                                  "Pedagogias Digitais": "#### Manual de Metodologias e Didáticas Digitais",
                                  "Aprendizagem Adaptativa": "#### Plano de Design de Experiência de Aprendizagem Adaptativa"}},
            "dm": {"nome": "Digital Metrics",
                   "blocos": {"Validação do Produto": "#### Painel de Desempenho de Produto Educacional",
                              "Avaliação Formativa": "#### Framework de Avaliação e Feedback Contínuo",
                              "Feedback Avaliação": "#### Sistema de Gestão de Feedback"}}
        }
    },
    "DA": {
        "nome": "Arquitetura Digital (DA)",
        "dominios": {
            "ds": {"nome": "Digital Strategy",
                   "blocos": {"Arquitetura Organizacional": "#### Blueprint da Arquitetura Organizacional",
                              "Plano Dívida Técnica": "#### Plano de Gerenciamento de Dívida Técnica"}},
            "bm": {"nome": "Digital Business Models",
                   "blocos": {"Padrões Projetos Aprendizagem": "#### Manual de Padrões Arquiteturais (SCORM/xAPI)"}},
            "ic": {"nome": "Innovation Culture",
                   "blocos": {"P&D Tecnologia": "#### Plano de P&D e Roteiro Tecnológico"}},
            "dc": {"nome": "Data Culture",
                   "blocos": {"Padrões Ciência de Dados": "#### Manual de Governança e Arquitetura de Dados"}},
            "cc": {"nome": "Collaboration Culture",
                   "blocos": {"Padrões Ágeis": "#### Manual de Metodologias Ágeis e Boas Práticas"}},
            "dg": {"nome": "Digital Governance",
                   "blocos": {"Segurança e Redundância": "#### Manual de Governança de Segurança e Resiliência",
                              "Acessibilidade": "#### Manual de Governança e Diretrizes de Acessibilidade Digital",
                              "Identidade e Autenticação": "#### Manual de Governança de Acesso e Identidade",
                              "Privacidade": "#### Manual de Governança de Privacidade de Dados (LGPD)"}},
            "dp": {"nome": "Digital Platforms",
                   "blocos": {"Mapa de Tecnologia": "#### Mapa de Tecnologia e Plano de Transição",
                              "Padrões Corporativos": "#### Manual de Padrões Corporativos de Dados e Tecnologia",
                              "Conectividade e Nuvem": "#### Plano e Arquitetura de Conectividade e Nuvem",
                              "Interoperabilidade": "#### Plano de Governança e Arquitetura de Interoperabilidade",
                              "Arquitetura Modular": "#### Plano e Padrões de Arquitetura de Microserviços",
                              "Relatórios Analítica": "#### Manual de Governança e Padrões de Relatórios de Analítica"}},
            "dc_cap": {"nome": "Digital Capabilities",
                       "blocos": {"Competências Tecnologia": "#### Matriz de Competências Tecnológicas"}},
            "dm": {"nome": "Digital Metrics",
                   "blocos": {"Validação da Solução": "#### Painel de Validação de Soluções e Valor de Negócio"}}
        }
    }
}
