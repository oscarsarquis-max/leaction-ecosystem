# Prompt 59 — composição da receita em destaque

## Causa comprovada (produção `prod-20261001c`)

`.week-recipe-media` era flex com `justify-content: flex-start` e `align-items: flex-start`. A foto vertical cabia em `max-height: 28rem` (448 px) e ficava encostada à esquerda. Métricas reais: caixa 367×448, imagem 252×448, vão esquerdo 0 e direito 115 — a faixa bege assimétrica da captura. A altura empurrou a busca para baixo do texto curto.

## Correção

Só no cartão (`.week-recipe-media`), sem `object-fit: cover` e sem alterar `.week-recipe-hero`, produtos ou editor:

- imagem centralizada nos dois eixos;
- altura máxima 20 rem (320 px) no desktop e 16,5 rem no cartão estreito;
- coluna da foto em `max-content`, para o retrato não ocupar uma coluna larga;
- breakpoint de empilhar pelo `@container` do cartão.

## Provas

| Tipo | Onde |
|---|---|
| Produção antes | `prod-before-metrics.json`, `prod-before-card-1440.png` |
| Isolada retrato/paisagem/quadrado | `isolated-*-card-1440.png`, `isolated-{1440,1024,768,390,320}.png` |
| Produção depois | `prod-after-metrics.json`, `prod-after-card-1440.png`, `prod-after-1440.png`, `prod-after-390.png` |

Publicado `lojadepaes:prod-20261001d`, bundle `/assets/index-Be2ifFKL.js`. Rollback de app: `prod-20261001c`. Alembic inalterado.

Produção depois: `contain`, altura 320 px, caixa = imagem (180×320), vãos 0/0, busca a 16 px da linha foto/texto. Formulário de data continua aberto.
