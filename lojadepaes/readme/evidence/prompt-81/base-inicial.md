# Base inicial para revisão editorial (rascunho)

Consulta das fontes: 2026-10-07. Todas em **rascunho**. Nenhuma é «Escolha de A Loja».  
Flag `LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=false` — o chat público **não** alega consulta especializada.

Editar em `/admin/produtos/gigio/harmonizacoes`. Publicar exige nome do responsável.

## 1. Tinto do Dão com leitão assado

- Chave: `wine-dao-leitao` · vinho · estilo
- Fonte comercial: [Vinhos do Dão](https://www.evino.com.br/blog/vinhos-do-dao/) — Redação Evino, 2026-04-23
- Relação: blog da varejista
- Síntese: a redação descreve vinhos do Dão como tintos de acidez presente e taninos geralmente moderados, e aponta o leitão assado como prato típico da região. Isso descreve um estilo/região, não a qualidade de uma garrafa específica.
- Características: acidez presente e taninos geralmente moderados *segundo a fonte*; corpo e intensidade não informados.
- Uso: bebida da refeição com leitão/porco. Não transfere qualidade a qualquer tinto do Hub.

## 2. Estilos para porco no churrasco

- Chave: `wine-churrasco-porco` · vinho · estilo
- Fonte comercial: [Vinhos e churrasco](https://www.evino.com.br/blog/vinhos-e-churrasco/) — Redação Evino, 2026-01-18
- Síntese: o artigo associa carnes de porco e linguiça a estilos como Lambrusco e Cabernet Franc. Orientação de categoria/estilo, não avaliação de SKU ou safra.
- Não autoriza citar uma marca que a fonte não nomeia.

## 3. Harmonização no produto, não como nota geral

- Chave: `wine-pairing-per-product` · vinho · geral
- Fonte comercial: [Central de Ajuda Evino](https://ajuda.evino.com.br/hc/pt-br/articles/360001678028-Como-faco-para-saber-os-pratos-corretos-para-harmonizar-com-os-vinhos) — 2025-09-25
- Síntese: a sugestão de pratos aparece na página de cada vinho. Método de consulta por produto, não nota de excelência nem lista universal.
- Não fundamenta correspondência específica de oferta do Hub.

## 4. Queijo Canastra com indicação geográfica

- Chave: `cheese-canastra-ig` · queijo · estilo
- Fonte independente: [Ficha INPI IG201002](https://www.gov.br/inpi/pt-br/servicos/indicacoes-geograficas/arquivos/fichas-tecnicas-de-indicacoes-geograficas/Canastra.pdf) — depósito 13/03/2012, alteração 17/09/2024
- Síntese: a IG identifica queijo produzido na Serra da Canastra, MG. Não é nota de excelência nem certifica um anúncio.
- Textura e maturação de um SKU: não informado.
- Salame ou frio com «queijo» no nome não é queijo Canastra.

## 5. Caracterização de azeites extra virgem brasileiros

- Chave: `oil-azeite-brasileiro-embrapa` · azeite · geral
- Fonte independente: [projeto Embrapa](https://www.embrapa.br/busca-de-projetos/-/projeto/211164/caracterizacao-de-azeites-de-oliva-extra-virgem-brasileiros)
- Data da fonte: não informada na página consultada
- Síntese: documenta que a classe extra virgem é objeto de pesquisa. Não atribui qualidade certificada a um azeite à venda no Hub.

## Critérios de correspondência (já no código)

1. Natureza correta (eliminatório).
2. Compatibilidade de perfil comprovável no anúncio.
3. Completude dos dados.
4. «Escolha de A Loja» só com revisão e publicação registradas.

Estilo não certifica garrafa. Safra divergente não herda análise. Comissão não entra no juízo.

## O que ainda não está ativo

- Alegação pública de consulta especializada
- Parceria Evino ou certificação de sommelier
- Crawler, pesquisa aberta por conversa, nota numérica de excelência
