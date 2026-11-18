# SPIDER_REV_RECONCILIACAO_ROTA_FINANCE_001

09/11/2026. Leitura da rota de recebimentos da Loja. Nada foi publicado, alterado ou sincronizado.

A chamada parte do ActionFinance. O Pay não empurra o recebimento para a Spider. O host `callbacks.spider.actionhub.com.br` responde 404 e, no Git, o ingresso de callbacks não tem rota.

O código da Spider está em `C:\Projetos\spider` dentro do monorepo. O checkout atual é `feat/actionfinance-extrato-032`, HEAD `249541b4`, com 0 arquivos sujos em `spider` e 35 no monorepo. A branch `feat/spider-monitor-persistence-b` (HEAD `ed82b476`, 33 arquivos sujos) é a única árvore em que o perfil `production` aparece, e isso está fora do commit: `application-production.yml` e `ProductionProfileGuard.java` não são rastreados; o controller e o `SatelliteSandboxConfig` estão modificados. No commit, o `POST /v1/satellites/interactions` só existe nos perfis `local-demo` e `sandbox`.

Não havia pasta de revisões nem pasta de prompts com esse nome. Os prompts antigos estão em `spider/docs/technical`. Este relato ficou em `spider/docs/reviews/`. O prompt ficou em `spider/docs/prompts/SPIDER_PROMPT_REC_001.md`.

## Mapa

| Etapa | Componente | Endpoint | Estado guardado em | Evidência |
|---|---|---|---|---|
| Finance pede a lista | `HttpSpiderInteractionClient` e `PayReceiptSyncService` | `POST /v1/satellites/interactions`, contrato 1.4, objetivo `LIST_EXTERNAL_PAYMENTS` | Postgres do Finance. A chave da página é `list-{execução}-{página}` | Código do Finance. A task `actionfinance-web:28` aponta o host `api.spider.actionhub.com.br` |
| Spider recebe | `spider-runtime-prod` (`spider-runtime-prod:4`), 2/2, rollout concluído em 09/11 às 03:06 (−03) | o mesmo POST. Autenticação por identificador e segredo de satélite | Idempotência em memória, chave `satélite:idempotencyKey`. Canônico em `jpa` | DNS da `api.` cai no ALB `spider-prod-canary`. Perfil `production`, satélite habilitado. Imagem `sha256:d116496379aff3c341682908f2ac7fef5ac06dd46ab59fbf332a2c22cad8bec0` |
| Spider consulta o Pay | `HttpActionHubPayCapabilityAdapter` | `POST /v1/provider/capabilities/LIST_PAYMENT_TRANSACTIONS/executions`. Header de credencial do Pay | Não guarda a resposta | Host configurado: `api.actionhub.com.br`. O adaptador não escreve log |
| Monitor | `spider-monitor-projector-prod:3` (1/1) e `spider-monitor-query-prod:3` (1/1). O console HTTP só está ligado no plano query | `monitor.spider.actionhub.com.br` responde 302 para o Cognito `spider-prod-monitor` | Projeção em `jpa` no RDS `spider-prod-canary-pg`. No runtime o modo do Monitor é `memory` | Variáveis dos serviços. Sem volume na task |
| Entrada pública | CloudFront do apex | `GET https://spider.actionhub.com.br/` responde 301 para o Monitor | Página estática | Resposta 301 |
| Callbacks | API Gateway sem rota | `GET https://callbacks.spider.actionhub.com.br/` responde 404 | Nada | Resposta 404 e o módulo `callbacks` do Git |

O contrato usado é o Satellite Contract V1, só a listagem 1.4. Não há caminho paralelo para o recebimento. A consulta individual 1.3 não está no arquivo de produção.

Isolamento: um segredo de satélite e um segredo de Pay. A empresa vai no corpo (`companyId`) e o vínculo com o aplicativo do Pay vai em `payAppId`. O arquivo de produção não commitado admite uma empresa e o guard recusa a empresa de teste. O yaml de sandbox commitado admite duas empresas no mesmo segredo; essa não é a configuração da task que está no ar. A idempotência não inclui a empresa na chave. Com duas tasks, a mesma chave pode ser atendida duas vezes. O Finance recusa outra sincronização simultânea da mesma empresa e ambiente.

Nomes de ambiente no runtime, sem valores: `SPIDER_ACTIONHUB_PAY_APP_ID`, `SPIDER_ACTIONHUB_PAY_EDGE_URL`, `SPIDER_CANONICAL_JDBC_URL`, `SPIDER_CANONICAL_PERSISTENCE_MODE`, `SPIDER_CONSOLE_HTTP_ENABLED`, `SPIDER_CORS_ORIGINS`, `SPIDER_MONITOR_ALLOWED_COMPANIES`, `SPIDER_MONITOR_HEALTH_ENABLED`, `SPIDER_MONITOR_JDBC_URL`, `SPIDER_MONITOR_PERSISTENCE_MODE`, `SPIDER_OBSERVATION_DISPATCH`, `SPIDER_PLANE`, `SPIDER_PRODUCTION_CREDENTIAL_REF`, `SPIDER_SATELLITE_ENABLED`, `SPRING_PROFILES_ACTIVE`. Segredos, só os nomes: `SPIDER_ACTIONFINANCE_APPLICATION_SECRET`, `SPIDER_ACTIONHUB_PAY_EDGE_SECRET`, `SPIDER_JWT_SECRET`, `SPIDER_MONITOR_JDBC_PASSWORD`, `SPIDER_MONITOR_JDBC_USERNAME`.

Não há volume na task. O RDS `spider-prod-canary-pg` (Postgres, `available`) guarda o canônico e a projeção do Monitor. Um restart perde a idempotência em memória e o Monitor em memória do runtime. Não perde o que já foi para o RDS nem o que o Finance gravou.

Há outro cluster, `spider-sandbox`, com RDS próprio. A `api.spider.actionhub.com.br` não aponta para o ALB dele. Não foi inspecionado.

## Documentos

| Documento | Caminho | Último commit |
|---|---|---|
| ARCH-014 | `spider/docs/architecture/SPIDER-ARCH-014-arquitetura-funcional-do-produto.md` | 2026-09-09 |
| ARCH-015 | `spider/docs/architecture/SPIDER-ARCH-015-context-intelligence-plane.md` | 2026-09-09 |
| ARCH-016 | `spider/docs/architecture/SPIDER-ARCH-016-execution-planning-business-capability-composition.md` | 2026-09-03 |
| ARCH-017 | `spider/docs/architecture/SPIDER-ARCH-017-satellite-architecture.md` | 2026-09-13 |
| SATELLITE-CONTRACT-V1, que se identifica como SAT-003 | `spider/docs/architecture/SPIDER-SATELLITE-CONTRACT-V1.md` | 2026-10-01 |

Não encontrados como documento: MONITOR-001, MON-001A, CAP e CTX. De CTX só há capturas em `spider/docs/technical/screenshots/`. SAT-003 não tem arquivo separado. ARCH-017 e o contrato continuam marcados DEMO ONLY.

## Riscos

O que está commitado não publica a rota no perfil `production`. A task que recebe a `api.` usa esse perfil. A ligação está em arquivos não commitados, e a imagem `sha256:d1164963` não foi amarrada a um commit.

A idempotência da listagem mora na memória de cada task. São duas tasks. Um restart ou um balanceamento repetem a chamada ao Pay. O Finance segura a corrida da mesma empresa, mas a Spider não compartilha a chave.

Em 7 dias o log `/spider/production/runtime` tem 121 mil linhas e todas as que trazem caminho são `GET /actuator/health/liveness`. Nenhuma linha de satélite, nenhuma do Pay e nenhum ERROR. Houve 3 subidas e 3 encerramentos graciosos. Não dá para ver uso real da rota nessa janela.

O apex ainda tem, na mesma distribuição, o nome `sandbox-monitor` e um bucket de Monitor sandbox. A resposta atual é o 301 para o Monitor de produção.

## Não verificado

- Se a imagem em execução contém o controller do perfil `production`. O digest não tem commit e a imagem não foi aberta.
- `GET` direto em `api.spider.actionhub.com.br` a partir daqui falhou (`URLError`). O POST não foi chamado.
- Quantas chamadas ao Pay ocorreram: o adaptador não loga, e não houve linha de satélite para inferir.
- O valor de `SPIDER_MONITOR_ALLOWED_COMPANIES`. Só o nome foi lido.
- O cluster `spider-sandbox`, de propósito.
- O conteúdo do RDS. O banco não foi aberto.
