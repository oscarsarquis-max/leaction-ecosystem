# SPIDER-PROMPT-018 — Laboratório de Falhas e Jornadas Operacionais

## Baseline

- Produto: **0.18.0** · boundary **MOCK_ONLY**
- Predecessor: SPIDER-PROMPT-017 VERIFIED
- Flags (default **false**): `spider.failure-lab.enabled`; superfícies `spider.failure-lab.http.enabled` e `spider.failure-lab.local-demo.enabled` (exigem o master ligado)
- HTTP do lab exige também `spider.console.http.enabled=true`
- Catálogo: `implementation/failure-lab-scenarios-v1.json` (7 cenários) · runbooks: `implementation/failure-lab-runbooks-v1.json`

## Missão

Demonstrar, em ambiente **MOCK_ONLY**, jornadas operacionais controladas: injeção de falha só via adapters/mocks, verificação de observações esperadas, pacote de evidência redigido e runbooks provisórios. O Failure Lab **não** controla a Engine nem altera políticas de execução — apenas dispara cenários mock, observa o Data Plane e fecha o ciclo com evidência.

## Flags

| Flag | Papel |
|------|--------|
| `spider.failure-lab.enabled` | Master do laboratório (OFF_BY_DEFAULT) |
| `spider.failure-lab.http.enabled` | Expõe API `/v1/console/failure-lab/*` |
| `spider.failure-lab.local-demo.enabled` | Demo local (profile `local-demo`) |
| `spider.failure-lab.evidence.enabled` | Montagem do pacote de evidência (default true quando o lab está ativo) |

Limites configuráveis: concorrência de runs, execuções por run, duração máxima.

## Catálogo — 7 cenários

| Código | Categoria | O que demonstra |
|--------|-----------|-----------------|
| `RETRY_THEN_SUCCESS` | RETRY | Indisponibilidade momentânea absorvida por retentativa; execução conclui em sucesso |
| `TECHNICAL_TERMINAL_FAILURE` | EXECUTION | Resposta inválida → falha técnica terminal, sem retentativa |
| `WAIT_AND_RESUME` | WAIT_RESUME | Espera assíncrona aberta e retomada por sinal simulado |
| `SIGNAL_SECURITY_REJECTED` | SECURITY | Sinal com credencial inválida rejeitado; espera intacta; sem vazamento sensível |
| `CALLBACK_UNCERTAIN` | CALLBACK | Desfecho externo incerto → reconciliação, sem promover sucesso/falha |
| `INSUFFICIENT_SAMPLE` | OPERATIONAL_HEALTH | Sem volume mínimo → `INSUFFICIENT_DATA` (não submete execução) |
| `OPERATIONAL_DEGRADATION` | OPERATIONAL_HEALTH | Sequência de falhas simuladas refletida na leitura operacional (ou inconclusiva se amostra pequena) |

Todos com `targetBoundary=MOCK_ONLY`. Parâmetro permitido típico: `note` (allowlist fechada por cenário).

## API

Base: `/v1/console/failure-lab` (ativa só com console HTTP + failure-lab + failure-lab.http).

| Método | Caminho | Ação authz |
|--------|---------|------------|
| `GET` | `/scenarios` | `VIEW_FAILURE_LAB` |
| `POST` | `/runs` | `EXECUTE_MOCK_FAILURE_SCENARIO` |
| `GET` | `/runs/{labRunId}` | `VIEW_FAILURE_LAB` |
| `GET` | `/runs/{labRunId}/evidence` | `VIEW_FAILURE_LAB_EVIDENCE` |

DenyAll / flags off / cenário inexistente → **404** (sem enumeração). Parâmetro fora da allowlist → 400; limite de concorrência → 409. `POST /runs` responde **202 Accepted** com o run.

## Authz

Ações do console: `VIEW_FAILURE_LAB`, `EXECUTE_MOCK_FAILURE_SCENARIO`, `VIEW_FAILURE_LAB_EVIDENCE`. Credencial via `X-Spider-Credential-Ref` (mesmo modelo do console operacional).

## Predicados de observação

Conjunto fechado (`ObservationPredicateType`) — sem expressão livre:

- `EXECUTION_REACHED_STATE`
- `OPERATIONAL_EVENT_EMITTED`
- `WAIT_OPENED` / `WAIT_RESUMED`
- `ATTEMPT_COUNT_AT_LEAST`
- `CALLBACK_REACHED_STATUS`
- `SIGNAL_REJECTED_WITH_CATEGORY`
- `HEALTH_DIMENSION_REACHED_STATUS`
- `SLO_EVALUATION_REACHED_STATUS`
- `SLI_STATUS_EQUALS`
- `HEALTH_OVERALL_STATUS`
- `NO_SECRET_EXPOSED`

## Ciclo do run e evidência

Estados: `REQUESTED | RUNNING | OBSERVING | VERIFIED | FAILED | TIMED_OUT | CANCELLED | INCONCLUSIVE`.

`FailureLabEvidenceBundle` (`schemaVersion=1`): `evidenceId`, `labRunId`, `scenarioRef`, `boundary=MOCK_ONLY`, refs de execução, resultados de verificação, `redactionStatus=APPLIED`, `completenessStatus` (`COMPLETE`|`PARTIAL`), `digest`.

## Relação com a Engine

O Failure Lab **não** decide rotas, não altera a máquina de estados e não injeta falha em produção. A Engine continua responsável só pela execução canônica; o lab usa submit/mock/signal já existentes e verifica o que ficou observável.

## Boundary MOCK_ONLY

- Sem IdP/KMS/legado real
- Sem fault injection em infraestrutura produtiva
- Runbooks são provisórios de laboratório (não procedimento de produção)
- Banner permanente na UI: demonstração Mock · falhas simuladas · sem legados reais

## Console

Nav **Failure Lab** (`FailureLab.jsx`): catálogo, confirmação explícita antes de executar, status do run, predicados, runbook e evidência. Banner `MOCK_ONLY` obrigatório.

## Screenshots

| Arquivo | Conteúdo |
|---------|----------|
| `018-failure-lab-catalog-desktop.png` | Catálogo de cenários |
| `018-failure-lab-running-desktop.png` | Run em andamento |
| `018-failure-lab-verified-desktop.png` | Run verificado |
| `018-failure-lab-runbook-evidence-desktop.png` | Runbook + evidência |
| `018-failure-lab-mobile.png` | Viewport mobile |

Geração: `frontend/scripts/capture-failure-lab-screenshots.mjs` (com local-demo e flags do lab ligadas).

## Fechamento do Grupo A

Com CAP-015–018 **VERIFIED**, o `GROUP_A_VISIBILITY_OBSERVABILITY` fecha **4/4**. Sequência: **SPIDER-PROMPT-019** (Grupo B) — **VERIFIED** no baseline 0.19.0.

## Referências

- ARCH-010 (fault injection / resposta a falhas)
- ARCH-013 (superfície Failure Lab)
- ARCH-014 (linguagem de negócio)
- Manifesto CAP-018
- Roadmap 016–026
