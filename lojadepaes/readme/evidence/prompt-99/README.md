# Prompt 99 — Enquadramento das imagens de receitas (11/10/2026)

Ajuste isolado do cartão de destaque. Sem pedido, pagamento, e-mail, Agenda, login, Hub, vitrine 98 ou alteração de cadastro.

## Causa

Não era margem embutida no arquivo. A sopa publicada (`f669ec51-…`, 552×309, ~16:9) preenche o JPEG. Em produção o quadro `.week-recipe-media` nascia largo e baixo (1440: 552×157, razão 3,52) e a foto usava `object-fit: contain` (280×157), deixando faixas laterais.

## O que mudou

Só o cartão de destaque (`.week-recipe-media` em `WeekRecipeCard`):

- quadro `width: 100%` + `aspect-ratio: 16/9` (reserva espaço, sem altura fixa)
- imagem `object-fit: cover` no escopo do cartão
- `object-position` reutiliza `image_focus` já publicado (`recipeImagePosition`)
- duas colunas só com `@container week-recipe (min-width: 36rem)`

A página de leitura (`.week-recipe-hero`) permanece `contain` e mostra a foto integral. A listagem/acervo continua só texto. Sem seletor global `img`. Originais e cadastros intactos.

## Receitas publicadas (as três)

| Receita | Arquivo | Intrínseco | Foco | Superfície conferida |
|---|---|---|---|---|
| Sopa de Cebolas à La Tartine (destaque) | `f669ec51-…` | 552×309 ~16:9 | 50% 50% | cartão + leitura |
| Sardinhas e Homus… | `7ad91013-…` | 960×1280 3:4 | 49% 53% | cartão (swap local) + leitura |
| Pan con Tomate | `fe2f7852-…` | 900×1600 9:16 | 57% 62% | cartão (swap local) + leitura |

Não há foto quadrada publicada. Fixture local `fixture-square.jpg` (400×400), só no cartão, sem cadastro.

## Verificação local

| Prova | Resultado |
|---|---|
| Sopa 1440 antes → depois | 552×157 contain 280×157 → 414×233 cover, `img_fills` true, prato visível, faixas sumiram |
| Sopa 1920 / 768 / 390 / 320 | mesma área 16:9 no breakpoint; coluna no estreito; título, resumo, tempo, rendimento e Ver receita visíveis; sem overflow |
| Sardinhas no cartão | 414×233 cover, foco 49% 53%, torrada e sardinha visíveis; corta o topo do 3:4 |
| Tomate no cartão | 414×233 cover, foco 57% 62%, presunto/prato visíveis; a mão/queijo do 9:16 saem do recorte |
| Quadrado (fixture) | mesma 414×233, preenche sem faixa |
| Leitura das três | `hero_fit: contain`, foto completa |
| Acervo `/receitas` | 0 fotos, 3 títulos |
| Build | `tsc --noEmit && vite build` ok (`index-DOsPT9rj.js`, `index-uGM9IcEh.css`) |
| Vitest | 17 testes de receita/cartão/acervo |
| Produção 1440 / 1920 / 768 / 390 / 320 | sopa 414×233 cover (desktop) / 16:9 na coluna; `img_fills` true; destaque inalterado |
| Produção leitura | sopa 552×309 contain; sardinhas 432×576 contain; tomate 324×576 contain |

## Limitação

Pan con Tomate (9:16) não preenche 16:9 sem corte relevante. O foco publicado mantém o prato; a mão e o queijo ficam de fora no cartão. A leitura continua integral. Não se declarou “todas resolvidas” por uma captura da sopa.

## Publicado

| Peça | Versão |
|---|---|
| Loja | `lojadepaes:prod-20261011a` (rollback `prod-20261009e`) |
| Bundle | `/assets/index-DsWTwRWr.js` + `index-uGM9IcEh.css` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261011T194521Z.sql.gz` |
| Alembic | `d7e0f5a24b38` — sem migração nova |
| Vitrine 98 / pães / marketplace / logos / Gigio / Agenda / pedidos / Pay | intocados |
