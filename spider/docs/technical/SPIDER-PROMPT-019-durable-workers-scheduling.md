# SPIDER-PROMPT-019 — Runtime de Workers Duráveis e Scheduling

## Baseline

- Produto: **0.19.0** · capability boundary **SIMULATED_INFRASTRUCTURE** · integrações **MOCK_ONLY**
- Predecessor: SPIDER-PROMPT-018 VERIFIED (Grupo A fechado 4/4)
- Grupo corrente: `GROUP_B_RUNTIME_OPERATIONS` (1/3)
- Flags (default **false**): `spider.worker-runtime.enabled`; superfícies `spider.worker-runtime.http.enabled` e `spider.worker-runtime.local-demo.enabled` (exigem o master ligado)
- HTTP do runtime exige também `spider.console.http.enabled=true`
- Drain HTTP exige `spider.worker-runtime.allow-drain=true` **ou** `local-demo.enabled=true`

## Missão

Dar **durabilidade e visibilidade operacional** ao agendamento dos processadores canônicos já existentes: claim com lease, fencing token, heartbeat, drain ordenado e leitura de backlog — sem inventar trabalho novo e sem duplicar a semântica dos processors. O runtime é a camada de **posse e ciclo**; a Engine e os processors continuam donos do efeito canônico.

## Tipos de worker (7)

Conjunto fechado (`WorkerType`). Cada tipo aponta para um processador/serviço já existente:

| WorkerType | Schedule code | Intervalo | Processador / serviço |
|------------|---------------|-----------|------------------------|
| `SIGNAL_APPLICATION` | `sched:signal-application@1` | 2s | `ExternalSignalApplicationProcessor` |
| `WAIT_EXPIRY` | `sched:wait-expiry@1` | 2s | `WaitExpiryProcessor` |
| `CALLBACK_DELIVERY` | `sched:callback-delivery@1` | 2s | `CallbackOutboxProcessor` |
| `CALLBACK_RECONCILIATION` | `sched:callback-reconciliation@1` | 3s | reconciliação de callback |
| `CALLBACK_RECOVERY` | `sched:callback-recovery@1` | 5s | `CallbackProcessingRecoveryService` |
| `SIGNAL_APPLICATION_RECOVERY` | `sched:signal-application-recovery@1` | 5s | recovery de aplicação de sinal |
| `PROTECTED_ENVELOPE_MAINTENANCE` | `sched:protected-envelope-maintenance@1` | 30s | manutenção de envelope protegido |

Catálogo versionado em código (`WorkerRuntimeCatalog`, `SCHEDULE_DEFINITION_VERSION=1.0`). Não há definição arbitrária de trabalho pela borda.

## Schedules

- Um agendamento durável por tipo (`DurableSchedule`): próxima elegibilidade, owner, lease, fencing token, último desfecho.
- Claim atômico (CAS): só um worker vence a disputa; conclusão usa o fencing token corrente.
- Outcomes: `SUCCESS` | `PARTIAL` | `SKIPPED` | `FAILED` (e recusa de conclusão stale).
- Tick / heartbeat / stale-after configuráveis; defaults conservadores no properties.

## Lease e fencing

- **Lease**: posse temporária do schedule; vence por tempo (`leaseUntil`), não por exclusão silenciosa.
- **Fencing token**: monotônico; conclusão com token antigo é rejeitada (`STALE_COMPLETION_REJECTED`).
- Crash após claim → lease expira → outro worker reclama → worker antigo não “ressuscita” o efeito.
- Contenção dual → exatamente um vencedor (`SINGLE_WINNER`).

## Drain

- Transição ordenada: worker em `DRAINING` não aceita **novos** claims; ciclo em andamento pode concluir.
- Console: `POST /v1/console/runtime/workers/{workerId}/drain` com confirmação na UI.
- Authz: `DRAIN_WORKER`. Sem `allow-drain` / local-demo → **404** (sem enumeração).

## Backlog

- Leitura **somente observação** das fontes canônicas por tipo (`WorkerBacklogQueryService`).
- Status tipados (`IDLE` / `HEALTHY` / `ACCUMULATING` / `STALE` / `UNKNOWN`).
- O runtime **não** semeia trabalho artificial para “provar” fila; cenário de lab sem backlog real → inconclusivo, nunca aprovado por omissão.

## Flags

| Flag | Papel |
|------|--------|
| `spider.worker-runtime.enabled` | Master do runtime (OFF_BY_DEFAULT) |
| `spider.worker-runtime.http.enabled` | Expõe API `/v1/console/runtime/*` |
| `spider.worker-runtime.local-demo.enabled` | Demo local (profile `local-demo`); também libera drain |
| `spider.worker-runtime.allow-drain` | Permite drain via HTTP fora do local-demo (default false) |
| `spider.worker-runtime.recovery.enabled` | Recovery workers (default false) |

Demais knobs: `instance-id`, `tick-interval`, `heartbeat-interval`, `stale-after`, `default-lease-duration`, `default-execution-timeout`, `default-batch-size`, `max-concurrency`, `drain-timeout`, `max-attempts`.

## API

Base: `/v1/console/runtime` (ativa só com console HTTP + worker-runtime + worker-runtime.http).

| Método | Caminho | Ação authz |
|--------|---------|------------|
| `GET` | `/` | `VIEW_WORKER_RUNTIME` — snapshot |
| `GET` | `/workers` | `VIEW_WORKER_RUNTIME` |
| `GET` | `/workers/{workerId}` | `VIEW_WORKER_RUNTIME` |
| `GET` | `/schedules` | `VIEW_WORKER_RUNTIME` |
| `GET` | `/backlogs` | `VIEW_WORKER_RUNTIME` |
| `POST` | `/workers/{workerId}/drain` | `DRAIN_WORKER` → **202** se aceito |

DenyAll / flags off / id inexistente / drain não permitido → **404** (sem enumeração).

## Dimensões de saúde (017 + 019)

Com o runtime ligado, o Cockpit Operacional passa a incluir (quando disponível):

- `WORKER_RUNTIME`
- `SCHEDULING`
- `BACKLOG`
- `LEASE_SAFETY`

Com o runtime desligado, a leitura 017 permanece inalterada (nenhuma dimensão extra).

## Failure Lab — cenários de workers

Categoria `WORKER_RUNTIME` (boundary do cenário: **MOCK_ONLY**; harness simula posse/fencing sem infra produtiva). Runbook: `runbook:failure-lab:worker-runtime@1.0`.

| Código | O que demonstra |
|--------|-----------------|
| `WORKER_CRASH_AFTER_CLAIM` | Crash após claim → lease expira → reclaim → conclusão stale rejeitada |
| `WORKER_DUAL_CONTENTION` | Dois workers; um único vencedor |
| `WORKER_GRACEFUL_DRAIN` | Drain: `DRAINING` + sem novos claims |
| `WORKER_BACKLOG_ACCUMULATION` | Observa backlog canônico; inconclusivo se não houver fila real |
| `WORKER_RESTART_RECOVERY` | Estado do schedule sobrevive à recarga |

Predicado tipado: `WORKER_FACT_EQUALS` (fatos emitidos pelo harness, sem expressão livre).

## Relação com processors (sem duplicação semântica)

| Camada | Responsabilidade |
|--------|------------------|
| **Processor / serviço canônico** | Efeito de domínio: aplicar sinal, expirar wait, entregar callback, reconciliar, recovery, manutenção de envelope |
| **Worker handler** | Adaptador fino: chama o processor com `workerId` / batch / clock e mapeia resultado → `ScheduleOutcome` |
| **Worker runtime** | Catálogo, schedule durável, claim/lease/fencing, heartbeat, drain, backlog read-model, telemetria e console |

O runtime **não** reimplementa regras de execução, não decide rotas e não altera a máquina de estados da Engine. Processors existentes permanecem a única fonte de semântica de negócio/técnica do efeito.

## Boundary

- **SIMULATED_INFRASTRUCTURE**: schedules, leases e fencing são reais no store do Spider (JPA/H2 ou memória conforme modo), não em Kafka/K8s/cluster produtivo.
- **MOCK_ONLY** nas integrações: sem IdP/KMS/legado real; Failure Lab de workers não injeta falha em infra externa.
- Banner permanente na UI: demonstração · runtime simulado · sem legados reais.
- OFF_BY_DEFAULT: com flags off, nenhum bean de coordenação/HTTP do runtime é criado.

## Console

Nav **Runtime de Workers** (`WorkerRuntime.jsx`): resumo (status, stale, leases vencidos), tabela de workers, schedules, backlogs, drain com confirmação. Banner de boundary obrigatório.

## Screenshots

| Arquivo | Conteúdo |
|---------|----------|
| `019-worker-runtime-overview-desktop.png` | Visão geral do runtime |
| `019-worker-runtime-backlog-desktop.png` | Backlogs por tipo |
| `019-worker-runtime-draining-desktop.png` | Worker em drenagem |
| `019-worker-runtime-stale-recovery-desktop.png` | Stale / recuperação de lease |
| `019-worker-runtime-mobile.png` | Viewport mobile |

Geração: `frontend/scripts/capture-worker-runtime-screenshots.mjs` (com local-demo e flags do worker-runtime ligadas).

## Abertura do Grupo B

Com CAP-019 **VERIFIED**, o `GROUP_B_RUNTIME_OPERATIONS` inicia **1/3**. Sucessor **SPIDER-PROMPT-020** (capacidade / backpressure) está **VERIFIED** no baseline 0.20.0 (Grupo B **2/3**).

## Referências

- ARCH-010 (workers / backlog / dimensões de saúde)
- ARCH-011 (unidades de execução / lease e fencing)
- ARCH-013 (superfície Runtime de Workers)
- ARCH-014 (linguagem de negócio: lease, fencing, drain)
- Manifesto CAP-019
- Roadmap 016–026
