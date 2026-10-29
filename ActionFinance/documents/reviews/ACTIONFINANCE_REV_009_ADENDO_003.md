# ACTIONFINANCE_REV_009_ADENDO_003

| Campo | Valor |
|---|---|
| Data | 02/10/2026 |
| Prompt | [ACTIONFINANCE_PRM_009_ADENDO_003_VALORES_PIX](../prompts/ACTIONFINANCE_PRM_009_ADENDO_003_VALORES_PIX.md) |
| Autorização | Continuidade do PRM_009; sem PRM_010 |
| Aceite | **Não** |

Sem cobrança, pagamento, reembolso ou payout de teste. Sem preenchimento histórico com R$ 70,00. PRM_007 separado. Os quatro estados do aceite público permanecem **não aceites**.

## Diff por produto

### ActionHub (gateway)

| Área | Antes | Depois |
|---|---|---|
| Fonte do valor cobrado | Admin somava `valor_negociado`; checkout avulso gravava `amount_cents` e o admin ignorava | `amount_cents` no avulso; `valor_negociado` só em sessão/plano, convertido a centavos com precisão de duas casas |
| Valor pago | `paidAmountCents` calculado no webhook e **não gravado**; `authorized` era tratado como pago | `paid_amount_cents` só se MP `approved` e `captured !== false`; `authorized`/`cancelled`/`pending` ficam em `observed_amount_cents` |
| Pix após PAID | `orders.status=PAID` e `pix.status=pending` | Observação do provedor e, na confirmação válida, `status`+JSON no mesmo `UPDATE` (`markPaid`) |
| `live_mode` | Ausente; token de processo não prova o passado | Só `mp_payment.live_mode` com `live_mode_source` |
| Mismatch | Não persistia o valor observado | Persiste `amount_mismatch` + valor observado; **não** marca PAID nem libera fulfill |
| Listagem 1.4 | Podia usar `paid_amount_cents` como cobrado | Cobrado e pago separados; pago nunca substitui cobrado |
| GET `/v1/checkout/amount/:id` | Não devolve pago/Pix actualizado | `paid_amount_cents`, `paid_amount_absent`, `provider_status`, `pix.status` |
| Admin | Rótulo de receita liquidada / soma sem fonte | Colunas Cobrado / Pago; totais “Valor cobrado informado”; ausência = não informado |
| Chamadores de `fulfillOrderPayment` | `server.js` (simular, card, sandbox-card, preapproval); `mp-webhooks` (avulso e demais) | Inalterados para sessão/plano/PanelDX; avulso continua `skipContract` |

Sequência de publicação do gateway (registada): a persistência inicial e o candidato de integridade (40/40) foram publicados **antes** da regressão completa pedida no parecer. Nesta continuidade os gates independentes correram primeiro; só depois o gateway foi republicado (44/44 remotos, restart 70) e o frontend Next do admin foi reconstruído (`BUILD_ID=dCCDeRNnyFwWoe6upS3gI`, `/dashboard/admin/payments` 200, bundle com Cobrado/Pago).

### ActionFinance

V13 aplicada no RDS público (`Successfully applied 1 migration … now at version v13`). Binding `lojadepaes`/`PRODUCTION` aplicado (empresa de teste permanece `af-public-test-padaria`/`HOMOLOG`). Imagem `actionfinance@sha256:77ef03baf8b7875a360b8a45eae9c73b32ce2526a6d32a3f9ef0ce5e5b8d9a35` · tarefa `actionfinance-web:5` estável. SPA `index-Ca0hvJ1C.js` com Valor cobrado / Valor pago e área de revisão. Sem INSERT dos nove; `pay_receipt_transaction` tinha 4 linhas pré-existentes (homolog), não os nove da Loja.

### Spider / Monitor

Imagem `spider-sandbox-backend@sha256:2b84ddcdda0eb0849ce56c8367847f6699e7d7acbb5d9ce6932050d425facf9d` · tarefa `spider-sandbox-backend:8` estável. Binding Loja → `lojadepaes` e `companyId` da Loja no allowlist. `SPIDER_MONITOR_ALLOWED_COMPANIES` inclui Padaria de teste e Loja. Canónica 28/09/2026 15:20:33: não recuperada. Persistência memory inalterada; RDS Spider continua proposta de custo, não autorização.

## 1. Persistência Hub — causa e correção

`paidAmountCents` era derivado de `transaction_amount` no webhook e passado a `notifyAmountCheckout`, mas **não** entrava no JSON de `orders.external_resource_id`. `fulfillOrderPayment` só marca `status`/`paid_at`/`gateway_reference`. `ensurePixCharge` gravava `pix.status` na criação (pending) e nunca o actualizava.

Correcção: `applyProviderObservation` / `persistAmountProviderObservation` (FOR UPDATE, merge JSON, recusa observação mais velha). Confirmação válida do avulso grava pago + `pix.status` + `PAID` no mesmo `UPDATE`. GET de pedido já PAID consulta o provedor e actualiza só a observação, sem novo fulfill. Outbox `ON CONFLICT (idempotency_key) DO NOTHING`.

Mapeamento oficial conferido: MP `approved` (e `captured !== false`) → evento financeiro `paid`; `authorized` + `pending_capture` **não** é pago (reserva); `cancelled`/`pending` guardam `observed_amount_cents` sem `paid_amount_confirmed`. Pedido Hub `PAID` só no fulfill de `approved` com valor coincidente. Não se grava o literal `approved` em `orders.status`. `live_mode` ≠ pagamento.

## 2. Apresentação

Admin API: `charged_amount_cents`, `paid_amount_cents`, `paid_amount_absent`, `provider_status`. Stats não se chamam receita liquidada. GET da Loja (capability 1.4) devolve o estado actual + `reviews`. Consumidores antigos continuam a ler `amountMinor` como cobrado.

## 3. Dry-run histórico (sem APPLY)

Script: `leaction-platform/services/gateway-api/scripts/prm009-adendo003-history-dryrun.py`. Matriz item a item: [`ACTIONFINANCE_REV_009_ADENDO_003_MATRIZ.md`](ACTIONFINANCE_REV_009_ADENDO_003_MATRIZ.md).

Regras: manter `amount_cents` e `orders.status`; não usar R$ 70,00; não fulfill; não outbox. `observed_amount_cents` vem de `transaction_amount`. `paid_amount_cents` proposto **só** se MP `approved` e `captured !== false`. Cancelled/pending não recebem pago confirmado. Divergências de status explícitas. Sem referência = pendente.

GET de pedido PAID agora pode escrever observação: “script não escreveu” não prova ausência de outras escritas. Pré-condição de APPLY: reler `updated_at` e `provider_observed_at`.

A aplicação histórica **não** foi executada.

## 4. Finance / Spider — jornada desta continuidade

| Pré-requisito | Estado |
|---|---|
| V13 + binding `lojadepaes`/`PRODUCTION` no RDS AF | **Comprovado** — Flyway 1–13; mapping `lojadepaes/PRODUCTION`; teste `af-public-test-padaria/HOMOLOG` intacto |
| Imagem AF com área de revisão e campos pagos | **Comprovado** — `actionfinance-web:5`; SPA `index-Ca0hvJ1C.js`; health UP; `/pay-receipts` 200 (shell) |
| Imagem Spider com binding Loja + allowlist Monitor | **Comprovado** — `spider-sandbox-backend:8` estável |
| Sincronização autenticada da Loja | **Bloqueado** — sessão OIDC humana do operador da Loja; não fabricada |
| Comparação visual do Monitor | **Não verificada** — depende da sincronização autenticada |
| Canónica 28/09 | Perda declarada no adendo 002; sem dispensa |

## 5. Testes do candidato

| Suite | Resultado | Quando |
|---|---|---|
| Hub isolado (`spider-pay-lookup`, `amount-observation`, `amount-checkout`, `pay-regression`, `money-cents`) | **44/44** local e remoto (apply) | 02/10/2026, após gates |
| Contract + outbox em Postgres descartável `:55435` | **DISPOSABLE_SMOKE_OK** — contrato idempotente; outbox 2 entregas; retry sem duplicar; isolamento de app | 02/10/2026 |
| `PayReceiptSyncIT` | 6/6, incl. `productionReviewsPersistWithChargedAmountAndAbsentPaidWithoutMovement` | Testcontainers |
| `PayReceiptSyncOidcIT` | 1/1 | Testcontainers + mock OIDC |
| Spider `ActionHubPayListIdentityTest` | 1/1 | 02/10/2026 |
| Spider `ActionHubPayLookupIdentityTest` | 4/4 | 02/10/2026 |
| Spider `ActionFinanceSatelliteInteractionHttpTest` | 6/6 | 02/10/2026 |
| Spider `MonitorCompanyAccessTest` | 6/6 | 02/10/2026 |

Sandbox Mercado Pago com cobrança de teste: **não executado**. Dependência: credenciais de teste do painel MP + autorização explícita de transação sandbox. Os testes independentes do provedor continuaram. Sem transação real.

## 6. Regressão completa do ActionHub Pay

Inventário das rotas/serviços efectivamente existentes no gateway:

| Superfície | Rotas / job |
|---|---|
| Checkout avulso | `POST/GET /v1/checkout/amount`, `GET /v1/checkout/amount/:id`, `POST .../cancel` |
| Sessão/plano | `POST /v1/checkout/sessions`, `POST /v1/checkout/catalog`, `GET /v1/catalog/:app_id` |
| PanelDX / cartão | `POST /v1/payments`, `POST /payments/card`, `POST /payments/sandbox-card`, `POST /simular-pagamento`, `GET /orders/:id/checkout` |
| Assinatura | `POST /subscriptions/preapproval` |
| Webhooks | `POST/GET /webhooks/mercadopago` e alias `/webhook/mercadopago`; `POST /webhook` (legado) |
| Fulfillment / outbox | `payment-fulfillment.js`, `contract-service.js`, `outbox-worker` (intervalo + `kickOutboxNow`) |
| Admin | `GET /admin/payments`, `/stats`, `POST /:id/notice` |
| Integração | `GET /v1/integration/payments`, `POST .../LIST_PAYMENT_TRANSACTIONS/executions` |

### Matriz 6.1

| Fluxo | Cenário | Componente | Ambiente | Dependência | Resultado | Evidência | Efeito externo |
|---|---|---|---|---|---|---|---|
| Checkout avulso Pix aprovação | observação + `markPaid` | amount-checkout / mp-webhooks | isolado | mock pool | PASSOU | `amount-observation` + `pay-regression` | nenhum |
| Checkout avulso pendente | GET sem pago | amount-checkout | isolado | payload | PASSOU | `pay-regression` | nenhum |
| Checkout avulso cancelado | `pix.status=cancelled`, pedido CANCELLED | amount-checkout | isolado | payload | PASSOU | `pay-regression` | nenhum |
| Checkout avulso divergência | mismatch não PAID | mp-webhooks | isolado | mock | PASSOU | `amount-observation` / `pay-regression` | nenhum |
| Checkout avulso cartão | método card, sem pix | amount-checkout | isolado | payload | PASSOU | `pay-regression` | nenhum |
| Checkout avulso criação autorizada | origem cadastrada, sem curinga | amount-checkout | isolado | mock app | PASSOU | `amount-checkout.test` | nenhum |
| Checkout avulso expiração | `mapMpStatusToFinancial('expired')=cancelled` | amount-checkout | isolado | função | PASSOU | mapeamento no `pay-regression` | nenhum |
| Checkout avulso criação real / QR | escrita MP | amount-checkout | sandbox provedor | token teste | **NÃO VERIFICADO** | sem sandbox autorizado neste ciclo | — |
| Sessão/plano valor | `valor_negociado` ≠ avulso | admin + lookup | isolado | payload | PASSOU | `pay-regression` | nenhum |
| Sessão/plano contrato/satélite | activateFromOrder + outbox | contract-service / outbox | DB descartável | destinos controlados | PASSOU | `prm009-adendo003-disposable-pay-smokes.js` | nenhum |
| PanelDX id_matu | parse numérico | payment-fulfillment | isolado | — | PASSOU | `pay-regression` | nenhum |
| PanelDX card/confirm live | rotas `/payments/card` | server.js | produção | — | **NÃO VERIFICADO** | sem tráfego fabricado | — |
| Preapproval criação | `POST /subscriptions/preapproval` | server.js / mercadopago | isolado | — | **EXISTENTE, NÃO VERIFICADO** (rota e `isPreapprovalSuccess` cobertos; transições authorized→pago/cancel **não** ensaiadas) | `pay-regression` | nenhum |
| Webhook IPN/body | extract id/tópico | mp-webhooks | isolado | — | PASSOU | `pay-regression` | nenhum |
| Webhook HMAC oficial | `x-signature` HMAC-SHA256 `id:;request-id:;ts:;` | mp-webhooks | isolado | `MP_WEBHOOK_SECRET` | PASSOU isolado; produção **secret_absent** (IPN actual não interrompido) | docs MP + `pay-regression` | nenhum até o secret ser configurado |
| Webhook id desconhecido | order_not_found | mp-webhooks | isolado | mock | coberto no fluxo approved sem order | `fulfillFromApprovedPayment` | nenhum |
| Webhook duplicado / ordem invertida | alreadyPaid + stale | amount-observation | isolado | mock | PASSOU | testes 4 e 9 | nenhum |
| Webhook timeout/retry | 5xx ao MP | mp-webhooks | produção | — | **NÃO VERIFICADO** | código devolve 5xx para retry; sem fault injection | — |
| Outbox entrega única | `ON CONFLICT DO NOTHING` | amount-checkout / contract-service | isolado (SQL) | — | PASSOU no contrato do INSERT | não exercitado contra worker real neste ciclo | nenhum |
| Outbox retry / cruzamento de app | worker | outbox-worker | DB descartável | destinos /app-a /app-b | PASSOU (retry sem duplicar; isolamento) | disposable smoke | nenhum |
| Admin cobrado/pago | serialize + stats + UI | admin + Next | produção | — | PASSOU isolado; UI publicada e bundle contém Cobrado/Pago | `pay-regression` + `BUILD_ID=dCCDeRNnyFwWoe6upS3gI` | nenhum |
| Integração Spider/Finance | 1.4 reviews + isolamento | lookup + AF | Hub vivo / AF publicado | OIDC humano | Hub lê 9 reviews. Importação autenticada da Loja **BLOQUEADA** à sessão do operador | apply + binding | nenhum INSERT dos nove |
| Precisão monetária | 70.00 / 70.001 | money-cents | isolado | — | PASSOU | 3 testes | nenhum |

### Anterior / posterior à publicação

| Item | Antes da 1.ª vaga | Depois da persistência | Depois do candidato cobrado≠pago |
|---|---|---|---|
| `paid_amount_cents` nos 9 | ausente / 0 | ainda ausente nos históricos (sem APPLY) | novos eventos passam a gravar; históricos só no dry-run |
| `pix.status` vs `PAID` | pending + PAID | GET/webhook novos actualizam; históricos intactos | `markPaid` atómico nos novos |
| Listagem cobrado | podia cair no pago | igual | pago separado; cobrado nunca substituído |
| Health / lookup 401 | 200 / 401 | 200 / 401 | a confirmar no apply deste candidato |

### Distinção de prova

| Tipo | O que prova | O que não prova |
|---|---|---|
| Teste isolado (40/40) | Contratos e invariantes do código candidato | Produção, sandbox MP, entrega real ao satélite |
| Sandbox do provedor | — | **Não disponível / não autorizado** neste ciclo |
| Observação em produção | Health, 401 sem key, 9 reviews INDETERMINATE, `public.orders` intocado pelo script | Novo Pix, cartão, preapproval, e-mail, outbox a consumidor real |

Ausência de tráfego operacional **não** é sucesso. Plano: após imagens AF/Spider, uma sincronização autenticada da Loja (leitura) e observação de webhooks/outbox já existentes, sem fabricar cobrança.

## 7. Distinção pedida pelo parecer

| Classe | Itens |
|---|---|
| **Comprovado** | 44/44 Hub; smokes contract/outbox; PayReceiptSyncIT+OidcIT; testes Spider afectados; `authorized`≠pago; HMAC isolado; matriz item a item; gateway+admin UI após gates; V13; binding Loja PRODUCTION; imagens AF/Spider estáveis |
| **Não verificado** | Transições de preapproval; sandbox MP com cobrança de teste; HMAC em produção (secret ausente); sync autenticado / Monitor da importação dos nove; captura atrasada de cartão em tráfego real |
| **Bloqueado** | APPLY histórico (sem autorização do proprietário); aceite do produto; sincronização autenticada (OIDC humano); secret `MP_WEBHOOK_SECRET` do painel MP; custo RDS Spider |

Webhook: documentação oficial actual usa `x-signature` HMAC-SHA256 no Webhooks (não no IPN clássico GET nem em QR Code). Consulta autenticada ao recurso **não** prova autenticidade da notificação. Código recusa POST sem/ inválido `x-signature` **quando** o secret existe; sem secret, IPN actual continua. Replay HMAC inválido e referência de pagamento não autorizada não confirmam o pedido.

## 8. Baseline e reversão

| Item | Valor |
|---|---|
| Host Hub | EC2 `3.17.19.188` · `gateway-api` restart 70 · health 200 · 401 sem key |
| Admin FE | `action-hub` restart 9 · health 200 · `BUILD_ID=dCCDeRNnyFwWoe6upS3gI` |
| AF | `actionfinance-web:5` · digest `77ef03ba…` · Flyway 1–13 |
| Spider | `spider-sandbox-backend:8` · digest `2b84ddcd…` |
| Reversão Hub | repor os `.js` anteriores e `pm2 restart gateway-api` |
| Reversão AF | tarefa `actionfinance-web:4`; V13 **permanece** |
| Reversão Spider | tarefa `spider-sandbox-backend:7` |

## Pendências (só o que ainda depende de fora)

1. Sessão OIDC do operador da Loja para sincronizar os nove como revisão (cobrado presente, pago ausente até APPLY/confirmação) e mostrar a execução no Monitor.
2. Autorização do proprietário para o APPLY histórico, com reler/precondicionar revisão.
3. Aceite do produto — **não** concedido.
4. Configurar `MP_WEBHOOK_SECRET` no Hub se o painel MP tiver a chave de Webhooks (sem isso o HMAC preparado não entra em vigor).
5. Canónica 28/09 e custo RDS Spider: sem dispensa e sem autorização de custo. Sem PRM_010.
