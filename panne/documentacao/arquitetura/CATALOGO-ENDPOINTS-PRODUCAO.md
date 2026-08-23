# Catálogo de endpoints de produção

Prefixo: `/api/v1/organizations/{organization_id}/production`

## Leituras

| Método | Caminho | Permissão |
|---|---|---|
| GET | `/plans`, `/plans/{id}` | `production.plan.read` |
| GET | `/orders`, `/orders/{id}` | `production.order.read` |
| GET | `/batches/{id}` | `production.order.read` |
| GET | `/orders/{id}/materials\|steps\|dependencies\|events\|weighings\|consumptions\|step-runs\|yields\|occurrences\|sheets` | `production.order.read` |
| GET | `/orders/{id}/sheets/{issue_id}` | `production.order.read` |
| GET | `/orders/{id}/traceability` | `production.traceability.read` |
| GET | `/board` | `production.board.read` |
| GET | `/catalog` | `production.order.read` |
| GET | `/orders/{id}/execution` | `production.order.read` |

## Comandos de planejamento

| Método | Caminho | Permissão |
|---|---|---|
| POST | `/plans`, `/plans/{id}/items`, `/plans/{id}/schedule` | `production.plan.manage` |
| PATCH/DELETE | `/plans/{id}/items/{item_id}` | `production.plan.manage` |
| POST | `/orders`, `/orders/{id}/schedule`, `/dependencies`, `/substitute` | `production.order.manage` |
| POST | `/orders/{id}/batches` | `production.batch.manage` |
| POST | `/orders/{id}/release` | `production.order.release` |
| POST | `/orders/{id}/hold\|resume` | `production.order.manage` |
| POST | `/orders/{id}/cancel` | `production.order.cancel` |
| POST | `/orders/{id}/policy` | `production.order.manage` |
| POST | `/orders/{id}/policy/adopt` | `production.order.policy_adopt` |

## Comandos de execução

| Método | Caminho | Permissão |
|---|---|---|
| POST | sessões e entradas de pesagem | `production.weighing.record` |
| POST | `/weighing-entries/{id}/verify` | `production.weighing.verify` |
| POST | `/batches/{id}/consumptions` | `production.consumption.record` |
| POST | transições de etapa e rendimentos | `production.step.execute` |
| POST | ocorrências / resolver | `occurrence.record` / `occurrence.resolve` |
| POST | `/dependencies/{id}/override` | `production.order.short_close` |
| POST | concluir batelada/ordem | `batch.complete` / `order.complete` |
| POST | `/orders/{id}/short-close` | `production.order.short_close` |
| POST | `/orders/{id}/sheets` | `production.sheet.issue` |

## Identidade

| Método | Caminho | Permissão |
|---|---|---|
| POST | `/api/v1/organizations/{id}/memberships/{id}/roles` | `membership.role.manage` |
| POST | `/api/v1/organizations/{id}/memberships/{id}/roles/{role}/revoke` | `membership.role.manage` |
| GET | `/api/v1/me` | `identity.read_me` |
| GET | `/health`, `/ready` | público |
