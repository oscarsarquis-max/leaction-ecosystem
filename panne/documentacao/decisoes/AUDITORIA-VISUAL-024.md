# Auditoria visual e funcional — CURSOR-024

Inventário executado sobre o produto local com dados sintéticos. Sem ActionHub e sem dados reais externos.

## Rotas produtivas

Login, callback, organização, início, componentes (ingredientes, estoque, lotes, fornecedores, catálogos), receitas e assistente de receitas, produção (quadro, planos, ordens, execução, ficha, rastreio), conformidade, gestão (custos, compras, inventários) e relatórios.

## Antes

| Superfície | Achado |
|---|---|
| Login | Centro único, sem colunas editoriais, sem fallback de imagem. |
| Shell | Sem acionador global de orientação. |
| Quadro | Fileira permanente de filtros, sem contexto de turno, sem cartões de situação. |
| Assistentes | Gavetas fixas concorrentes em custos, relatórios, rotulagem, estoque e edição. |
| Vazios | Uma frase genérica para filtro, ausência de plano e erro. |
| Cores | Grafite e bege oficiais, mas estados sem oliva/ocre/terracota consistentes. |
| Controles | Selects vazios permanentes; IDs técnicos em alguns filtros. |

## Depois

| Superfície | Mudança |
|---|---|
| Login | Três colunas; centro prioritário; laterais recolhem se o provider falhar. |
| Shell | Botão Assistente; gaveta temporária, minimizável e dispensável. |
| Quadro | Abertura de contexto, faixa compacta, cartões, fluxo/lista/estação, filtros recolhidos. |
| Assistentes | Fluxo específico registra na mesma gaveta; cartão inline não compete com o overlay. |
| Vazios | Contexto ausente, sem plano, filtro vazio, sem acesso, serviço indisponível, erro recuperável. |
| Tokens | Espresso, castanho, caramelo, trigo, creme, areia e semântica AA. |

## Controles adequados

Catálogo em select para estabelecimento/turno/área. Busca única para código ou texto. Chips para visão e filtros. Tabela sempre disponível como alternativa ao fluxo e à estação.
