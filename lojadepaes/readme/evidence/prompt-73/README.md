# Prompt 73 — Para acompanhar seu pão

Estrutura pronta, **desligada**. Nenhum complemento autorizado foi publicado. A adaptação no Hub é **seleção configurada por perfil** (categorias/termos), não IA nem tabela local fingindo curadoria adaptativa.

## Contrato efetivo do ActionHub

| Peça | O que existe | O que não existe |
|---|---|---|
| Plugin | Flask `:4012` `GET /api/marketplace/offers` e `/vitrine` | ETA/frete confiável |
| Origem | Header `X-ActionHub-App-Id` (servidor). Query `origin` só na allowlist publicada. | Referer ou parâmetro público para coleção privada |
| Perfil legado | Sem header → `formacao`, `equipamentos`, `software` (TI) | Troca global por alimentos |
| Perfil A Loja | App id `lojadepaes` → `vinhos`, `queijos`, `frios`, `azeites` | Publicação automática de todo retorno |
| Educação | Fixture `educacao` / `livros`, **não publicada** | Integração educacional |
| Desconhecida | 400 + `offers: []` + `shelves: []` | Vazamento do legado ou da Loja |
| Link | URL exata do Hub (`link`), query preservada. Amazon: `DetailPageURL` / PartnerTag quando o Hub já devolve. | Código de afiliado inventado na Loja. Busca `lista.mercadolivre.com.br` não vira oferta |
| Preço/imagem | `price`, `currency`, `price_label`, `image` | Estoque, frete, prazo de entrega |

Não houve scraping nem integração paralela com Mercado Livre ou Amazon. A Loja não altera checkout, credenciais ou tema global do Hub.

## Quem edita o quê

| Lugar | O que o proprietário edita | Origem da informação pública |
|---|---|---|
| ActionHub → Marketplace → curadoria do perfil A Loja | Categorias, termos, inclusões/exclusões, ordem | Produto, foto, preço, disponibilidade conhecida, destino comissionado, CTA (ML ou Amazon) |
| Loja → Produtos → Complementos | Ocasião, história, por que combina, dica, slugs de pães/receitas | Narrativa e associações. **Não** preço, produto ou link |
| Site / Gigio | Nada comercial | Consomem o perfil Hub + overlay da Loja |

## Como a Loja consome

- Backend `GET /api/v1/accompaniments` e `/for-product/{slug}` → `GET {ACTIONHUB_MARKETPLACE_URL}/vitrine` com `X-ActionHub-App-Id: lojadepaes`. Timeout ≤ 2 s, cache 5 min, falha isolada.
- Sem app id a Loja **não** chama o Hub (evita receber o legado de TI).
- Tabela `accompaniment_items` permanece como overlay narrativo; não é catálogo concorrente e não foi apagada.
- Flags, ambas `false` por padrão: `LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED`, `LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED`.
- CTA nomeia o destino real: **Ver no Mercado Livre** ou **Ver na Amazon**.
- Fallbacks `fallback-*` e páginas de busca do ML não entram na vitrine.

## Experiência (código, não publicada)

- Rota `/acompanhar`, identidade da Loja, retorno à página principal.
- Chamada na home depois da grade de pães, só com flag pública **e** itens reais do perfil.
- Detalhe do pão: bloco secundário só com associação da overlay.
- Gigio: `lookup_accompaniments`, orçamento de 2 rodadas. Flag própria.
- Prazo: a API não traz estimativa. Ajuda honesta: conferir no destino e, se quiser, informar a data que o cliente viu.

## Isolamento e reversão

- Flags desligadas: API pública vazia, sem CTA, Gigio sem oferta. Pedidos, pagamento e fidelidade intocados.
- Falha do Hub não impede catálogo, `/operations` nem rascunho de pedido; a vitrine some, sem snapshot local como oferta atual.
- Rollback de app: voltar `prod-20261006g`. A tabela pode permanecer; a aplicação anterior a ignora.
- Desligar: as duas flags em `false`, sem reverter dados comerciais.
- Produção em 06/10/2026 permanece `prod-20261006g`. SSH `:22` em `52.15.107.86` continua inacessível (TCP timeout). A imagem local antiga `h` era a primeira tentativa (catálogo local) e **não** deve ser publicada; esta revisão ainda não gerou imagem nova porque o host não responde.

## Provas isoladas

- Hub `test_origin_profiles.py` — legado TI, Loja culinária, origem desconhecida/educação, fallback de vinho sem notebook.
- Loja `tests/test_prompt73.py` — flags off, atribuição da query, Amazon CTA, overlay não compete, URL inválida/busca, preço ausente, Hub lento, pão rascunho, Gigio, admin recusa ID fora do perfil.
- Regressão: Prompt 72, 71, Gigio, storefront, fidelidade.

Sem compra no Mercado Livre ou Amazon, sem e-mail, sem pedido de teste em produção.
