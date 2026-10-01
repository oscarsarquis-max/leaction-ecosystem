# ACTIONFINANCE_REV_009_INC_001

| Campo | Valor |
|---|---|
| Data | 01/10/2026 |
| Prompt | [ACTIONFINANCE_PRM_009_INC_001](../prompts/ACTIONFINANCE_PRM_009_INC_001.md) |
| Autorização | A da implantação PRM_009 permanece; não foi pedida outra |
| Aceite | **Não** |

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
