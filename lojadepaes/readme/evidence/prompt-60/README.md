# Prompt 60 — margens no celular e Gigio

## Telas

| Rota | Papel |
|---|---|
| `/receitas/{slug}` | Leitura da receita |
| `/pedido/novo` | Revisão antes do envio |
| `/pedido/{referencia}` | Confirmação / acompanhamento após envio (fixture isolada) |

## Antes (produção `prod-20261001d`)

| Tela | Causa medida |
|---|---|
| Leitura `/receitas/{slug}` | `main.week-recipe-page` com `padding: 32px 0 64px` zerava o respiro horizontal. A regra de `main { padding: 0 16px }` perdia por especificidade. Título, foto, ingredientes e preparo encostavam na borda. 320/390: `paddingLeft/Right 0`, `firstLeft 0`. |
| Revisão `/pedido/novo` | Já tinha 16 px no `main`. O acionador do Gigio só subia nesta rota; no restante ficava sobre busca/ações. |
| Confirmação `/pedido/{ref}` | Mesma classe `checkout-page` (16 px). Gigio **não** recebia `data-checkout` — o FAB ficava na base e podia cobrir ações. Prova desta tela só em fixture isolada. |
| Home busca | Em 390 px o FAB largo cobria o campo «Receita ou ingrediente…». Pendência do Prompt 59. |
| `main` ≤400 px | `responsive.css` usava 12 px, abaixo dos 16 px pedidos. |

Capturas: `before-recipe-320|390.png`, `before-review-320|390.png`, `before-home-card-320|390.png`, `before-metrics.json`.

## Cartão em destaque (pendência 59)

Referência anterior disponível: `prompt-59/prod-before-metrics.json` (produção `prod-20261001c`) — `max-height` 448 px (`28rem`), foto 252×448, faixa direita 115 px. Depois do 59: `contain`, centro, `fit-content`, cap 320 px, vãos 0.

O 320 px **não** era a medida anterior aprovada; foi escolha do 59 para encurtar a foto. A composição aprovada (foto inteira, texto ao lado, formulário de data aberto no bloco verde, promoção acima, busca abaixo) já estava correta após o 59. Sem divergência visual a corrigir neste ciclo — o cartão **não foi alterado**.

## Correção

- `.week-recipe-page` e `.recipe-archive-page`: respiro lateral `max(16px, safe-area)` no próprio `main`; 0 horizontal só a partir de 721 px (caixa de 720 continua centrada no desktop). Fundo extra para o FAB.
- Checkout/confirmação: 16 px + safe-area; fundo 120 px para as ações rolarem acima do Gigio.
- `responsive.css`: `main`/`header` passam a 16 px em ≤400 px; `scroll-padding-bottom` no documento.
- Gigio: sobe na home e em `/receitas*` (`data-lift`); em `/pedido/*` mantém o recuo de checkout; no celular fechado o rótulo some do pill (fica o avatar, `aria-label` intacto) para não tapar o campo.
- Sem `overflow-x: hidden`, zoom, scale ou redução de fonte. Quantidade editável só na revisão; pedido persistido continua só leitura.

## Isolado

`tests/test_prompt60_browser.py` — 320/390/768/1440. Receita com texto longo, revisão preenchida, pedido fixture. Gutters ≥16, sem overflow, Gigio fora da busca/ações. Cartão 320 + formulário aberto.

## Publicação

Imagem `lojadepaes:prod-20261001f`, bundle `/assets/index-BQUOR5jh.js`. Rollback de app: `prod-20261001d`. Alembic inalterado (`c8e2f1a90b64`). Sem migrate/seed/reset.

Produção pública (320/390): leitura `firstLeft 16`, revisão `firstLeft 16`, home busca sem overlap. Desktop 768/1440: caixa da receita centrada, revisão com 5%. Confirmação persistida só no isolado.
