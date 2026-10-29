# Prompt 98 — Vitrine na abertura da home (09/10/2026)

Ajuste isolado do frontend. Sem pedido, Agenda, e-mail, pagamento, login ou Hub.

## O que mudou

A foto pequena da massa e o selo “Fermentação natural / Sem pressa, sem atalhos” saíram. No lugar entra a vitrine autorizada (`frontend/images/vitrine da loja.png`), sem gerar outra imagem e sem alterar o original.

“O despertar do levain”, o título “Todo pão tem uma história. Vamos criar a sua?” e o parágrafo à esquerda permanecem.

No desktop a coluna visual ocupa cerca de metade da área útil da abertura (604 / 1240 ≈ 49%). A proporção 1237×646 é respeitada (`object-fit: contain`, `aspect-ratio`). Em tablet e celular, texto e imagem em coluna; a vitrine usa a largura disponível.

## Asset

| Item | Valor |
|---|---|
| Arquivo | `frontend/images/vitrine da loja.png` (original, 925842 bytes, 1237×646) |
| Público | `/images/vitrine%20da%20loja.png` |
| Produção | 200, `image/png`, 925842 bytes, assinatura PNG |
| Alt | Vitrine com pães artesanais |
| Dimensões no HTML | `width={1237}` `height={646}` |

Sem derivado recompresso: o fluxo de assets (`isServedImage`) passou a servir este arquivo no build. Sem caminho Windows no navegador.

## Publicado

| Peça | Versão |
|---|---|
| Loja | `lojadepaes:prod-20261009e` (rollback `prod-20261009d`) |
| Bundle | `/assets/index-CoEF1B--.js` + `index-nODbCDxw.css` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261009T133533Z.sql.gz` |
| Alembic | `d7e0f5a24b38` — sem migração nova |
| Hub / Pay / Agenda / login 97 | intocados |

## Verificação

| Prova | Resultado |
|---|---|
| Local 1440 / 1920 | vitrine ~metade, sem selo, levain e título ok, sem overflow |
| Local 768 / 390 / 320 | uma coluna, imagem na largura útil, sem rolagem horizontal |
| Build | vitrine copiada para `dist/images` (925842 bytes) |
| Vitest App + catalog | ok |
| Produção 1440 e 390 | imagem real 1237×646, composição igual à local |

Capturas: `captures/local-intro-*.png`, `local-fold-*.png`, `prod-intro-*.png`, `prod-fold-*.png`.

## Limitações

- Em 1920 a abertura continua no container de 1240 px (máximo do site). A metade pedida é da área útil, não do viewport.
- A PNG original (~904 KB) entra na primeira dobra; `width`/`height` e `aspect-ratio` evitam salto. Sem biblioteca nova.
- O widget Gigio no canto do celular é o existente; não faz parte deste ajuste.
