# ACTIONFINANCE_REV_009_EXECUCAO_PUBLICA

| Campo | Valor |
|---|---|
| Data | 01/10/2026 |
| Origem | [Pacote](../operations/ACTIONFINANCE_PRM_009_PACOTE_PUBLICACAO.md) · [recomendação](ACTIONFINANCE_REV_009_RECOMENDACAO_EXECUCAO_ANALISTA.md) · [autorização](../prompts/ACTIONFINANCE_PRM_009_AUTORIZACAO_PROPRIETARIO.md) |
| Executor | Cursor |
| Autorização de implantação | **Sim** — não é aceite |
| Implantação executada | **Sim** — componentes do recorte publicados na infra existente |
| Jornada pública autenticada | **Não** — sync novo no Finance exige login Cognito no browser do operador |
| Aceite do proprietário | **Não** |

PRM_007 (invalidação de sessão no restore) permanece pendente à parte. PRM_010 não emitido. PRM_008 não reaberto.

## Impedimento concreto da última milha

A API `POST /api/v1/pay-receipts/sync` e o Monitor exigem sessão OIDC humana. Senha, MFA e tokens não entram neste chat. Sem essa sessão o executor **não** inicia uma execução nova no Finance, **não** abre o deep link correspondente e **não** confirma o retorno persistido. O roteiro do proprietário está no [guia](../operations/ACTIONFINANCE_PRM_009_GUIA_PROPRIETARIO.md).

## URLs públicas verificadas

| Superfície | URL | Prova (01/10/2026) |
|---|---|---|
| Finance | https://actionfinance.actionhub.com.br | 200 · SPA `index-C0gESpWW.js` |
| Recebimentos do Pay | https://actionfinance.actionhub.com.br/pay-receipts | 200 `text/html` após correção do `SpaController` |
| API sessão Finance | `/api/v1/me` · `/api/v1/pay-receipts` | 401 sem sessão (rota existe; sem anónimo) |
| Info pública Finance | `/api/v1/system/info` | `homologIntegration=false` · `receiptSyncEnabled=true` · `accessMode=OIDC` · `spiderIntegrationStatus=RECEIPT_SYNC` |
| Monitor | https://monitor.spider.actionhub.com.br | 302 para Cognito hosted UI; cookie de estado HttpOnly; sem corpo anónimo |
| Pay lookup (FORWARD) | https://api.actionhub.com.br/v1/integration/payments | 401 sem key; 200 `count=4` no app de teste; 200 `count=0` em `loja-de-paes` |
| Pay apex | https://actionhub.com.br/v1/integration/payments | 404 (Next/nginx do FE). A Spider **não** usa este host |

Empresa de teste: **Padaria de teste público** · código `af-public-test-padaria` · id `9c2e0a10-4f11-4b8a-9c2e-0a104f11000c` · ambiente de listagem **HOMOLOG**. Proibida: Loja de Pães `624023a4-57e3-415c-b7d0-925ca1acd3b7`.

## Identidade do Monitor (`owner:sandbox`)

Cadeia observada: CloudFront Lambda@Edge OIDC → grupo `spider-sandbox-operators` → cookie de sessão → `X-Spider-Credential-Ref=sandbox-operator` → principal de backend **`owner:sandbox`**. Isto é um **principal compartilhado do recorte sandbox**, não uma identidade Cognito individual. O recorte de empresa é o binding `SPIDER_MONITOR_ALLOWED_COMPANIES=9c2e0a10-4f11-4b8a-9c2e-0a104f11000c`. Sem sessão o Monitor não entrega o console. Troca de ID de outra empresa deve continuar 404 nos canais da consola.

## Isolamento e integridade (Hub)

| Teste | Resultado |
|---|---|
| `public.orders` após seed isolado | **15** (inalterado pelo apply) |
| `prm009_public_test.orders` | **4** sintéticas do app de teste |
| Lookup localhost `:4001` `af-public-test-padaria` | 200 · count=4 · `testLabeled=true` · `HOMOLOG` |
| Lookup localhost `:4001` `loja-de-paes` | 200 · count=0 (página vazia isolada, não 404) |
| Lookup público `api.actionhub.com.br` sem key | 401 |
| Lookup público app de teste / Loja | 200 count=4 / 200 count=0 |
| `ACTIONHUB_PAY_LOOKUP_PUBLIC_TEST` | **false** |
| `ACTIONHUB_PAY_ENVIRONMENT=sandbox` no EC2 | **não** ligado |
| Insert em `public.orders` | **não** feito |
| `DROP SCHEMA` | **não** executado |

Finance: `homolog=false`, `demo-auth=false`, `receipt-sync-enabled=true`. Títulos/login existentes continuam a responder (401 sem sessão; não houve esvaziamento do secret Spider).

## Versões publicadas

| Peça | Valor |
|---|---|
| Branch | `feat/prm-009-public-receipt-sync` |
| Commits | `c407591d` · `e2a45cc2` · `03d051c5` (SPA `/pay-receipts`) |
| HEAD | `03d051c5a3ad38b8cb202ae06dcad908cb52f0f7` |
| AF imagem | `actionfinance@sha256:ec0c62c59c7936365f8aab2aa284bf52f310bd3c62c9fb9dd688b34d6532dfbc` · tag `prm009-03d051c5` |
| AF tarefa | `actionfinance-web:3` · running=1 |
| AF JAR desta imagem | `e4d305b6f14260b14f1ebb217834823789d5a3b61068da1e6a906a372110dd2c` |
| AF SPA | `index-C0gESpWW.js` (mesmo digest do candidato) |
| Flyway RDS | `1,2,3,4,5,6,7,8,9,10,11,12` |
| Snapshot pré-apply | `af-pre-prm009-v12` · available |
| Bootstrap | tenant=1 · company=1 · mapping=1 · membership=1 |
| Spider imagem | `spider-sandbox-backend@sha256:8709085a9f96daedbab22ce3b200b4c5d20a02c5998eb93077935239ab99569a` |
| Spider tarefa | `spider-sandbox-backend:7` · HEALTHY · desired=1 · memory · profile `sandbox` |
| Spider FORWARD | `https://api.actionhub.com.br` |
| Monitor SPA | `index-WQl_rw8l.js` · invalidação `IDLVYWUQDUVI8X1JEF63MXWM6U` Completed |
| SG ALB Spider | `sg-0ad34b305223b59f8` · `3.143.92.115/32` `af-nat-prm009` |

A imagem AF `sha256:1b3fb968…` (`actionfinance-web:2`) ficou para trás de propósito: o host `/pay-receipts` respondia 404 JSON porque o `SpaController` não encaminhava o shell. Corrigido em `03d051c5` + `SpaControllerTest`.

## Cuidados observados

1. Working tree misto preservado: só o conjunto PRM_009 na branch. Rebuild a partir do commit, não de ficheiros excluídos.
2. `owner:sandbox` não foi apresentado como sujeito Cognito individual.
3. Secret obrigatório da tarefa AF **não** foi esvaziado. Indisponibilidade controlada do secret **não** ensaiada.
4. Schema isolado conservado. Sem `DROP SCHEMA`.
5. Engine sandbox teve janela a zero durante o rollout `:6`→`:7` (maxPercent 100 + drain 300 s). `maximumPercent` foi 200 só para arrancar a tarefa `:7` e voltou a 100. AF usou rolling 200/100 e manteve login no ar.
6. Apex `actionhub.com.br` continua 404 no lookup; a correção no escopo foi apontar a Spider para `api.actionhub.com.br`, sem alterar o nginx do FE.

## O que falta para o aceite

No browser do operador, com a sessão já usada no Finance público:

1. Empresa de teste (não a Loja) → **Sincronizar recebimentos**.
2. Anotar o id da execução e a hora.
3. **Ver execução na Spider** → a mesma execução no Monitor.
4. Factos Finance → Spider → ActionHub Pay e regresso persistido no Finance.

Até isso ocorrer: autorização de implantação **≠** aceite.
