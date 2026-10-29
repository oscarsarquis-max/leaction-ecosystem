# ACTIONFINANCE_REV_009_INC_001

| Campo | Valor |
|---|---|
| Data | 01/10/2026 |
| Prompt | [ACTIONFINANCE_PRM_009_INC_001](../prompts/ACTIONFINANCE_PRM_009_INC_001.md) · [complemento](../prompts/ACTIONFINANCE_PRM_009_INC_001_COMPLEMENTO.md) |
| Autorização | A da implantação PRM_009 permanece; não foi pedida outra |
| Aceite | **Não** — jornada autenticada ainda depende de um login novo do operador |

## Tentativa AF preservada

| Campo | Valor |
|---|---|
| Horário | 2026-10-01T21:07:21Z |
| Correlação | `afp-5092b7c9-66d5-4c11-8f35-ccfbd1ae230a-1` |
| Finance | `actionfinance-web:3` · digest `sha256:ec0c62c59c7936365f8aab2aa284bf52f310bd3c62c9fb9dd688b34d6532dfbc` |
| Spider | `spider-sandbox-backend:7` |
| Monitor SPA anterior | `index-WQl_rw8l.js` |

Sem cookies, senhas ou tokens neste relato.

## Causas demonstradas

### 1. Finance → Spider — primeira fronteira: WAF da API

Log AF (`/actionfinance/web`): `spider list transport failed` · `403 Forbidden` · corpo HTML `<title>403 Forbidden</title>`.

A tarefa AF alcança `https://api.spider.actionhub.com.br` (SG `/32` do NAT `3.143.92.115`). O WAF regional `spider-sandbox-api` (default BLOCK) só libertava:

- `/v1/console` + `x-spider-origin-secret` (CloudFront)
- IP do operador `191.57.226.77/32`

`POST /v1/satellites/interactions` a partir do NAT do AF era bloqueado no WAF. Não é CORS, não é perda de RAM, não é falta de login do Finance.

Reparo: IP set `spider-sandbox-af-nat-v4` = `3.143.92.115/32` e regra `allow-af-nat-satellites` (AND path `/v1/satellites`). Sem abrir 0.0.0.0/0. Sem desligar autenticação de satélite.

### 2. Navegador do Monitor — primeira fronteira: CSP + host errado no bundle

O bundle público `index-WQl_rw8l.js` continha `https://api.spider.actionhub.com.br`. O cliente faz `fetch` cruzado. A política CloudFront tem `connect-src 'self'`. O browser bloqueia → `TypeError: Failed to fetch`.

O NAT do AF **não** é o caminho do browser. Liberar o NAT não prova o Monitor. A API directa `api.spider` a partir deste host continua a expirar no SG (esperado).

O caminho correcto do bundle actual é a mesma origem: `https://monitor.spider.actionhub.com.br/v1/console/*` → CloudFront → ALB com o secret de origem.

Reparo: rebuild **sem** `VITE_SPIDER_API_BASE`. Artefacto `index-wXeIWmk1.js` (0 ocorrências de `api.spider.actionhub.com.br`). S3 + invalidação `I7VM5VYT6CGHH42DZ4WIH1L2SX` Completed.

### 3. Edge 302 em `/v1/console` (agravava o Failed to fetch)

Sem sessão, `/v1/console/executions` respondia **302** para o Cognito. Um `fetch` que seguisse esse redirect violava `connect-src 'self'`.

Reparo: Lambda `spider-sandbox-monitor-oidc:3`. API sem sessão → **401** `application/problem+json`. Página HTML continua a redirecionar ao login. Autenticação não foi desligada.

Prova sem sessão (executor): `GET https://monitor.spider.actionhub.com.br/v1/console/executions` → 401 JSON.

## O que não era a causa (e foi verificado)

| Hipótese | Evidência |
|---|---|
| Falta de login no Finance | Log da tentativa autenticada com correlação AF |
| Lista vazia / RAM | Transport 403 e Failed to fetch; não 200 vazio |
| CORS da engine | O bloqueio do Monitor foi CSP no CloudFront; o AF foi WAF HTML 403 |
| Health da engine | `:7` running=1; health ≠ API de negócio |

## Pendências já conhecidas (não são este incidente)

Flyway da tarefa `actionfinance-migrate`: migrações V8–V12 **aplicadas** (`now at version v12`); o processo saiu 1 depois, por `ClientRegistrationRepository` com `web-application-type=none`. Schema público: `flyway=1..12`. Sem DROP.

Política IAM temporária `actionfinance-bootstrap-once`: **ausente** (`NoSuchEntity`).

## Alterações

| Peça | Alteração |
|---|---|
| WAF API | regra `allow-af-nat-satellites` |
| Monitor SPA | `index-wXeIWmk1.js` same-origin; UX: indisponibilidade ≠ vazio; botão tentar novamente |
| Edge | `:3` 401 JSON em `/v1/console` e `/v1/canonical` sem sessão |
| AF | `withMonitor` só emite URL se existir `spiderMessageId` remoto |
| Spider código | `canonical-principals=owner:sandbox` para fluxo canónico sem `companyId`; satélite sem empresa continua oculto. **Imagem `:7` ainda não republicada com isto.** |

Testes: `MonitorCompanyAccessTest` + `MonitorEventsTest` exit 0; edge `index.test.js` 7/7; frontend `api.test.js` + `MonitorShell.test.jsx` 10/10.

## O que ainda falta para devolver a jornada

Não encerrar com HTML/401 anónimo. Falta a sessão do operador no browser:

1. Recarregar o Monitor (hard refresh) e confirmar lista/eventos **sem** Failed to fetch.
2. No Finance, empresa de teste, **Sincronizar recebimentos** — esperar 4 registos do schema isolado.
3. O link **Ver execução na Spider** só deve aparecer se a engine devolveu `spiderMessageId`.
4. Repetir sync sem duplicar.

Até o proprietário concluir esses três passos no browser, o aceite permanece **Não**. PRM_007 separado. PRM_010 não emitido.

## Complemento — 01/10/2026 ~22:10Z

O proprietário determinou “precisamos ajustar”. As evidências novas não são falta de login no Finance. A mudança de texto no AF também não prova recuperação. Os reparos WAF/CSP acima permanecem factuais; não fecharam estas falhas.

### Tentativas AF preservadas (não apagadas)

| id | início UTC | status | erro (recorte) | importados | `spider_message_id` |
|---|---|---|---|---|---|
| `b433dd29-5e69-4a1f-a60a-bb846f8515dc` | 21:51:32 | FAILED | A Spider não devolveu a listagem. | 0 | none |
| `9d147f2c-3774-4244-978d-31a5be4537c3` | 21:50:05 | FAILED | A Spider não devolveu a listagem. | 0 | none |
| `1396596a-7ce7-41fd-bb76-27599a9a64ad` | 21:49:34 | FAILED | A Spider não devolveu a listagem. | 0 | none |
| `5092b7c9-66d5-4c11-8f35-ccfbd1ae230a` | 21:07:20 | FAILED | Não foi possível consultar a Spider… | 0 | none |

Correlação de página da primeira: `afp-5092b7c9-…-1` (WAF 403). As três seguintes chegaram à engine: HTTP 200 com status ≠ READY, sem messageId remoto. `pay_receipt_transaction=0`. Flyway `1..12`. Sem limpeza de tabelas.

### Causa demonstrada A — listagem

Publicado em `spider-sandbox-backend:7`: `SPIDER_ACTIONHUB_PAY_EDGE_URL=https://api.actionhub.com.br`. O adapter Java faz `POST /v1/provider/capabilities/LIST_PAYMENT_TRANSACTIONS/executions`. Antes do reparo, o Hub público respondia **404 HTML** `Cannot POST /v1/provider/capabilities/…`. O GET `/v1/integration/payments` já existia (401 sem key). O adapter engolia o 404 como `PROVIDER_UNAVAILABLE`; o AF convertia READY-only em “A Spider não devolveu a listagem.” Não é lista vazia válida, não é rejeição de empresa, não é falta de login.

Segredo da Spider e `ACTIONHUB_PAY_PROVIDER_SECRET` coincidem (`sha12=13cd91b51f52`). Binding `9c2e0a10-…00c` → `af-public-test-padaria`. Contrato 1.4. Schema `prm009_public_test` intacto.

Reparo: a mesma rota de capability foi acrescentada no `gateway-api` já publicado, reutilizando a listagem isolada. Sem sidecar, sem simulador, sem AF→Pay, sem READY fabricado, sem `public.orders`.

Prova no host (loopback com a credencial do Hub, só contagens/ids): POST COMPLETED `count=4` ids `…0101`…`…0104`. `public.orders=15`. `isolated_orders=4`. Público sem key: **401 JSON** (rota existe).

### Causa demonstrada B — callback do Monitor

A mensagem “O retorno de autenticação é inválido ou já foi usado” é o ramo `!ticket || !code || state≠ticket.state` do Edge. O reparo `:3` fazia `unauthorizedApi()` **apagar** `__Host-SpiderSt`. A SPA, sem sessão, consulta `/v1/console/*` e recebia 401 + `Set-Cookie` a limpar o state de um login em curso. Não é senha errada; não se concluiu recarga do callback antigo.

Reparo: Edge `:4` — API sem sessão continua 401 `application/problem+json` `Cache-Control: no-store`, **sem** `Set-Cookie`. Validação de state/PKCE/TLS/grupo intacta. Callback sem código continua 403 e limpa o state (esperado). CloudFront `E2E4ORTD4DHI1D` associado a `:4`, Status Deployed.

Prova anónima: `GET /v1/console/executions` → 401 JSON, **sem** `Set-Cookie`.

### Alterações deste complemento

| Peça | Versão | Alteração |
|---|---|---|
| Hub `gateway-api` | git_sha público anterior `49b2a83`; ficheiro `spider-pay-lookup.js` aplicado no EC2 | POST capability 1.4 |
| Edge | `spider-sandbox-monitor-oidc:4` | 401 da API não apaga state |
| AF código | local; imagem publicada continua `:4` `sha256:ee05dbd5…` | log sanitizado + distinção REJECTED/UNAVAILABLE (ainda não republicado) |
| Spider engine | `:7` inalterada | URL e binding já correctos; faltava o destino Hub |

Testes: Hub `spider-pay-lookup.test.js` 15/15; Edge `index.test.js` 8/8; AF `HttpSpiderInteractionClientTest` exit 0.

### Pendências já conhecidas (não são causa)

Flyway da tarefa migrate: V8–V12 aplicadas; o processo migrate ainda pode sair 1 por `ClientRegistrationRepository`. Schema `1..12`. Política `actionfinance-bootstrap-once`: **ausente**. Política pontual `actionfinance-inc001-query-once`: criada e **removida**. PRM_007 separado.

### O que falta para o aceite

Checks independentes deste complemento estão feitos. Falta **uma** sessão humana nova:

1. Em **https://monitor.spider.actionhub.com.br**, iniciar login novo (não reabrir o callback antigo).
2. Com a sessão do Finance já autenticada, empresa Padaria de teste público, uma sincronização nova.

Depois disso o executor confere persistência dos quatro ids, ausência de duplicado, deep link e recusas. Aceite continua **Não** até essa jornada. Sem PRM_010. Sem redesign.
