"""Guia público da Panne Demo — conteúdo versionado (sem segredos)."""

from __future__ import annotations

from typing import Any

GUIDE_SCHEMA_VERSION = 1
GUIDE_CONTENT_VERSION = "r028-003"

# Totais de referência (fallback versionado). Nunca inventar zero quando a fonte falha.
FALLBACK_COUNTS: dict[str, Any] = {
    "source": "fallback",
    "updated_at": None,
    "note": "Contagens de referência; a API tenta atualizar ao vivo na demo.",
    "organizations": [
        {
            "slug": "panne-demonstracao",
            "display_name": "Panne Demonstração",
            "role": "principal",
            "counts": {
                "produtos": 12,
                "produtos_ativos": 12,
                "produtos_inativos": 0,
                "ingredientes": 18,
                "receitas": 6,
                "planos": 10,
                "ordens": 10,
                "fornecedores": 4,
                "lotes": 6,
                "saldos": 6,
                "movimentos": 7,
                "entradas_fiscais": 0,
                "perfis_disponiveis": 7,
            },
        },
        {
            "slug": "padaria-horizonte-demo",
            "display_name": "Padaria Horizonte Demo",
            "role": "isolamento",
            "counts": {
                "produtos": 0,
                "produtos_ativos": 0,
                "produtos_inativos": 0,
                "ingredientes": 1,
                "receitas": 0,
                "planos": 0,
                "ordens": 0,
                "fornecedores": 0,
                "lotes": 0,
                "saldos": 0,
                "movimentos": 0,
                "entradas_fiscais": 0,
                "perfis_disponiveis": None,
            },
        },
    ],
    "totals": {
        "produtos": 12,
        "produtos_ativos": 12,
        "produtos_inativos": 0,
        "ingredientes": 19,
        "receitas": 6,
        "planos": 10,
        "ordens": 10,
        "fornecedores": 4,
        "lotes": 6,
        "saldos": 6,
        "movimentos": 7,
        "entradas_fiscais": 0,
        "perfis_disponiveis": 7,
    },
}


def static_guide_body() -> dict[str, Any]:
    return {
        "schema_version": GUIDE_SCHEMA_VERSION,
        "content_version": GUIDE_CONTENT_VERSION,
        "title": "Guia da demonstração Panne",
        "what_is": {
            "purpose": (
                "A Panne organiza o fluxo produtivo de padarias e ateliers: "
                "compras e estoque, produtos e receitas, planejamento, ordens, "
                "execução, rotulagem e custos — com revisão humana nos pontos críticos."
            ),
            "flow": (
                "O mapa do caminho crítico em /fluxo distingue a visão geral da "
                "organização (preparação) da jornada de um produto (código público). "
                "“Você está aqui” é a primeira etapa que ainda impede o avanço; "
                "clicar numa etapa só muda o foco de consulta."
            ),
            "data_nature": (
                "Todos os dados desta demonstração são fictícios. Não representam "
                "padaria real, fornecedor real nem obrigação legal."
            ),
            "shared": (
                "Este é um ambiente compartilhado de homologação. Outros avaliadores "
                "podem alterar os mesmos registros."
            ),
            "not_production": (
                "Não há relação com o banco nem com a aplicação de produção da Panne."
            ),
        },
        "scenario": {
            "anchor_date_label": "24/08/2026",
            "primary_organization": "Panne Demonstração",
            "isolation_organization": "Padaria Horizonte Demo",
            "establishment_hint": "Use o estabelecimento padrão sugerido ao abrir o fluxo.",
            "shift_hint": "O turno do cenário de demonstração é o do dia âncora.",
            "areas_with_data": [
                "Fluxo produtivo",
                "Compras e entradas",
                "Ingredientes e estoque",
                "Produtos e receitas",
                "Planejamento e ordens",
                "Execução / preparo",
                "Conformidade e rotulagem",
                "Custos e preços",
                "Relatórios",
            ],
        },
        "profiles": [
            {
                "id": "owner",
                "label": "Proprietário",
                "purpose": "Visão completa para avaliar o produto de ponta a ponta.",
                "areas": "Quase todas as áreas, inclusive troca de organização e custos.",
                "actions": "Consultar e, se desejar, executar o roteiro completo com mutações.",
                "limits": "Continua em ambiente compartilhado; alterações afetam outros homologadores.",
            },
            {
                "id": "manager",
                "label": "Gestor de produção",
                "purpose": "Operar o chão de fábrica e o turno.",
                "areas": "Fluxo, planejamento, ordens, execução e estoque operacional.",
                "actions": "Acompanhar e executar produção conforme as permissões do perfil.",
                "limits": "Sem o recorte completo de custos e conformidade do proprietário.",
            },
            {
                "id": "formulator",
                "label": "Técnico / formulador",
                "purpose": "Trabalhar ingredientes e receitas.",
                "areas": "Componentes, receitas e assistente de formulação.",
                "actions": "Consultar e editar formulações quando permitido.",
                "limits": "Foco técnico; menos ênfase em compras e turno.",
            },
            {
                "id": "baker",
                "label": "Padeiro",
                "purpose": "Executar o que o turno pede.",
                "areas": "Quadro, ordens e execução.",
                "actions": "Registrar preparo e seguir fichas.",
                "limits": "Sem preço de compra nem gestão ampla.",
            },
            {
                "id": "reviewer",
                "label": "Revisor regulatório",
                "purpose": "Avaliar rotulagem e dossiês.",
                "areas": "Conformidade, dossiês e avaliações.",
                "actions": "Revisar e registrar pareceres humanos.",
                "limits": "Não publica certificação automática.",
            },
            {
                "id": "buyer",
                "label": "Comercial / compras",
                "purpose": "Percorrer necessidades, cotações e recebimentos.",
                "areas": "Compras, fornecedores e entradas.",
                "actions": "Consultar e registrar movimentações de compra quando permitido.",
                "limits": "Sem o recorte completo de formulação e conformidade.",
            },
            {
                "id": "reader",
                "label": "Leitor",
                "purpose": "Somente leitura do que o perfil enxerga.",
                "areas": "Telas permitidas em modo consulta.",
                "actions": "Navegar e imprimir o que estiver liberado.",
                "limits": "Não altera cadastros nem estoque.",
            },
        ],
        "roadmap": [
            {
                "step": 1,
                "title": "Entrar como Proprietário",
                "path": "/entrar",
                "requires_session": False,
            },
            {
                "step": 2,
                "title": "Escolher Panne Demonstração",
                "path": "/organizacao",
                "requires_session": True,
            },
            {
                "step": 3,
                "title": "Começar roteiro no mapa do caminho crítico",
                "path": "/fluxo",
                "requires_session": True,
            },
            {
                "step": 4,
                "title": "Distinguir visão geral e jornada de produto com o Gigio",
                "path": "/fluxo",
                "requires_session": True,
            },
            {
                "step": 5,
                "title": "Consultar compras e entrada fiscal",
                "path": "/gestao/compras/entradas",
                "requires_session": True,
            },
            {
                "step": 6,
                "title": "Conferir ingredientes e estoque",
                "path": "/componentes/estoque",
                "requires_session": True,
            },
            {
                "step": 7,
                "title": "Consultar produtos",
                "path": "/produtos",
                "requires_session": True,
            },
            {
                "step": 8,
                "title": "Consultar receitas",
                "path": "/receitas",
                "requires_session": True,
            },
            {
                "step": 9,
                "title": "Abrir planejamento e ordens",
                "path": "/planejamento",
                "requires_session": True,
            },
            {
                "step": 10,
                "title": "Acompanhar preparo e execução",
                "path": "/ordens",
                "requires_session": True,
            },
            {
                "step": 11,
                "title": "Consultar rotulagem",
                "path": "/conformidade",
                "requires_session": True,
            },
            {
                "step": 12,
                "title": "Consultar custos e preços",
                "path": "/gestao/custos",
                "requires_session": True,
            },
            {
                "step": 13,
                "title": "Trocar para Padaria Horizonte Demo (isolamento)",
                "path": "/organizacao",
                "requires_session": True,
            },
            {
                "step": 14,
                "title": "Sair",
                "path": "/entrar",
                "requires_session": False,
            },
        ],
        "safe_actions": {
            "consult": [
                "Abrir telas e detalhes",
                "Usar filtros e buscas",
                "Consultar relatórios e impressões",
                "Trocar de perfil (após sair) ou de organização",
                "Abrir o Gigio para orientação",
            ],
            "mutates_shared": [
                "Criar ou editar produto",
                "Registrar entrada de mercadoria",
                "Confirmar conferência física",
                "Movimentar estoque",
                "Criar ordem de produção",
                "Executar produção",
                "Alterar receita",
                "Publicar ou avançar rotulagem",
                "Mudar custos ou preços",
            ],
            "shared_notice": (
                "Antes de uma alteração relevante, lembre: este ambiente é compartilhado. "
                "A funcionalidade permanece disponível; a indicação é proporcional."
            ),
        },
        "integrations": [
            {
                "name": "CMS Action Hub (colunas de /entrar)",
                "state": "ativo",
                "detail": "Casca editorial da página de acesso; não controla login nem o guia operacional.",
            },
            {
                "name": "Fazenda / DistDFe",
                "state": "preparado_desativado",
                "detail": "Código preparado; integração ao vivo desligada nesta demo.",
            },
            {
                "name": "Documentos fiscais sintéticos",
                "state": "simulado",
                "detail": "Disponíveis para simular entrada e conferência sem SEFAZ real.",
            },
            {
                "name": "Certificado A1 real",
                "state": "indisponivel",
                "detail": "Não configurado; fiscal real fica fora deste recorte.",
            },
            {
                "name": "OCR / Textract real",
                "state": "preparado_desativado",
                "detail": "Leitura automática de anexo não está ativa na demo.",
            },
            {
                "name": "Autenticação corporativa / OIDC",
                "state": "indisponivel",
                "detail": "A demo usa perfis prontos sem senha; OIDC não é usado aqui.",
            },
            {
                "name": "IA generativa em nuvem",
                "state": "indisponivel",
                "detail": "Assistente de receitas com IA generativa não está ligado neste ambiente.",
            },
            {
                "name": "Banco de produção",
                "state": "indisponivel",
                "detail": "Somente panne_demo; o banco panne de produção não é utilizado.",
            },
        ],
        "limitations": [
            "Criação de nova separação ainda pode estar indisponível na tela.",
            "Integração fiscal real depende de certificado A1 — não configurado nesta demo.",
            "Combos, mistos e sub-receitas avançadas seguem o estado real do recorte (podem estar incompletos).",
            "Dados podem ser alterados por outros homologadores a qualquer momento.",
            "Restauração/reset da demo, quando houver, é operação de equipe — não automática pelo avaliador.",
        ],
        "version": {
            "label": "Panne Demo · CURSOR-028",
            "environment": "demo",
            "anchor_date_label": "24/08/2026",
            "published_hint": "Consulte o carimbo de publicação no detalhe técnico recolhido, quando disponível.",
        },
    }


def unavailable_count() -> None:
    """Sentinel: ausência ≠ zero. Representado como null no JSON."""
    return None
