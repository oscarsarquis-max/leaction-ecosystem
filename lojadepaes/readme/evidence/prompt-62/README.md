# Prompt 62 — margens no detalhe do pão

## Rota real

Captura do proprietário = **produto da vitrine**, não receita editorial.

| | |
|---|---|
| Produto | Pão de Canela (Cinnamon Bread) |
| Rota | `/paes/pao-de-canela-cenemon-bread` |
| Bundle antes | `/assets/index-BQUOR5jh.js` (`prod-20261001f`) |

O mesmo defeito aparece em `/paes/pao-de-frutas-arabian-bread`.

## Causa

`main.product-page` com `padding: 32px 0 64px`. O shorthand zera as laterais e ganha de `main { padding: 0 16px }`. Bounding boxes em 320/375/390/430: título, foto, textos e opções com `left: 0`. Não é cache.

O Prompt 60 corrigiu `.week-recipe-page` / checkout; esta classe ficou de fora.

## Correção

Mesmo padrão da receita, no componente compartilhado: laterais `max(16px, safe-area)` até 720 px; 0 horizontal a partir de 721 px (desktop/tablet como estavam). Fundo extra e Gigio com `data-lift` em `/paes/`. Sem overflow-x hidden, zoom ou fonte menor.

## Navegadores

Chromium Playwright emulado (320/375/390/430/768/1440). WebKit Playwright **indisponível** neste Windows. **Não** houve teste em iPhone físico nem Safari real.

## Publicação

Imagem `lojadepaes:prod-20261001g`, bundle `/assets/index-DiwRvsMb.js`. Rollback de app: `prod-20261001f`. Alembic `c8e2f1a90b64` inalterado. Sem migrate/seed/edição de produto.

Produção 320/375/390/430 (Chromium emulado): Pão de Canela e Pão de Frutas com 16 px reais nos bounding boxes (foto ~17 px pela borda de 1 px). Home → produto: `/paes/pao-de-canela-cenemon-bread`. Desktop 1440: duas colunas preservadas.
