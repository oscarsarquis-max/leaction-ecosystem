# Prompt 94 — evidência (exceção temporária Loja–Hub)

Spider permanece em sandbox. Esta etapa não publica Spider nem faz dupla escrita.
Pay dos pedidos físicos não foi alterado. Sem dump local sobre produção.

## Arquitetura temporária real

```text
Frontend Loja → backend Loja (`baker_library/hub_plans.py`) → API autenticada ActionHub
ActionHub → Mercado Pago pelo mecanismo existente
Provedor → ActionHub (evento financeiro)
ActionHub outbox → webhook isolado POST /api/v1/webhooks/actionhub/plans
Loja → GET /v1/entitlements e /v1/subscriptions para reconciliação
```

O frontend não chama operações financeiras do Hub. Checkout oficial continua em `/loja`.
Retorno do navegador não concede direito. Hub é o ledger.

## Endpoints reutilizados

| Operação | Método | Auth |
|---|---|---|
| Catálogo | `GET /v1/catalog/lojadepaes` | BFF, Bearer se houver |
| Direitos | `GET /v1/entitlements` | Bearer / `X-App-Secret` |
| Assinaturas | `GET /v1/subscriptions` | Bearer |
| Checkout | `POST /v1/checkout/catalog` | BFF |
| Cancelar renovação | `POST /v1/subscriptions/cancel` | Bearer |
| Créditos | `POST /v1/credits/reserve\|confirm\|release` | Bearer + `Idempotency-Key` |

Não usa `POST /v1/checkout/amount` (Pay).

## Eventos Hub → Loja

`CONTRACT_ACTIVATED`, `CREDITS_GRANTED`, `SUBSCRIPTION_STATUS`, `BIBLIOTECA_*`.
JWT `iss=leaction-hub`, `app_id=lojadepaes`, `outbox_id` / `idempotency_key`.
URL isolada: `APP_PLANS_WEBHOOK_URL_LOJADEPAES`. Sem fallback para o webhook de pedidos.

## Autenticação e correlação (sem segredos)

- Loja → Hub: `Authorization: Bearer`, `X-App-Id`, `Idempotency-Key`, `X-Correlation-ID`.
- Hub → Loja: JWT HS256 no corpo/`Authorization`; comparação segura; app_id conferido.
- Persistência antes de aceitar; deduplicação por `event_id`; evento antigo não desfaz estado mais novo.

## Provas isoladas

- Hub: `credits-ops` + isolamento de URL + catálogo recorrente — 14+5 testes.
- Loja: `test_prompt94` + 91/91b/91g/91h + storefront Pay + data excepcional — 51 testes.
- Frontend: Header, Gigio, Biblioteca — 16 testes.
- Pay: `payment_webhooks.py` e `actionhub_client.request_amount_checkout` intactos.

## Produção (leitura, sem cobrança)

| Item | Evidência |
|---|---|
| Loja | https://lojadepaes.com.br/ — `lojadepaes:prod-20261008g` |
| Backup Loja | `/opt/lojadepaes/backups/lojadepaes-20261009T000337Z.sql.gz` |
| Alembic | `c6d9e4f13a27` (`hub_plans_events`) |
| Regras | `94` |
| Hub gateway | `git_sha` local; health 200; catálogo 200 |
| Backup Hub | `leaction_hub_20261009T000448Z` + rollback files `p94-20261009T000448Z` |
| Ingresso planos | `POST /api/v1/webhooks/actionhub/plans` → 401 `notificação de planos recusada` |
| Ingresso Pay | `POST /api/v1/webhooks/actionhub` → 401 `notificação recusada` (texto distinto) |
| Visitante | Assinatura **Identifique-se**; consultas mensal/avulso vazias; fidelidade separada |
| Catálogo | principal R$ 19/mês 20 créditos; pack R$ 10 avulso; `pack_accumulate=true` |
| Calculadora | `1720 g`; calendário 200 |

## O que não foi feito

Cobrança, assinatura, cancelamento ou e-mail reais. Jornada financeira completa permanece no sandbox.
Healthcheck de produção não prova pagamento.

## Rollback

- Loja: `LOJADEPAES_API_IMAGE=lojadepaes:prod-20261008f` e recreate. Tabela `hub_plans_events` pode permanecer.
- Hub: copiar de volta os arquivos em `/var/lib/leaction-platform/backups/p94-*`.
- Não restaurar dump antigo. Não repetir transações financeiras.

## Pendência

Migração futura para Spider exige tarefa própria, sem corte automático.

## Adendo 94A — verificação e encerramento

Sem novo deploy. Imagem permanece `lojadepaes:prod-20261008g`. Pay e Spider não foram alterados. Confirmação financeira desta prova: `fulfillOrderPayment` no Hub local (contrato do Hub), **não** Mercado Pago sandbox.

### URLs

| Superfície | URL |
|---|---|
| Loja | https://lojadepaes.com.br/ |
| Biblioteca | https://lojadepaes.com.br/biblioteca/o-comeco |
| Calculadora | https://lojadepaes.com.br/biblioteca/calculadora |
| Planos oficiais | https://actionhub.com.br/loja |
| Catálogo | https://api.actionhub.com.br/v1/catalog/lojadepaes |

### Interface publicada (produção, sessão anônima)

Capturas em `captures/`, Chrome headless. A webfont às vezes cola letras na foto; o DOM e as APIs têm espaços.

- Visitante: **Identifique-se**; o painel diz que o código vai ao e-mail cadastrado e não prova assinatura. Desktop `prod-home-visitor-1440.png`, celular `prod-home-visitor-390.png`.
- Artigo aberto, sem formulário de autenticação no texto; resumo R$ 19/mês e pacote R$ 10 avulso; **Ver planos**. `prod-article-1440.png`.
- Calculadora aberta. `prod-calculator-1440.png`.
- `GET /api/v1/conta/situacao` anônimo: `identified=false`, `status_label=Identifique-se`, saldos nulos, fidelidade à parte.
- Bundle servido: `/assets/index-CQYW3i1H.js`.

### Jornada autenticada (sandbox, sem cliente real)

Intercept de `/api/v1/conta/situacao` na UI publicada, contas fictícias:

- Assinatura ativa, mensal 19, avulso 10 sem vencimento, fidelidade 2 créditos de pão. `sandbox-header-assinante-1440.png`.
- Renovação cancelada · acesso vigente; avulso permanece. `sandbox-header-cancelada-1440.png`.

### Cadeia isolada (Hub local :5433)

Script `leaction-platform/services/gateway-api/scripts/p94a-plans-chain.js`. Relatório sanitizado: `p94a-chain-report.json`.

- Pedido PENDING não concede saldo.
- Fulfillment do ciclo → 20 créditos + outbox `CONTRACT_ACTIVATED` (`iss=leaction-hub`, app `lojadepaes`).
- URL de planos isolada; evento de planos não cai no webhook de Pay.
- Consumo 20→19; mesma `operationId` não desconta de novo; falha devolve à origem.
- Conta sem assinatura: pacote 10; duplicata da mesma ordem não soma; segunda compra → 20.
- Cancelar renovação mantém o período pago; ao expirar o ciclo, o avulso permanece.

Loja `test_prompt94a.py`: 4 testes — código só no outbox interno; webhook válido / inválido / duplicata; persistência se o Hub falha na reconciliação; 10% só com assinatura vigente.

### Produção (leitura)

Ingresso planos 401 `notificação de planos recusada`. Ingresso Pay 401 `notificação recusada`. Catálogo publicado: assinatura `plan` R$ 19 / 20 créditos; pacote `credit_pack` R$ 10 avulso, sem desconto de assinante.

A captura de https://actionhub.com.br/loja mostrou a UI “This page couldn’t load”. O 94A tratou isso como lacuna de captura. O Prompt 95 reproduziu a mesma tela na URL do Ver planos, achou `Cannot read properties of null (reading 'colors')` e publicou o Hub FE. Ver `readme/evidence/prompt-95/`.

### O que não foi feito

Pagamento, assinatura, cancelamento ou e-mail reais. Mercado Pago sandbox não foi exercitado. Sem republicação. Sem dump. Sem concessão manual de direito em produção.
