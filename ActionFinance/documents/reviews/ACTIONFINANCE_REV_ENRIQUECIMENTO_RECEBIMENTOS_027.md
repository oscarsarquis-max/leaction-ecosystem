# Enriquecimento dos recebimentos — 027

Data: 15/10/2026. Baseline AF-BL-023 revisão 1.1. Produto publicado neste incremento: **0.1.1**. Aceite do proprietário: **não atribuído**. A prova autenticada de persistência ainda não foi executada.

## Causa

Os 11 recebimentos de produção já estavam gravados com valor cobrado e status, e sem pago, aplicação, pagador, método, processador ou classificação. A imagem da Spider em execução (`sha256:ca0cdfdd…`) não copiava esses campos. O arquivo de lista publicado no Hub também não os expunha. A última tentativa pública, `1f159934-4b30-446c-8c2c-3f84176e3025`, ficou `EMPTY` com uma página e zero gravações. A tentativa `b39468f1-3ab2-4396-b070-15514fb34ee4` permanece `FAILED`. Nenhuma das duas foi reescrita.

A origem do pagamento `b6cf9b7a-d8d3-42a7-873e-818f17133322`, lida em `leaction_hub` no host efetivo `paneldx-database`, confirma o que o Finance ainda não gravou.

## Alterações

Revisão do item de resposta: **2026-10-15**. Ela é aditiva e independente do envelope. As requisições continuam 1.3 (consulta) e 1.4 (lista). A versão 1.5 permanece da biblioteca e não foi reutilizada. Não há `contractVersion` novo obrigatório.

| Componente | O que mudou |
|---|---|
| Hub | `spider-pay-lookup.js` só emite `paidAmountMinor` quando `paid_amount_confirmed` é verdadeiro. Aplicação, descrição, pagador, método, processador e classificação saem de registro ou payload com motivo. `PRODUCTION` do envelope não classifica o pagamento. |
| Spider | Só a classe `ActionHubPayListIdentity` e o teste. Lista explícita de campos. Pago omitido não envia `paidAmountAbsent`. Núcleo, autenticação, isolamento, outras capacidades, WAF, projector, query e Monitor não foram alterados. |
| Finance 0.1.1 | A omissão não apaga pago, aplicação ou pagador já gravados. A mesma revisão preenche lacuna e não substitui pago confirmado. `ABSENT` de pagador não revoga e-mail já conhecido. `INDETERMINATE` não rebaixa `REAL`/`TEST`. Repetição idêntica não conta atualização. `EMPTY` com página recebida diz que a origem respondeu e nenhum campo novo foi gravado. `EMPTY` não entra mais como último sucesso. Schema permanece V20. |

Dinheiro publicado continua na representação já aceita pelo consumidor. No banco, `amount_minor` é numérico. A lista da Spider continua enviando dígitos em texto, como já fazia o campo cobrado.

## Testes executados

| Suíte | Resultado |
|---|---|
| `PayReceiptSyncMergeTest` | 10 testes, sucesso |
| `PayReceiptSyncIT` | 9 testes, sucesso, inclusive produtor enriquecido, pago diferente do cobrado, pendências e repetição |
| `PayReceiptsPage.test.tsx` | 6 testes, sucesso |
| `ActionHubPayListIdentityTest` | 1 teste, sucesso |
| `spider-pay-lookup.test.js` | 18 testes no local e 18 no servidor antes do restart |

Os identificadores de teste são sintéticos. O UUID real do pagamento de R$ 90 não entrou em fixture.

## Testes não executados

- Clique autenticado em Sincronizar e a recarga da lista/detalhe.
- `mvn verify` completo e a suíte inteira da Spider.
- Sonda direta Finance → Hub ou Mercado Pago. Não substitui a prova da interface.
- APPLY, títulos, baixas, movimentos ou ajuste de saldo.

## Artefatos publicados

| Peça | Anterior | Publicado |
|---|---|---|
| Finance | `actionfinance-web:14` · `sha256:cb0619f2f1b4b38c86da43298cc11cd1979dbe25dc4dc5f25c1f6533072c528a` · SPA `index-CRjEQs1k.js` · produto 0.1.0 | `actionfinance-web:15` · `sha256:61cf094d2673d2344c293612b484e2c16cdb2d7cdc1458eebdab17a936e628cc` · SPA `index-UhuYx_ma.js` · produto 0.1.1 |
| Spider runtime | `spider-runtime-prod:3` · `sha256:ca0cdfdd0494499759c2f059c883e73039453df8e19d3e1ba0c073fe95bd9430` | `spider-runtime-prod:4` · `sha256:d116496379aff3c341682908f2ac7fef5ac06dd46ab59fbf332a2c22cad8bec0` |
| Hub | `spider-pay-lookup.js` sem `commercialApplication` | o mesmo arquivo com `confirmedPaid`; cópia anterior em `/tmp/spider-pay-lookup.js.pre027` |

Conferido depois da publicação: `GET /api/v1/system/info` devolve `version=0.1.1`, `RECEIPT_SYNC`, sincronização ligada. Spider `GET /actuator/health` 200. Gateway `GET /health` 200. Query e projector da Spider permaneceram na revisão 3, desired 1. Runtime desired 2, rollout concluído, healthy percent mínimo 100. Flyway do Finance continua em V20. Nenhuma migration nova.

## Caso R$ 90 — origem conferida, armazenamento ainda antigo

Origem `public.orders` em `leaction_hub`, lida pelo gateway já publicado. E-mail do pagador existe e não foi copiado para este relato.

| Campo | Origem em 15/10/2026 | Finance PRODUCTION antes da nova sincronização |
|---|---|---|
| Identidade | `b6cf9b7a-d8d3-42a7-873e-818f17133322` | o mesmo `transaction_id` (id do pedido) |
| Status | `PAID` | `CONFIRMED` |
| Cobrado | `amount_cents` 9000 | 9000 |
| Pago | `paid_amount_cents` 9000 e `paid_amount_confirmed=true` | nulo, `paid_amount_absent=true` |
| Classificação | `live_mode=true` | `INDETERMINATE` |
| Aplicação | `app_id=lojadepaes` | nula |
| Descrição | produto `Checkout avulso por valor`, sku `AMOUNT_CHECKOUT` | nula |
| Pagador | e-mail do usuário presente; `customer_email` no payload | `payer_kind` nulo |
| Método | `pix` | nulo |
| Processador | `mp_payment_id` presente e `pix` presente; nome explícito ausente | nulo |
| Revisão | `updated_at` 2026-10-06T15:01:49.498Z | a mesma |

A lacuna atual está no armazenamento do Finance, porque a sincronização que usaria o caminho publicado ainda não rodou. A origem tem o pago confirmado de 9000. Este relato não trata esse valor como já exibido na lista.

## Cardinalidade

O escopo `lojadepaes` na origem tem 12 pedidos. O Finance de produção tem 11. O pedido ausente no Finance é `a9578147-7a25-4a98-ba68-a0216aa8ed73`, `PENDING`, `updated_at` 2026-10-09, sem `amount_cents` na leitura. Os outros 11 ids coincidem, inclusive `a6f7fc4e-9c40-4f23-9ae9-67a0c296f87a` (cobrado 7000, já armazenado, `paid_amount_confirmed=true` na origem). Os 11 não são um limite. Homologação tem outros 4 registros, separados.

Títulos 0, baixas 0, movimentos de caixa 0.

## Efeitos financeiros

Nenhum título, baixa, movimento ou ajuste de saldo foi criado. Reimportar observação não dispara esses efeitos. Despesa compartilhada permanece não atribuída. Rateio não foi implementado.

## Rollback

| Peça | Retorno | Efeito nos dados |
|---|---|---|
| Finance | recolocar `actionfinance-web:14` / `sha256:cb0619f2…` | a imagem antiga não apaga V20 nem linhas já enriquecidas |
| Spider | recolocar `spider-runtime-prod:3` / `sha256:ca0cdfdd…` | o runtime volta a omitir os campos novos; projector e query não entram |
| Hub | restaurar `/tmp/spider-pay-lookup.js.pre027` e `pm2 restart gateway-api` | a lista volta a omitir a revisão de resposta |

Interromper se a lista perder registros, misturar empresa, criar título/baixa/movimento, ou se a sincronização falhar de contrato. O circuito do ECS está com rollback automático. Não há migration para desfazer.

## Prova que ainda falta

Abrir `https://actionfinance.actionhub.com.br/pay-receipts` na sessão já autenticada e acionar Sincronizar. A tentativa nova precisa de id novo. A esperada, se o caminho publicado se comportar como os testes, preenche o caso de R$ 90 com pago 9000, aplicação `lojadepaes`, descrição do produto, pagador por e-mail, método `pix`, processador Mercado Pago e classificação `REAL` por `live_mode=true`. Repetir o clique deve gravar zero campos novos. Esta etapa não foi feita nesta entrega.

## Próxima fatia

Movimentos de conta a partir do extrato, como observação separada dos recebimentos. Não faz parte deste release.
