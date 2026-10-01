# ACTIONFINANCE_PRM_009_PACOTE_PUBLICACAO — Pacote concreto aplicado

| Campo | Valor |
|---|---|
| Data | 01/10/2026 |
| Versão | 0.4 |
| Origem | [ADENDO_001](../prompts/ACTIONFINANCE_PRM_009_ADENDO_001_ACEITE_PUBLICO.md) · [recomendação](../reviews/ACTIONFINANCE_REV_009_RECOMENDACAO_EXECUCAO_ANALISTA.md) |
| Autorização do proprietário | [ACTIONFINANCE_PRM_009_AUTORIZACAO_PROPRIETARIO](../prompts/ACTIONFINANCE_PRM_009_AUTORIZACAO_PROPRIETARIO.md) — “tem minha autorizacao.” (01/10/2026). **Não** é aceite do resultado. |
| Estado | **Implantação executada.** Jornada autenticada e aceite pendentes. |
| Relato da execução | [REV_009_EXECUCAO_PUBLICA](../reviews/ACTIONFINANCE_REV_009_EXECUCAO_PUBLICA.md) |
| Git / apply | Branch `feat/prm-009-public-receipt-sync` · HEAD `03d051c5` |

Prova local já aceite (CONTINUIDADE_001 + COR_001) permanece. PRM_008 não reaberto. PRM_007 (invalidação de sessão no restore) permanece pendente à parte. PRM_010 não emitido.

## 0. Estados

| Estado | Agora |
|---|---|
| Correções COR_001 concluídas | **Sim** — [REV_009_COR_001](../reviews/ACTIONFINANCE_REV_009_COR_001.md) |
| Ativação Finance sem `homolog=true` | **Sim** — `receipt-sync-enabled` + OIDC IT |
| Autorização Monitor por empresa | **Sim** — deny-by-default; lista/detalhe/eventos/monitor-events |
| Pacote delimitado para recomendação | **Sim** — este ficheiro |
| Recomendação do analista | **Sim** — [REV_009_RECOMENDACAO_EXECUCAO_ANALISTA](../reviews/ACTIONFINANCE_REV_009_RECOMENDACAO_EXECUCAO_ANALISTA.md) |
| Implantação autorizada | **Sim** — [autorização do proprietário](../prompts/ACTIONFINANCE_PRM_009_AUTORIZACAO_PROPRIETARIO.md) |
| Implantação executada | **Sim** — [REV_009_EXECUCAO_PUBLICA](../reviews/ACTIONFINANCE_REV_009_EXECUCAO_PUBLICA.md) |
| Commit / push | `c407591d` · `e2a45cc2` · `03d051c5` em `origin/feat/prm-009-public-receipt-sync` |
| Jornada pública validada tecnicamente | **Parcial** — hosts, isolamento Hub e rotas autenticadas ok; sync novo no Finance **não** corrido (login Cognito do operador) |
| Aceite do proprietário | **Não** (não confundir com autorização de implantação) |
| PRM_007 invalidação de sessão no restore | **Pendente** (separado; sem RDS novo) |
| Publicação global declarada | **Não** |
| PRM_010 | **Não emitido** |

## 1. Git — uma raiz, um remoto, working tree misto

| Campo | Valor |
|---|---|
| Raiz | `C:\Projetos` |
| Remoto | `origin` → `https://github.com/oscarsarquis-max/leaction-ecosystem.git` |
| Branch desta execução | `feat/prm-009-public-receipt-sync` (criada a partir de `d51d85f3`) |
| HEAD | `03d051c5a3ad38b8cb202ae06dcad908cb52f0f7` — shell público `/pay-receipts` |
| Repositórios | **Um.** Não há três remotos só porque existem `ActionFinance/`, `spider/` e `leaction-platform/`. |

A branch actual mistura Loja de Pães, Panne e outros. Criar `feat/prm-009-public-receipt-sync` a partir do HEAD acima e adicionar **somente** a lista da §8. Conferir o diff integral contra a base antes do commit.

Identidade local do candidato: hashes da §7. Digest remoto só depois de push autorizado. A ausência de digest ECR **não** impede este artefacto local.

## 2. Identidades fixas (sem decisão no apply)

| Peça | Valor |
|---|---|
| Tenant AF | `9c2e0a10-4f11-4b8a-9c2e-0a104f110009` · código `af-public-test` |
| Empresa AF | `9c2e0a10-4f11-4b8a-9c2e-0a104f11000c` · código `af-public-test-padaria` · `is_demo=true` · fuso `America/Sao_Paulo` |
| App Pay | `af-public-test-padaria` |
| Ambiente de listagem | `HOMOLOG` |
| Binding Monitor | principal `owner:sandbox` → empresa `9c2e0a10-4f11-4b8a-9c2e-0a104f11000c` (`SPIDER_MONITOR_ALLOWED_COMPANIES`) |
| Operador AF | O mesmo subject Cognito já autorizado no AF público; **nova** `company_membership` OPERATOR só nesta empresa. Viewer sem `titles:write`. Sem ADMIN global. |
| Empresa proibida | Loja de Pães `624023a4-57e3-415c-b7d0-925ca1acd3b7` — não ler, não mapear, não seedar |

SQL de bootstrap (executado no RDS AF): [`scripts/dev/prm009/bootstrap-public-test-identities.sql`](../../scripts/dev/prm009/bootstrap-public-test-identities.sql) — tenant=1 · company=1 · mapping=1 · membership=1.

**Convites / mensagens:** não autorizados por este pacote. Se o operador do Monitor ainda não estiver no grupo Cognito `spider-sandbox-operators`, isso é pedido **separado**, sem envio automático.

## 3. Levantamento público (só leitura; inalterado)

Fonte: [survey-publico-2026-10-01](../reviews/evidence/prm-009-adendo-001/survey-publico-2026-10-01.md).

| Produto | Digest / versão pública | Lacuna que este candidato fecha |
|---|---|---|
| Finance | `sha256:7c4cc0de…da5b65` · Flyway **v7** | V8–V12, `/pay-receipts`, `receipt-sync-enabled` |
| Spider | `sandbox-20260928-monitorfix` · `sha256:72ed3a8c…f9b9f4a1` · memory · desired 1 | Contrato 1.4 + recorte por empresa |
| Monitor | CloudFront `E2E4ORTD4DHI1D` · SPA 28/09 | Badge observado + deep link recortado |
| Pay | FE `git_sha=49b2a83` · `GET /v1/integration/payments` → **404** | Lookup só no schema isolado |

## 4. Item 1 — Ativação Finance sem homolog em produção

`ACTIONFINANCE_INTEGRATION_HOMOLOG=false` permanece no perfil `production`. `PayReceiptSyncService.requireReceiptSync()` usa `isReceiptSyncAllowed()` = `homolog || receiptSyncEnabled`.

| Perfil | `homolog` | `receipt-sync-enabled` | Efeito |
|---|---|---|---|
| `production` | sempre `false` (validador recusa `true`) | `ACTIONFINANCE_RECEIPT_SYNC_ENABLED` (default `false`) | Sync só com flag + HTTPS Spider/Monitor + secret |
| `local-demo` | pode ser `true` no recorte local | default `false` | Isolado do público |
| `oidc-it` | `false` | `true` | Prova OIDC/CSRF sem homolog |

`ProductionSafetyValidator`: recusa `local-demo`/`oidc-it` combinados com production, recusa demo-auth, recusa homolog; se `receiptSyncEnabled`, exige `ACTIONFINANCE_SPIDER_BASE_URL` HTTPS, `ACTIONFINANCE_SPIDER_SECRET` e `ACTIONFINANCE_SPIDER_MONITOR_BASE_URL` HTTPS.

UI: `loadPayReceiptsVisible()` = `homologIntegration \|\| receiptSyncEnabled`. Nav `/pay-receipts` segue essa visibilidade. Identidade demo continua 401 em production/OIDC.

**Prova isolada equivalente ao candidato** (`PayReceiptSyncOidcIT`, porta 18792, homolog=false, receipt-sync=true):

| Caso | Resultado |
|---|---|
| Operador OIDC + CSRF POST sync | 200 |
| Token demo | 401 |
| Outra empresa | 403 |
| Sem CSRF | 403 |
| Viewer POST | 403 |

`ProductionSafetyValidatorTest`: aceita receipt-sync sem homolog; recusa URL HTTP da Spider; recusa homolog+receipt-sync. **Não** se liga `homolog=true` em produção para contornar.

## 5. Item 2 — Autorização do Monitor (pré-requisito concluído)

`MonitorCompanyAccess`: deny-by-default quando `company-scope.enabled=true`. Empresa lida de `metadata.companyId` ou `SATELLITE_COMPANY_AUTHORIZED.reasonCode`. Empresa ausente ou em branco → **nega**. Principal sem binding → conjunto vazio → nega.

Canais usados pelo Monitor:

| Canal | Recorte |
|---|---|
| `GET /v1/console/executions` | filtra itens pela empresa ligada |
| `GET /v1/console/executions/{id}` | 404 se empresa estrangeira ou ausente |
| `GET /v1/console/executions/{id}/events` | idem |
| `GET /v1/console/monitor/events` | filtra stream por execução visível |

`implementation`, `presentation/readiness` e `monitor/simulation` não devolvem corpo de execução de outra empresa.

Sandbox: `application-sandbox.yml` liga o âmbito; binding `[owner:sandbox]=${SPIDER_MONITOR_ALLOWED_COMPANIES:}`. local-demo: âmbito **desligado** (default `enabled=false`).

**Provas:** `MonitorCompanyAccessTest` (deny default, empresa ausente, deep link da empresa ligada, troca para `624023a4-…` recusada) e `MonitorEventsTest.companyScopeAllowsBoundExecutionAndHidesForeignId`. `mvn -q "-Dtest=MonitorCompanyAccessTest,MonitorEventsTest"` exit 0.

Deep link autorizado: `https://monitor.spider.actionhub.com.br/?q={correlation}&execution={messageId}` — sem token na URL. Troca de ID de outra empresa → 404.

## 6. Item 4 — Rede, custo e isolamento Hub

### 6.1 504 da API Spider — diagnóstico (só leitura)

| Facto | Valor |
|---|---|
| Recurso | ALB `spider-sandbox-alb` · SG `sg-0ad34b305223b59f8` |
| Target | saudável em `/actuator/health/liveness` — a engine **não** está caída |
| 443 ingress actual | `191.57.226.77/32` (operador) + prefix list CloudFront `pl-b6a144df` |
| Origem AF | NAT instance já paga `i-0bdd19288b5118611` · IP público `3.143.92.115` — **não** está no SG |
| Causa | drop no SG do ALB (timeout/504 visto pelo cliente), não WAF genérico nem target unhealthy |
| Alteração exacta (só após auth) | inbound TCP 443 · CIDR `3.143.92.115/32` · descrição `af-nat-prm009` · no SG `sg-0ad34b305223b59f8` |
| Impacto | só o NAT do AF alcança a API; o resto permanece bloqueado |
| Reversão | apagar essa regra |
| Custo da regra | US$ 0 |
| O que **não** fazer | NAT Gateway novo, WAF “se necessário”, SG largo, peering, ALB novo |

### 6.2 Consumidores de `public.orders` — isolamento não comprovado por marca

A marca `sandbox`/`test_order` no JSON **não** isola. Consumidores do Hub operacional leem `public.orders` sem esse filtro:

| Consumidor | Efeito se a linha estiver em `public.orders` |
|---|---|
| `admin/payments.js` `EXCLUDE_TEST_ORDERS_SQL` | Exclui `users.is_test` e e-mails fixos — **não** `sandbox`/`test_order` |
| `payment-fulfillment.fulfillOrderPayment` | Pode disparar webhook JWT |
| `domain/mp-webhooks.js` | Fulfillment a partir de notificação MP |
| `domain/amount-checkout.js` | Insert + `webhook_outbox` |
| `domain/contract-service.js` | Outbox de contrato |
| `domain/outbox-worker.js` | Entrega a `app_registry.webhook_url` |
| `domain/catalog-public.js` / `checkout-sessions.js` | Novos pedidos operacionais |

**Decisão:** este apply **não** insere em `public.orders` e **não** liga `ACTIONHUB_PAY_LOOKUP_PUBLIC_TEST`.

### 6.3 Alternativa segregada (preparada; recurso **não** criado)

| Campo | Valor |
|---|---|
| Destino | Schema `prm009_public_test.orders` no **mesmo** Postgres do Hub |
| Código | `ordersRelation()` em `spider-pay-lookup.js` — com `LOOKUP_ISOLATED=true` a SQL usa só essa relação |
| Colunas | `id, status, gateway_ref, gateway_reference, external_resource_id, created_at, updated_at` — sem `user_id`, `webhook_url`, fulfillment |
| Seed | 4 linhas sintéticas do app `af-public-test-padaria` — [`prm009-isolated-schema.sql`](../../../leaction-platform/services/gateway-api/scripts/prm009-isolated-schema.sql) |
| Flags apply | `ACTIONHUB_PAY_LOOKUP_ENABLED=true` · `ACTIONHUB_PAY_LOOKUP_ISOLATED=true` · `ACTIONHUB_PAY_LOOKUP_PUBLIC_TEST=false` |
| `ACTIONHUB_PAY_ENVIRONMENT=sandbox` | **Não** ligar no EC2 operacional (evita mudar Mercado Pago / checkout real) |
| Custo desta opção | US$ 0 (KB no PG existente) |
| Se o proprietário recusar schema no PG operacional | sidecar `db.t4g.micro` estimado **~US$ 12–15/mês** — **não** criar agora; seria pedido separado |

Prova de isolamento: fulfillment, webhook, outbox e admin listam `public.orders`; o lookup isolado não lê essa tabela. Unit tests 11/11 incluem `ordersRelation({ISOLATED}) === 'prm009_public_test.orders'` e `PUBLIC_TEST` sozinho **não** muda a relação.

## 7. Artefactos locais (builds deste working tree)

Digests publicados: AF `sha256:ec0c62c59c7936365f8aab2aa284bf52f310bd3c62c9fb9dd688b34d6532dfbc` · Spider `sha256:8709085a9f96daedbab22ce3b200b4c5d20a02c5998eb93077935239ab99569a`. Relato: [REV_009_EXECUCAO_PUBLICA](../reviews/ACTIONFINANCE_REV_009_EXECUCAO_PUBLICA.md).

| Artefacto | SHA-256 | Notas |
|---|---|---|
| `ActionFinance/backend/target/actionfinance-backend-0.1.0.jar` | `4DE80D67F35E3C290E5C6204670763B77E8F5ACBCEFBF3F06CDD3F965F2FF010` | 66 083 087 bytes · `mvn -DskipTests package` após ITs |
| `spider/backend/target/spider-0.1.0-SNAPSHOT.jar` | `4C9357D1A1A394E5BD5B068A2EED0656F314CE5D8E4948FB992B60F2E05A339F` | `mvn -DskipTests package` |
| AF `dist/assets/index-C0gESpWW.js` | `F0075BE48A577C54870FA78D0D5D4F341734C14BEECC03DBDB5F68059D0DF74C` | `vitest` 39/39 · `vite build` |
| AF `dist/assets/index-I6b5UG5n.css` | `2055CA2099814B380295F318E3143B5E056C9B6EC07F4782F46866C49204A65F` | |
| AF `dist/index.html` | `8A2E78FD0706407B9A3E90285A877FC96B08FADAB96D8552364F648F6FBE28A3` | |
| Monitor `dist/assets/index-Ufag3vrV.js` | `C58BE99ADACAC58FD00F79E1C5555CFC6F825903E11F82983ED79E546FE674B0` | `vitest` 192/192 · `vite build` |
| Monitor `dist/assets/index-CkU0BY1u.css` | `72E2D97769B8529E499CF5C501D01EDFAE85B59C2B2F34A34F17E2AB435E1BED` | |
| Monitor `dist/index.html` | `B749384DF62B180F1F910B12CF8CFD3385C5BE40D9BDED35A4816AAA9E521222` | |
| HEAD git (base, sem este conjunto committed) | `d51d85f364dfa285a555edcb9a44cc19ab9775eb` | |

Imagens Docker **não** foram construídas (evita publicar a partir de tree não identificado). O apply, se autorizado, constrói a partir do commit da §8 e regista o digest ECR **depois** do push.

Cópia: [local-artifacts-2026-10-01](../reviews/evidence/prm-009-adendo-001/local-artifacts-2026-10-01.md).

### Testes do candidato (01/10/2026)

| Suite | Resultado |
|---|---|
| `PayReceiptSyncOidcIT` | 1/1 BUILD SUCCESS |
| `ProductionSafetyValidatorTest` | passou |
| Spider `MonitorCompanyAccessTest` + `MonitorEventsTest` | exit 0 |
| Hub `spider-pay-lookup.test.js` | 11/11 |
| AF frontend vitest | 39/39 |
| Spider frontend vitest | 192/192 |
| Prova local aceite (CONTINUIDADE_001 / COR_001) | preservada — não reexecutar como aceite público |

## 8. Inventário exacto a incluir (e o que fica de fora)

### 8.1 Incluir — ActionFinance

Implementação: `backend/src/main/java/br/com/actionfinance/application/integration/**`, `infrastructure/integration/HttpSpiderInteractionClient.java`, `infrastructure/persistence/JdbcExternalOperationRepository.java`, `infrastructure/persistence/JdbcPayReceiptRepository.java`, `interfaces/http/ExternalLookupController.java`, `interfaces/http/PayReceiptController.java`, alterações em `ActionFinanceProperties`, `ProductionSafetyValidator`, `SecurityConfiguration`, `SystemInfo`, `SystemInfoService`, `FinanceExceptions`, `FinanceHttpModels`, `ApiExceptionHandler`, `LocalDemoSeed` (mapping local `homolog-padaria` **não** vai ao RDS público).

Config: `application.properties`, `application-production.properties`, `application-local-demo.properties` (`receipt-sync-enabled`, homolog=false em production).

Migrations: `database/migrations/V8__external_pay_lookup.sql` … `V12__pay_receipt_sync.sql`.

Testes: `PayReceiptSyncIT`, `PayReceiptSyncOidcIT`, `ExternalLookupReliabilityIT`, `ProductionSafetyValidatorTest`, `FoundationSecurityIT`, `MixedCompanyAuthorizationIT`, `CompanyNameJsonEncodingTest`, `backend/src/test/java/br/com/actionfinance/application/**`.

Frontend: `PayReceiptsPage.tsx`, `PayReceiptsPage.test.tsx`, `api.ts`, `App.tsx`, `App.test.tsx`, `AppShell.tsx`, `AppShell.test.tsx`, `app.css`.

Scripts deste ciclo: `scripts/dev/prm009/backup-restore-v12.ps1`, `prove-cursor-pg.mjs`, `bootstrap-public-test-identities.sql` (os `live-proof*` / `seed-hub.sql` são prova **local** já aceite; não correm no apply público).

Documentos: `documents/prompts/ACTIONFINANCE_PRM_009*.md` (inclui autorização do proprietário), `documents/reviews/ACTIONFINANCE_REV_009*.md` (inclui recomendação do analista), este pacote, guia, `DEP_001` se tocado, `documents/README.md`, evidência **resumida** `evidence/prm-009-adendo-001/survey-publico-2026-10-01.md` e `local-artifacts-2026-10-01.md`, `evidence/prm-009-cor-001/cursor-pg-proof.json` + `restore-v12-fk-grants.txt`, `evidence/prm-009/verify-2026-10-01/SUMMARY.txt`.

### 8.2 Incluir — spider

`MonitorCompanyAccess.java`, `MonitorCompanyAccessTest.java`, `OperationalConsoleProperties.java`, `OperationalConsoleHttpController.java`, `MonitorEventsTest.java`, `application-sandbox.yml` (company-scope), contrato 1.4 + adapters `HttpActionHubPayCapabilityAdapter`, `ActionHubPayListIdentity`, `ActionHubPayLookupIdentity`, `SatelliteContractV1/Schema/Config/Properties`, `SatelliteInteractionService`, `DemoSliceRules`, `SatelliteLookupStats`, `DispatchingProviderCapabilityAdapter`, `SatelliteInteractionHttpController`, `OperationalEventType`, `application-local-demo.yml` (âmbitos locais; company-scope off), frontend `monitorEnvironmentBadge.js` + teste, `MonitorShell.jsx` + teste, `api.js`, `monitorProjection.js`, `projectExecutionJourney.js`, `docs/architecture/SPIDER-SATELLITE-CONTRACT-V1.md`, `ADR-SPIDER-MONITOR-IDENTITY-ACCESS.md` se presente.

### 8.3 Incluir — leaction-platform (Hub)

`services/gateway-api/domain/spider-pay-lookup.js`, `spider-pay-lookup.test.js`, `server.js` (**só** o `require` + `registerSpiderPayLookupRoutes`; +2 linhas), `services/gateway-api/scripts/prm009-isolated-schema.sql`.

### 8.4 Excluir — trabalho alheio ou sensível

`lojadepaes/**`, `panne/**`, `qmind*/**`, screenshots/scripts PRM_006, prompts/reviews/screenshots PRM_007 e PRM_008 (ciclo encerrado; não reabrir), `ActionFinance/ops/aws/state/**`, `tfplan-*`, `put-prod-secrets.ps1`, dumps, `.env`, evidência bruta `evidence/prm-009-continuidade-001/logs/*.out.log`, terraform/state Spider sandbox não necessário a este recorte, `invite-monitor-operator.ps1` **não corre**, scripts `scripts/ops/repair-loja*` / restore RDS isolado (PRM_007), `leaction-platform/scripts/deploy/_prod-*` / school catalog, `leaction-platform/frontend/action-hub/src/app/inove4us/**`.

Revisão de conteúdo (não só pastas): os JSON de CONTINUIDADE_001 são prova local já aceite — podem versionar-se os SUMMARY/`live-*.json` sem tokens; **não** versionar logs de processo nem dumps PG.

### 8.5 Comandos Git (autorizados neste escopo)

```
cd C:\Projetos
git checkout -b feat/prm-009-public-receipt-sync
# git add — somente os caminhos da §8.1–8.3
git commit -m "Prepare PRM_009 public receipt-sync with isolated Pay schema and Monitor company scope."
git push -u origin HEAD
```

Um commit, um remoto. Sem três repositórios. Sem `--no-verify`. Sem force.

## 9. Configuração de apply (valores; secrets não impressos)

| Destino | Chave | Valor |
|---|---|---|
| AF runtime | `ACTIONFINANCE_INTEGRATION_HOMOLOG` | `false` |
| AF runtime | `ACTIONFINANCE_RECEIPT_SYNC_ENABLED` | `true` |
| AF runtime | `ACTIONFINANCE_DEMO_AUTH_ENABLED` | `false` |
| AF runtime | `ACTIONFINANCE_SPIDER_BASE_URL` | `https://api.spider.actionhub.com.br` |
| AF runtime | `ACTIONFINANCE_SPIDER_SECRET` | **novo**, distinto do local-demo |
| AF runtime | `ACTIONFINANCE_SPIDER_MONITOR_BASE_URL` | `https://monitor.spider.actionhub.com.br` |
| Spider sandbox | `SPRING_PROFILES_ACTIVE` | `sandbox` |
| Spider sandbox | persistência | memory · `desired_count=1` |
| Spider sandbox | `SPIDER_MONITOR_ALLOWED_COMPANIES` | `9c2e0a10-4f11-4b8a-9c2e-0a104f11000c` |
| Spider sandbox | FORWARD | `https://api.actionhub.com.br` + provider secret |
| Hub EC2 | `ACTIONHUB_PAY_LOOKUP_ENABLED` | `true` |
| Hub EC2 | `ACTIONHUB_PAY_LOOKUP_ISOLATED` | `true` |
| Hub EC2 | `ACTIONHUB_PAY_LOOKUP_PUBLIC_TEST` | `false` |
| Hub EC2 | `ACTIONHUB_PAY_ENVIRONMENT` | **não** alterar para `sandbox` |

## 10. Ordem de implantação (só após autorização)

1. Snapshot RDS AF nomeado `af-pre-prm009-v12` (retenção 7 dias).
2. Criar schema `prm009_public_test` + 4 linhas (`prm009-isolated-schema.sql`) no PG **existente** do Hub. Sem insert em `public.orders`.
3. Publicar código Pay no EC2 + flags da §9. Provar: 401 sem key; 200 no `af-public-test-padaria`; 404 noutro `app_id`; `SELECT count(*) FROM public.orders` inalterado pelo seed.
4. Regra SG exacta da §6.1. Provar HTTPS do NAT AF → `api.spider` (health). Sem WAF/NAT Gateway novos.
5. Publicar engine Spider (imagem do commit §8, desired 1, memory, sandbox, FORWARD, `SPIDER_MONITOR_ALLOWED_COMPANIES`).
6. Publicar SPA Monitor (badge + deep link). Binding já na imagem/env.
7. Migrate AF V8–V12. Conferir `flyway_schema_history` = 1..12. Sem `DROP`.
8. Publicar imagem AF do commit §8 + secrets. `ACTIONFINANCE_RECEIPT_SYNC_ENABLED=true`. `desired_count=1`. Readiness 200.
9. Bootstrap identidades §2. Membership OPERATOR do subject já existente **só** na empresa de teste.
10. Smoke humano no browser: Finance sync → Monitor factos → registos AF com a **mesma** correlação **nova**. Viewer 403. Outra empresa 403/404. Deep link ok; ID da Loja recusado.
11. Indisponibilidade controlada: falha **restrita** à integração/app de teste (Hub isolado ou resposta 5xx só desse `app_id`). **Não** esvaziar `ACTIONFINANCE_SPIDER_SECRET` na tarefa AF (o validador impede o startup e derruba o produto). **Não** derrubar a engine compartilhada. Login e títulos existentes devem continuar a responder.

## 11. Custo (estimativa; **não** verificada de forma independente)

Faixa **US$ 0–2** no arranque, com premissas:

| Premissa | Valor usado |
|---|---|
| Tráfego NAT | um smoke autenticado, \<10 MB HTTPS |
| Snapshot AF | 1 manual, retenção 7 dias, tamanho ≈ RDS actual |
| Schema Hub | KB no PG existente |
| Regra SG | US$ 0 |
| Recursos novos | nenhum (sem ALB, NAT GW, RDS, Cognito, cluster) |

A faixa já contratada do AF (~US$ 35–50/mês) e da sandbox Spider **não** é pedida de novo. Sidecar Hub (~US$ 12–15/mês) **não** faz parte deste pacote.

## 12. Rollback por componente

Desligar flags **não** substitui reverter código.

| Componente | Rollback de processo / imagem | Rollback de dados | Não fazer |
|---|---|---|---|
| Finance imagem | voltar digest `7c4cc0de…da5b65` | V8–V12 **permanecem** | `DROP`, recriar RDS, `terraform destroy` |
| Finance código | a imagem antiga **não contém** `/pay-receipts` nem `receipt-sync`; isso é a reversão do código | linhas importadas ficam; sync pára | apagar títulos da Loja |
| Finance flags | `RECEIPT_SYNC_ENABLED=false`. Manter secret Spider presente se a tarefa continuar no perfil production com a flag ainda true | complementar à imagem | ligar `homolog=true`; esvaziar secret obrigatório com a flag ligada |
| Spider engine | voltar `sandbox-20260928-monitorfix` `72ed3a8c…` **só** se o recorte por empresa permanecer na task/env ou a consola ficar indisponível | RAM some no restart (já é o modo) | desired_count\>1 com memory; imagem antiga **sem** company-scope e sem binding (acesso amplo) |
| Monitor SPA | sync S3/CloudFront da SPA anterior ao commit | — | | 
| Monitor auth | manter `company-scope.enabled=true` e binding só da empresa de teste; se a imagem antiga não tiver scope, **não** a publicar — indisponibilizar o console até haver barreira | — | admin amplo; esvaziar binding numa imagem sem deny-default |
| Pay código | restaurar `gateway-api` **sem** `registerSpiderPayLookupRoutes` / sem `spider-pay-lookup.js` (404 de novo) | schema `prm009_public_test` **conservado** (sem `DROP SCHEMA`) | `DROP` em `public.orders` ou no schema de teste |
| Pay flags | `LOOKUP_ENABLED=false` · `LOOKUP_ISOLATED=false` · `PUBLIC_TEST` continua `false` | complementar ao revert do ficheiro | deixar PUBLIC_TEST no operacional |
| Rede | remover regra `3.143.92.115/32` de `sg-0ad34b305223b59f8` | — | abrir 0.0.0.0/0 |

Imagem antiga do AF **não** desfaz Flyway. Rollback de imagem ≠ rollback do banco.

## 13. O que este pacote recusa

local-demo no público, tokens demo, `homolog=true` em produção, `LOOKUP_PUBLIC_TEST` no Hub operacional, insert em `public.orders`, `ACTIONHUB_PAY_ENVIRONMENT=sandbox` no EC2 operacional, admin amplo no lugar de empresa, token na URL, dados da Loja, payout/cobrança/baixa, Panne, ALB dedicado, RDS da Spider, mensageria nova, recriar RDS do AF, convite/mensagem automática, PRM_010, reabrir PRM_008, resolver PRM_007 neste apply.

## 14. Autorização e aceite

A implantação deste pacote **já está autorizada** ([autorização](../prompts/ACTIONFINANCE_PRM_009_AUTORIZACAO_PROPRIETARIO.md)). A recomendação técnica está em [REV_009_RECOMENDACAO_EXECUCAO_ANALISTA](../reviews/ACTIONFINANCE_REV_009_RECOMENDACAO_EXECUCAO_ANALISTA.md).

Autorização de implantação ≠ aceite do resultado. Componentes publicados. A jornada autenticada (sync novo → Monitor → retorno no Finance) e o aceite só depois da prova no browser do operador.
