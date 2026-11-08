# BLOG-010 — retorno

Data: 08/11/2026. A parte 2 parou no teste. As partes 3 e 4 não foram feitas.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Cherry-pick do `249541b4` no `main` e push | **Feito.** Hash `b45e4e00`. |
| 2 | `tsc`, testes de (a) e do CMS, merge e push | **Não feito até o fim.** O `tsc` passou. Um teste falhou. Não houve merge nem push do Hub. |
| 3 | Comparação de `sha256` e proposta do script | **Não feito.** |
| 4 | Regras de SSH do Hub | **Não feito.** |
| 5 | Este retorno, commit e push | **Feito** neste commit. |

## 1. Commit da Loja

O cherry-pick de `249541b4` entrou no `main` como `b45e4e00` (`lojadepaes: o Caddy importa os sites por pasta [BLOG-009]`). No `main` esses três arquivos não existiam, então o cherry-pick os criou: `lojadepaes/infra/caddy/Caddyfile` (com `import /etc/caddy/sites/*.caddy`), `lojadepaes/infra/caddy/sites/.gitkeep` e `lojadepaes/infra/docker-compose.prod.yml` (monta `./caddy:/etc/caddy:ro`).

Push: `09509dfc..b45e4e00` em `origin/main`.

`feat/actionfinance-extrato-032` continua em `249541b4`. A branch não foi reescrita. Ela está 1 commit à frente de `origin/feat/actionfinance-extrato-032` e não foi enviada.

## 2. Hub

Em `sync/producao-20261108`, a partir de `bcedc024`, os arquivos de (a) foram copiados da produção. Os 28 de (b) ficaram como estão no `main`. `frontend/action-hub/src/lib/admin-api.ts` ficou na versão da produção, com `revenue?: number` e os campos de cobrança. `next-env.d.ts` já era igual ao `main` e não entrou no commit.

Commit local, sem push e sem merge: `91f6b5e8`. São 68 arquivos (7806 inserções, 380 remoções).

`npx tsc --noEmit` no frontend do Action Hub saiu 0. A única ocorrência de `revenue` no `src` é o campo opcional em `admin-api.ts`. Nada mais foi ajustado.

Testes: 90, 89 passaram, 1 falhou.

Passaram os de checkout, créditos, assinatura, Spider Pay, admin (a listagem em `pay-regression` e o `PaymentsOps` coberto por esse arquivo), CMS (`cms-posts`, `cms-lepain-patch`, `cms-lepain-instagram-patch`, `cms-panne-keys`, `cms-media-url`) e os três da Loja no frontend.

Falhou `services/gateway-api/domain/pay-regression.test.js`, no teste `sessão/plano continua em valor_negociado e não é confundida com checkout avulso`. Esperava `item.paidAmountAbsent === true`. O valor foi `undefined`.

`publicListItem` em `spider-pay-lookup.js` só define `paidAmountAbsent` quando o pago está confirmado. Sem confirmação, o campo não entra no objeto. O `spider-pay-lookup.test.js` da mesma cópia da produção espera exatamente isso: o campo ausente. Os dois arquivos vieram da produção. Não é um arquivo do `main` misturado no lugar.

Por isso o merge no `main` não foi feito e a branch `sync/producao-20261108` não foi enviada.

## 3 e 4

Não comparei com o servidor e não alterei o SSH do Hub. A porta 22 segue como ficou no BLOG-009: aberta para a internet. A regra desta sessão continua fora.
