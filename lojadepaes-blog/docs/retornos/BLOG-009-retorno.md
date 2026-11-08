# BLOG-009 — retorno

Data: 08/11/2026. As partes foram feitas na ordem. A parte C parou no conflito.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | `git log` dos mains e a tag `lepain-v1.0` | **Feito.** |
| 2 | Caddy com `import`, pasta montada, queda medida, prova do `zz-teste`, 3 sites em 200, só o Caddy com `StartedAt` novo, SSH fechado | **Feito.** |
| 3 | Lista a/b/c, testes de (a), merge e modo seco | **Não feito até o fim.** Há um conflito. Os testes, o merge e o modo seco não rodaram. |
| 4 | Este retorno, commit e push | **Feito** neste commit. |

## A. Git

`main` local e `origin/main` avançaram em fast-forward até `02db6d04` e, em seguida, receberam os merges.

```
bcedc024 fix(caddy): Gestao e LePain gravam o proprio arquivo de site [BLOG-009]
d467aebf merge(gestao): traz o Caddy da Gestao para o main [BLOG-009]
626b653f merge(blog): publica o LePain v1 no main [BLOG-009]
```

`release/lepain-v1`, a partir de `db25a0df`, com o merge de `feat/blog-005-caddy` (`9a3d8054`):

```
f5eb259c merge(blog): traz o Caddy do LePain para a release v1 [BLOG-009]
db25a0df feat(blog): botao Seguir e link do post no Instagram [BLOG-008]
f3c8baec feat(blog): capa, autor e número do ensaio [BLOG-006]
```

A tag anotada `lepain-v1.0` aponta para `626b653f`, o merge do blog no `main`, antes do merge da Gestão.

O merge de `feat/blog-005-caddy-gestao` (`9308a893`) entrou no `main` sem squash: `d467aebf`. Nenhum merge teve conflito. Branches e worktrees existentes foram mantidos.

O `infra/` da Loja não está neste `main`. O commit dele ficou em `feat/actionfinance-extrato-032`: `249541b4 lojadepaes: o Caddy importa os sites por pasta [BLOG-009]`.

## B. Caddy

`lojadepaes/infra/Caddyfile` foi para `lojadepaes/infra/caddy/Caddyfile`, com `import /etc/caddy/sites/*.caddy` no final. O compose monta `./caddy:/etc/caddy:ro`. `infra/caddy/sites/.gitkeep` está no git. Os blocos da Gestão e do LePain não foram commitados.

No host, a parte da Loja do Caddyfile era igual à do repositório, e o compose também. Backup: `/opt/lojadepaes/app/backups/caddy-blog009-20261108T203411Z`. Os blocos foram extraídos para `sites/gestao.caddy` e `sites/lepain.caddy`, sem marcadores. O `docker compose up -d --no-deps --force-recreate caddy` recriou só o `infra-caddy-1`.

A queda medida foi de 3 segundos: uma tentativa não conectou na porta 443 e, em seguida, os três endereços responderam 200. A raiz do LePain continua respondendo 302 e a página seguida responde 200; a medição seguiu o redirecionamento.

A prova gravou `sites/zz-teste.caddy` vazio, recarregou (o Caddy avisou que o arquivo importado estava vazio) e os três sites seguiram em 200. O arquivo foi apagado, o Caddy recarregou de novo e os três seguiram em 200.

O contêiner vê `/etc/caddy` como `ro`. O `import` está na linha 36.

| Contêiner | `StartedAt` |
|---|---|
| `infra-caddy-1` | `2026-11-08T20:34:12.590952489Z` (só este mudou; antes `2026-11-08T17:46:46.938554147Z`) |
| `infra-api-1` | `2026-11-04T16:05:11.35453791Z` |
| `infra-db-1` | `2026-09-20T18:14:08.677061212Z` |
| `gestao-api` | `2026-11-07T15:12:10.777531884Z` |
| `lepain` | `2026-11-08T19:37:34.548763844Z` |

Os `caddy-add.sh` e `caddy-remove.sh` da Gestão e do LePain passam a gravar ou apagar `sites/<app>.caddy`, validar e recarregar. Não há mais marcador nem checagem de inode. As cópias no host foram atualizadas. A porta 22 da Loja foi fechada. Ficaram abertas a 80 e a 443.

## C. Hub

A base de três vias é o `git_sha` da produção, `49b2a83`. A cópia de `/var/www/leaction-platform` deixou de fora `node_modules`, builds (incluindo `.next` e `.next.bak-blog008`), `.venv`, `.env`, `.env.production`, uploads e logs. A branch `sync/producao-20261108` foi criada a partir do `main` (`bcedc024`) e não recebeu a cópia, porque a classificação achou conflito.

Build ignorado na conta: 1525 arquivos de `.next.bak-blog008` e o `GIT_SHA` da produção.

### (a) só na produção, ou a produção mudou e o `main` não — não entrou

68 arquivos de código. Entre eles: checkout por valor (`amount-checkout`, `money-cents`, `PaymentsOps`), créditos (`credits-api`, `credits-ops`), assinatura (`catalog-subscription`, `MercadoPagoSubscriptionBrick`, `patch_subscription_cycles.sql`) e Spider Pay (`spider-pay-lookup`). A lista completa:

- `backend/app/__init__.py`
- `backend/app/api/curation_routes.py`
- `backend/app/api/marketplace_routes.py`
- `backend/app/database/models.py`
- `backend/app/database/seed.py`
- `backend/app/services/amazon_service.py`
- `backend/app/services/contextual_vitrine.py`
- `backend/app/services/curation_repository.py`
- `backend/app/services/marketplace_resilience.py`
- `backend/app/services/mercadolivre_fallback.py`
- `backend/app/services/mercadolivre_service.py`
- `backend/app/services/multivendor_orchestrator.py`
- `backend/app/services/offer_decisions.py`
- `backend/app/services/offer_relevance.py`
- `backend/app/services/origin_profiles.py`
- `frontend/action-hub/next-env.d.ts`
- `frontend/action-hub/next.config.ts`
- `frontend/action-hub/public/brands/lojadepaes.png`
- `frontend/action-hub/src/app/dashboard/crm/contas/page.tsx`
- `frontend/action-hub/src/app/dashboard/crm/tracking/page.tsx`
- `frontend/action-hub/src/app/dashboard/page.tsx`
- `frontend/action-hub/src/app/loja/contratar/page.tsx`
- `frontend/action-hub/src/app/loja/page.tsx`
- `frontend/action-hub/src/app/marketplace-api/offers/route.ts`
- `frontend/action-hub/src/app/marketplace-api/vitrine/route.ts`
- `frontend/action-hub/src/components/CatalogPricingCards.tsx`
- `frontend/action-hub/src/components/CheckoutChrome.tsx`
- `frontend/action-hub/src/components/ClientCheckoutHeader.tsx`
- `frontend/action-hub/src/components/MercadoPagoSubscriptionBrick.tsx`
- `frontend/action-hub/src/components/SiteHeader.tsx`
- `frontend/action-hub/src/components/admin/CmsSiteForm.tsx`
- `frontend/action-hub/src/components/admin/PaymentsOps.tsx`
- `frontend/action-hub/src/lib/catalog-api.ts`
- `frontend/action-hub/src/lib/client-branding.ts`
- `frontend/action-hub/src/lib/loja-brand-asset.test.mjs`
- `frontend/action-hub/src/lib/loja-checkout-copy.test.mjs`
- `frontend/action-hub/src/lib/loja-checkout-copy.ts`
- `frontend/action-hub/src/lib/loja-return.test.mjs`
- `frontend/action-hub/src/lib/loja-return.ts`
- `frontend/action-hub/src/middleware.ts`
- `services/gateway-api/admin/payments.js`
- `services/gateway-api/crm-contas.js`
- `services/gateway-api/domain/amount-checkout.js`
- `services/gateway-api/domain/amount-checkout.test.js`
- `services/gateway-api/domain/amount-observation.test.js`
- `services/gateway-api/domain/catalog-public.js`
- `services/gateway-api/domain/catalog-subscription.js`
- `services/gateway-api/domain/catalog-subscription.test.js`
- `services/gateway-api/domain/checkout-sessions.js`
- `services/gateway-api/domain/contract-service.js`
- `services/gateway-api/domain/credits-api.js`
- `services/gateway-api/domain/credits-ops.js`
- `services/gateway-api/domain/credits-ops.test.js`
- `services/gateway-api/domain/entitlements-api.js`
- `services/gateway-api/domain/loja-plans-notify.js`
- `services/gateway-api/domain/mp-webhooks.js`
- `services/gateway-api/domain/outbox-worker.js`
- `services/gateway-api/domain/outbox-worker.plans.test.js`
- `services/gateway-api/domain/pay-regression.test.js`
- `services/gateway-api/domain/spider-pay-lookup.js`
- `services/gateway-api/domain/spider-pay-lookup.test.js`
- `services/gateway-api/lib/money-cents.js`
- `services/gateway-api/lib/money-cents.test.js`
- `services/gateway-api/mercadopago.js`
- `services/gateway-api/p91g-inspect-clients.js`
- `services/gateway-api/payment-fulfillment.js`
- `services/gateway-api/server.js`
- `shared/database/patch_subscription_cycles.sql`

### (b) o `main` tem e a produção não — ficou o do `main`

28 arquivos:

- `CHANGELOG.md`
- `DEPLOY_LOG.md`
- `VERSION`
- `docs/CMS-PANNE-ADMIN-PUBLICATION-028.md`
- `docs/CMS-SITE-S3-PERSISTENCE.md`
- `docs/MP-PRODUCAO-CHAVES.md`
- `docs/retornos/BLOG-003-retorno.md`
- `docs/retornos/BLOG-007-retorno.md`
- `docs/retornos/BLOG-008-retorno.md`
- `docs/retornos/evidence/blog-003/lista.png`
- `docs/retornos/evidence/blog-003/novo-en-ligada.png`
- `docs/retornos/evidence/blog-003/novo-insights-pt.png`
- `docs/retornos/evidence/blog-003/novo-right-now-mobile.png`
- `docs/retornos/evidence/blog-003/novo-right-now.png`
- `docs/retornos/evidence/blog-007/aviso-slug.png`
- `docs/retornos/evidence/blog-007/editar-instagram.png`
- `docs/retornos/evidence/blog-007/excluir-duas-versoes.png`
- `docs/retornos/evidence/blog-007/lista-menu.png`
- `docs/retornos/evidence/blog-008/painel-instagram.png`
- `examples/cms-consumer-noticias.js`
- `examples/cms-consumer-noticias.py`
- `imagens/ActionHub Logo.png`
- `imagens/ActionHubCor Logo.png`
- `imagens/ActionHubCorMarrom Logo.png`
- `leaction-platform_docs/RESUMO-TECNICO.md`
- `services/gateway-api/domain/cms-lepain-instagram-patch.test.js`
- `services/gateway-api/domain/cms-lepain-patch.test.js`
- `services/gateway-api/domain/cms-posts.test.js`

### (c) conflito — parei aqui

`frontend/action-hub/src/lib/admin-api.ts`

Os dois lados mudaram o mesmo tipo em relação a `49b2a839`. O `main` tem `revenue: number`. A produção tem `revenue?: number` e também `charged_amount_cents`, `paid_amount_cents`, `paid_amount_absent`, `currency`, `method`, `provider_status` e `charged_missing`.

Não copiei a produção por cima do `main`, não rodei os testes de (a), não fiz o merge e não montei o zip do `deploy-remote.ps1`. Esse script não tem modo seco: o caminho normal apaga `/var/www/leaction-platform` antes de enviar.

A porta 22 do Hub já estava aberta para a internet, além do endereço desta sessão. Removi só a regra desta sessão. A regra que já existia para a internet ficou como estava.
