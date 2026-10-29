# Prompt 86 — Contexto da refeição, cervejas e batatas

07/10/2026. Incremento depois do Prompt 85 (`prod-20261007k`). Sem refazer 84/84A. Sem migração. Revisão técnica: `agente-revisao-assistida`. Sem pedido, pagamento ou e-mail real.

## Produção efetiva

| Peça | Valor |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem Loja | `lojadepaes:prod-20261007m` (rollback de app: `prod-20261007k`; `l` foi o primeiro 86; não usar `h`) |
| Bundle | `/assets/index-B1EglQRL.js` |
| Alembic | `f3c9a1b28e04` — sem mudança |
| Regras | `86` |
| Flags | Gigio, vitrine, complementos e pairing on; timeout Hub 4 s |
| Hub marketplace | `marketplace-api` em actionhub.com.br — perfil A Loja agora com `cervejas` e `batatas` |
| Rollback Hub | `/var/lib/leaction-platform/rollback-prompt86-20261007T215042Z` |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

Backup Loja no host: `/opt/lojadepaes/backups/lojadepaes-20261007T215822Z.sql.gz` (e o dump do recreate `n`). Sem cópia do banco local e sem seed comercial.

## Causa comprovada

A captura do proprietário (Queijos / Canastra) não era «não existe cerveja no Mercado Livre».

1. O perfil da Loja no Hub só tinha vinhos, queijos, frios e azeites. A pergunta de hambúrguer com batatas e bebidas não tinha prateleira.
2. `infer_suggested_query` não tinha prato `hamburguer`. «Bebidas» não virava cerveja. O default da mesa desconhecida ainda era vinho/queijo/azeite. A busca padrão de queijos é Canastra.
3. O Gigio falou de pão genérico sem consultar o catálogo publicado (`lookup_products`).
4. Pendências 85A: o agrupamento usava «Mesa de fim de tarde» em todo vinho; URL/cache bastavam para cartão. Agora o cartão exige `availability_verified` da busca ativa do Mercado Livre (`status=active`, instante em `availability_checked_at`). Fallback e consulta falha não viram oferta.

Não houve alteração de receita publicada. Consultoria culinária + seleção contextual.

## Cobertura das categorias

| Categoria | Hub | Verificação | O que entra | O que fica de fora |
|---|---|---|---|---|
| Cervejas | prateleira nova, busca `cerveja pilsen lata` / lager | `availability_verified` + `mercadolivre_search_active` | bebida (lata, long neck, pilsen, lager) | copo, tulipa, camiseta, kit de fabricação, livro |
| Batatas | prateleira nova, busca palito pré-frita e chips | a mesma | alimento: palito/congelada, chips, palha | semente, fatiador, almofada, pegador, brinquedo |
| Queijos | inalterada | a mesma | só se o cliente ou a resposta justificar | não é padrão do hambúrguer |
| Molhos | só orientação | — | — | não virou supermercado |

Primeira leitura do Hub trouxe utensílio/almofada com «batata palito» no título. Filtro de natureza apertado e republicado; a prateleira viva ficou MacCain 600 g + chips, sem fatiador.

## Jornada do hambúrguer (pergunta exata)

«queremos fazer um hamburguer bem legal, com batatas e molho… que tipo de pao… que bebidas…»

| Superfície | Resultado |
|---|---|
| Resposta | Sem pão de hambúrguer no catálogo; adaptação só como sugestão; batatas já da proposta (preparo/formato); cerveja quando cabe; molho culinário |
| CTA | **Ver acompanhamentos sugeridos** — `cats=batatas,cervejas&mesa=hamburguer`. Se o modelo citar azeite no forno, uma volta do browser ainda pode incluir azeites; a API da pergunta exata ficou só cervejas e batatas. |
| Título | **Para o hambúrguer** — um título; sem «Mesa de fim de tarde» e sem copiar o primeiro produto |
| Ofertas verificadas | Pilsen (Aretzbeer, Hollandia, Baden) e batata palito MacCain + chips; links comissionados do Hub |
| Sem álcool | só `batatas` |
| Só as bebidas | só `cervejas` |
| Fritar, não chips | `forma=fritar` |
| Prefiro cerveja | cervejas + batatas (contexto da refeição) |
| Link antigo / não verificado | vitrine vazia (`ids=MLBGHOST`) |

Não foi preciso o cliente dizer «marketplace».

## 85A

| Pendência | Estado |
|---|---|
| Repetir «Mesa de fim de tarde» / primeiro produto no cabeçalho | corrigido — ocasião por categoria (Vinhos, Cervejas, Batatas…) |
| Vitrine só com disponibilidade verificada | corrigido — sem `availability_verified` não há cartão; fallback não autoriza |

## Regressão

| Caso | Produção |
|---|---|
| Sardinhas com homus | Wine Folly + receita; CTA azeites (vinho pedido sem oferta verificada fica no aviso); cerveja da receita **não** abre prateleira de cerveja |
| Mesa de frios | frios, queijos, azeites; sem vinho |
| Nota de guia | Descorchados 95, sem CTA comercial |
| Pedido / pagamento | orientação, sem CTA culinário |

## Prova isolada

Loja `test_prompt86.py` + regressão 85/84/84A/80/77/73: **97 passed** no primeiro lote; nature Hub 19/19. Frontend Accompaniments + Gigio: 16 passed.

## Capturas

| Arquivo | O quê |
|---|---|
| `prod/chat-hamburguer-1440.png` / `390.png` | resposta completa + CTA visível |
| `prod/vitrine-hamburguer-1440.png` / `390.png` | «Para o hambúrguer»; cervejas e batatas reais |
| `prod/chat-sardinhas-1440.png` | regressão 85; sem cerveja como resultado |
| `prod/chat-*.json` / `summary.json` / `catalogs.json` | API ao vivo |

## O que não mudou

Receitas, avaliações de guia, pedidos, pagamentos, fidelidade, endereços, calendário, modelo AWS e credenciais. Sem segundo catálogo na Loja. Sem compra de teste.

## Rollback (independente)

1. Loja: `LOJADEPAES_API_IMAGE=lojadepaes:prod-20261007k` e recreate da API. `l` e `m` são incrementos 86; `k` devolve o 85.
2. Hub: restaurar `$RB/backend` (`rollback-prompt86-20261007T215042Z`) e `pm2 restart marketplace-api`. A Loja `k` ignora prateleiras novas.
3. Só a camada comercial: `LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED=false`. Chat e vitrine genérica permanecem.
