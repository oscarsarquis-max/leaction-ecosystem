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

### 2.1 Home operacional (PROMPT-020A)

A rota inicial do console é a **Home operacional**, não “Observação do Data Plane”. A jornada do operador é:

```text
USER → HOME OPERACIONAL → EXECUÇÕES → DETALHE / TIMELINE / OPERAÇÃO
```

A Home reutiliza o submit canônico existente (`POST /v1/canonical/executions`, cenário `RETRY_THEN_SUCCESS`) e lista últimas execuções via `GET /v1/canonical/executions`. A navegação é **agrupada por finalidade** (PROMPT-020B): Home; Execuções (lista / detalhe / visão geral); Operação (Cockpit, Runtime de Workers, Capacidade); Testes & demonstração (Laboratório Mock, Failure Lab); Plataforma (Implementação, Apresentação).

#### 2.1.1 Compreensão contextual antes da execução (CTX-001A)

A Home preserva as superfícies 020A/020B e acrescenta uma etapa explícita de compreensão. Clicar em
um Business Intent Card abre **SPIDER ENTENDEU**; não submete execução. O painel projeta o Intent
Contract, a decisão do Context Guard e a rota determinística. Somente uma confirmação separada em
**Executar** atravessa o ingress canônico.

```text
OBJETIVO → INTENT → POLICY → ROTA → EXECUTAR → JORNADA
```

A experiência contextual separa compreensão de execução. Business Cards e, futuramente, linguagem
natural convergem para o mesmo Intent Contract antes da entrada no Data Plane. O campo de linguagem
natural permanece desabilitado e identificado como `IA — próxima etapa`.

### 2.2 Jornada visual da execução (PROMPT-020B)

A interface do Spider projeta visualmente o comportamento real da execução e não simula etapas inexistentes.

```text
ENGINE / DATA PLANE
       ↓
Operational Events / State
       ↓
Read Model (detail + timeline + events)
       ↓
Console (projeção amigável)
```

A **Jornada da execução** é uma projeção no frontend (`projectExecutionJourney`) de summary, timeline persistida, steps/attempts, wait/callback e Operational Events (CAP-016). Retry, wait, callback, signal, capacity e worker só aparecem com evidência. Etapas não percorridas, quando listadas na conclusão ainda em curso, ficam `NOT_REACHED`. Sem `sleep`, sem WebSocket/SSE novo: polling já existente do detalhe, cancelado no unmount e em estado terminal. A timeline técnica permanece no detalhe.

Uma execução disparada pela Home torna-se automaticamente a execução ativa e sua jornada real é projetada no próprio ponto de entrada do produto. O POST canônico devolve `execution.executionId` (ExecutionSummary aninhado); o console extrai esse identificador, seleciona a execução e inicia o acompanhamento sem exigir clique em Execuções/Detalhe. O JSON bruto da resposta HTTP não é o feedback principal.

Cada etapa da Jornada da Execução é uma superfície explicável. O operador pode selecionar uma etapa e compreender o que ocorreu, quais evidências técnicas existem e qual foi a continuidade da execução. Em desktop, a timeline ocupa a área principal e o painel contextual fica à direita; em tablet/mobile, as áreas são empilhadas. A seleção automática acompanha a etapa ativa enquanto não houver escolha manual; uma escolha manual permanece estável durante as atualizações da mesma execução.

Quando a execução nasce do Context Plane, a mesma Jornada divide visualmente **CONTEXTO** (objetivo,
intent, policy e rota) de **DATA PLANE** (ingress, contrato canônico, Engine, interações e outcome).
As etapas contextuais usam o mesmo painel explicativo e somente fatos do read model.

O painel usa somente campos seguros do read model: summary, route/correlation redigida, steps/attempts, timeline, wait/callback e Operational Events correlacionáveis. Campos não existentes não são inferidos. Por exemplo, o adapter in-process do cenário `RETRY_THEN_SUCCESS` expõe `safeErrorCode=TRANSIENT`, disposition e duração, mas não um status HTTP; portanto a UI não inventa `HTTP 500`. Metadata arbitrária, payloads, headers, tokens e credenciais não são renderizados.

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

Ingress canônico (`CanonicalIngressAuthenticationPort`) é **DenyAll independente** do console. O 401 em `GET/POST /v1/canonical/executions` no default é intencional. Em `local-demo` + `spider.console.local-demo.enabled=true`, a credencial allowlist `X-Spider-Credential-Ref: local-demo-console` autentica o originador Mock; credencial ausente ou estranha permanece 401. Não há `permitAll`.

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

Checks: manifesto válido, console API, submit/status canônicos, persistência, bootstrap Mock, bundle, cenários, coerência integrity/DP Mock, nenhum Adapter real, versões compatíveis (`productVersion` do manifesto, não hardcoded). `boundary=MOCK_ONLY`. Home operacional (020A) lê este endpoint para Presentation: READY.

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
