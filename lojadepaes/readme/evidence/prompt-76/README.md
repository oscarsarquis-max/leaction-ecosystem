# Prompt 76 — Vitrine compacta de «Para acompanhar seu pão»

06/10/2026. Somente layout e paginação. Sem seed, migração, pedido, e-mail, cobrança ou compra externa.

## Publicado

| Peça | Estado |
|---|---|
| Código Loja | `lojadepaes:prod-20261006k` |
| Rollback de app | `prod-20261006j` (não usar `h`) |
| Bundle | `/assets/index-UyX9NXP6.js` |
| URL | https://lojadepaes.com.br/acompanhar |
| Alembic | `b8e4c1d93f50` (inalterado) |
| Flags | vitrine pública **on**; Gigio complementos **off**; prévia **off** |

## Grade servida (Chrome headless, dados reais do Hub)

| Largura | Colunas | Página 1 | Página 2 | Página 3 | Overflow |
|---|---|---|---|---|---|
| 1440 | 3 | 12 | 12 | 8 | não |
| 1024 | 2 | 12 | 12 | 8 | não |
| 768 | 2 | 12 | 12 | 8 | não |
| 390 | 1 | 12 | 12 | 8 | não |
| 320 | 1 | 12 | 12 | 8 | não |

Capturas em `readme/evidence/prompt-76/prod/`. CTA «Ver no Mercado Livre» visível em todos os tamanhos; paginação Anterior / página atual / total / Próxima depois da grade. Margem móvel 16 px (trilha 358 px em 390; 288 px em 320). Gigio não cobre os botões da página.

## Preservado

Seleção, links e comissão do Hub. Pedidos, pagamentos e fidelidade ligados. Gigio comum ligado; complementos do Gigio desligados. Sem mudança de banco.

## Rollback

`LOJADEPAES_API_IMAGE=lojadepaes:prod-20261006j` e `docker compose up -d --force-recreate api`. Sem reverter migração.
