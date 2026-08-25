# SPIDER-ARCH-013 — Console Operacional e Visualização

| Campo | Valor |
|-------|--------|
| Identificador | SPIDER-ARCH-013 |
| Título | Console Operacional e Visualização |
| Predecessor | SPIDER-ARCH-010 (sinais/operação), SPIDER-ARCH-012 (qualidade/testes) |
| Implementação | SPIDER-PROMPT-015 (+ revisão cockpit/apresentação) |

## 1. Contexto e objetivos

Este documento define o **console operacional canônico** como superfície de observação do Data Plane Spider e o **cockpit de implementação** como superfície de estado do produto (capabilities/prompts), distinto do estado de uma execução.

Objetivos:

1. observar execuções canônicas persistidas (lista, detalhe, plan, timeline, wait/callback/governance);
2. expor estado versionado da implementação via manifesto;
3. habilitar Modo Apresentação Mock guiado com readiness explícito;
4. manter DenyAll, flags off-by-default e fronteira Mock/real.

> **Nota de alinhamento histórico:** o SPIDER-ARCH-012 (seção 63) antecipava um ARCH-013 de “roadmap incremental”. O identificador ARCH-013 foi reservado aqui para **console e visualização**, que incorpora o **manifesto versionado de capabilities (prompts 001–026)** como artefato de roadmap rastreável. Uma especificação futura dedicada apenas a migração física/fase final permanece decisão adiada e não contradiz este documento.

## 2. Console como consumidor read-only do Data Plane

```text
UI React → Console HTTP (opt-in) → Operational Query / Implementation Use Cases
         → Store Ports / Manifest Loader → Persistência / Classpath
```

O console **não** é fonte de verdade, **não** altera estado de execução e **não** substitui Control Plane administrativo.

## 3. Runtime execution state versus implementation state

| Dimensão | Fonte | Endpoint típico |
|----------|-------|-----------------|
| Execution state | Execution control/plan/steps/attempts/transitions/wait/callback/fixation | `GET /v1/console/executions*` |
| Implementation state | `spider-capability-manifest.json` + flags efetivas | `GET /v1/console/implementation` |
| Presentation readiness | Checks locais sobre flags/manifest/mocks | `GET /v1/console/presentation/readiness` |

## 4. Fontes persistidas da timeline

Eventos derivados apenas de registros reais: transitions, steps, attempts, waits, callback outbox (e reconciliação quando presente). Fontes: `PERSISTED` ou `DERIVED` explícito. Sem sleep/timeline inventada no frontend.

## 5. Safe projections e redaction

Projeções opt-in (`spider.console.safe-projections.enabled`). Redaction remove chaves sensíveis; envelope protegido nunca é decriptado para o console; `dataExposure=REDACTED`.

## 6. Authn / authz / no-enumeration

Portas `OperationalConsoleAuthenticationPort` / `AuthorizationPort`. Default DenyAll. Execução inexistente e não autorizada → resposta externa equivalente. Profile `local-demo` + flag explícita apenas para demo local.

Ações incluem: `LIST_EXECUTIONS`, `VIEW_EXECUTION_*`, `VIEW_SAFE_PROJECTIONS`, `VIEW_GOVERNANCE_REFERENCE`, `SUBMIT_MOCK_SCENARIO`, `VIEW_IMPLEMENTATION_STATUS`, `VIEW_PRESENTATION_READINESS`, `VIEW_WORKER_RUNTIME`, `DRAIN_WORKER`, `VIEW_CAPACITY`.

## 7. Manifesto de capabilities

Classpath: `implementation/spider-capability-manifest.json` + schema. Status: PLANNED | IN_PROGRESS | IMPLEMENTED | VERIFIED | BLOCKED | DEPRECATED. Runtime: OFF_BY_DEFAULT | LOCAL_DEMO_ONLY | TEST_ONLY | RUNTIME_OPT_IN | RUNTIME_DEFAULT | NOT_IMPLEMENTED. Integração: MOCK_ONLY … PRODUCTION (nunca PRODUCTION nesta jornada).

Roadmap oficial 015–026: `docs/roadmap/SPIDER-ROADMAP-IMPLEMENTACAO-016-026.md`  
Contrato anti-drift: `implementation/spider-roadmap-015-026-contract.json`

Grupos oficiais da jornada: A Visibilidade (015–018), B Runtime (019–021), C Plataforma (022–024), D Integração real (025–026). `currentGroup` = `GROUP_B_RUNTIME_OPERATIONS` (Grupo B **2/3** — CAP-019 e CAP-020 VERIFIED; Grupo A **4/4**). `currentPrompt` = `SPIDER-PROMPT-020`.

O detalhe da execução também consome Operational Events (PROMPT-016) via `GET /v1/console/executions/{id}/events` — fatos de telemetria distintos da timeline projetada do estado persistido. Telemetria é opt-in (`spider.telemetry.enabled`) e fail-open.

### Cockpit Operacional (PROMPT-017)

Superfície distinta do Cockpit de Implementação. Consome `GET /v1/console/operational-health` com banner permanente `MOCK_ONLY` / SLOs provisórios. Flag `spider.operational-health.enabled` (exige telemetria). Não emite comandos à Engine. Com worker-runtime ligado, inclui dimensões `WORKER_RUNTIME` / `SCHEDULING` / `BACKLOG` / `LEASE_SAFETY`. Com capacity ligado, inclui `CAPACITY` / `BACKPRESSURE` / `BULKHEAD_SAFETY` / `CIRCUIT_HEALTH`.

### Failure Lab (PROMPT-018)

Superfície **Failure Lab** no console (`FailureLab.jsx`): catálogo de cenários mock, execução controlada, verificação de observações, runbook provisório e evidência redigida. Flags `spider.failure-lab.enabled` (+ `http` / `local-demo`). Endpoints: `GET/POST /v1/console/failure-lab/*`. Authz: `VIEW_FAILURE_LAB`, `EXECUTE_MOCK_FAILURE_SCENARIO`, `VIEW_FAILURE_LAB_EVIDENCE`. Banner permanente MOCK_ONLY. Não decide dentro da Engine; fault injection apenas via mocks. Inclui cenários `WORKER_RUNTIME` quando o runtime 019 está habilitado e `CAPACITY_RESILIENCE` quando capacity 020 está habilitado.

### Runtime de Workers (PROMPT-019)

Superfície **Runtime de Workers** (`WorkerRuntime.jsx`): snapshot de workers, schedules, backlogs e drain com confirmação. Flags `spider.worker-runtime.enabled` (+ `http` / `local-demo`). Endpoints: `GET /v1/console/runtime`, `/workers`, `/schedules`, `/backlogs`; `POST /workers/{id}/drain`. Authz: `VIEW_WORKER_RUNTIME`, `DRAIN_WORKER`. Boundary: `SIMULATED_INFRASTRUCTURE` + integrações `MOCK_ONLY`. Não duplica processors — só posse/scheduling.

### Capacidade & Resiliência (PROMPT-020)

Superfície **Capacidade & Resiliência**: pressão, policies, bulkheads, circuits, quotas/shedding e decisões recentes. Flags `spider.capacity.enabled` (+ `http` / `local-demo` / `enforcement`). Endpoints: `GET /v1/console/capacity`, `/policies`, `/pressure`, `/bulkheads`, `/circuits`, `/decisions`. Authz: `VIEW_CAPACITY`. Boundary: `SIMULATED_INFRASTRUCTURE` + integrações `MOCK_ONLY`. Sem force-open/reset/requeue (021). Screenshots: `020-capacity-*.png`.

## 8. Modo Apresentação

Modo guiado rotulado **DEMONSTRAÇÃO MOCK**. Preflight via readiness. Jornada ao vivo usa submit canônico e detalhe/polling reais. Sem legado `/v1/products/orchestrate`.

## 9. Presentation Readiness

Checks: manifesto válido, console API, submit/status canônicos, persistência, bootstrap Mock, bundle, cenários, coerência integrity/DP Mock, nenhum Adapter real, versões compatíveis. `boundary=MOCK_ONLY`.

## 10. Mock / real boundary

Até fase final: somente Mocks. Integração real começa apenas quando capabilities deixarem `MOCK_ONLY` sob governança explícita — fora do escopo do console 015.

## 11. Polling e consistência eventual

Polling apenas em states não terminais; intervalo ≥ mínimo backend; AbortController; eventual consistency aceita entre lista e detalhe.

## 12. Invariantes

1. Console off por default.
2. Sem entity JPA no HTTP.
3. Sem JWT/token/ciphertext no caminho canônico.
4. Sem inventar timeline no UI.
5. Manifesto é fonte autoritativa do cockpit (não hardcode divergente).
6. Legado preservado mas fora da jornada canônica.

## 13. Decisões adiadas

Plataforma de métricas/OTel, SLO dashboards, admin requeue, WebSocket/SSE, IdP corporativo, migração do endpoint legado, ARCH dedicado só a migração física.

## 14. Critérios de aceite e rastreabilidade

Ver matriz em README e `docs/technical/SPIDER-PROMPT-015-operational-console.md` (revisão cockpit/apresentação). Testes: schema/manifest, endpoints DenyAll, readiness, frontend cockpit/presentation, scripts validate/start-presentation.
