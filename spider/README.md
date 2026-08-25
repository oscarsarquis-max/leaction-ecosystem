# Spider — Orquestrador de Contexto

Motor de orquestração entre canais/produtos e sistemas legados internos.

## Stack

- **Backend:** Java 21 · Spring Boot 3.4 · **WebFlux** · JPA (`tb_product_routes`, `tb_audit_trace`) · WebClient · Resilience4j · jjwt · OpenAPI
- **Frontend:** React · Vite (`:5180`) — não usar `:5175` (Phanton)
- **DB técnico:** PostgreSQL 16 (Docker) — rotas, idempotência, audit/trace
- **Mocks:** cadastro `:8091` · crédito `:8092`

## Subir banco

```powershell
cd C:\Projetos\spider
docker compose up -d
```

- Host: `localhost:5432`
- DB / user / pass: `spider_orchestrator` / `spider_user` / `spider_password`
- Schema: `spider.*` (via `database/init.sql`)

## Compilar a base (backend)

Pré-requisitos: JDK 21 + Maven 3.9+.

```powershell
cd C:\Projetos\spider
.\scripts\compile-base.ps1
# ou:
cd backend
mvn -DskipTests package
```

## Rodar a stack local

```powershell
# terminais separados
cd services\mock-sistema-cadastro; npm install; npm start
cd services\mock-sistema-credito;  npm install; npm start
cd backend;  mvn spring-boot:run
cd frontend; npm install; npm run dev
```

| Serviço | URL |
|---------|-----|
| Painel | http://127.0.0.1:5180 |
| API / Swagger | http://127.0.0.1:8080/swagger-ui.html |
| Health | http://127.0.0.1:8080/actuator/health |

## Estrutura

```
spider/
├── .cursorrules
├── docker-compose.yml
├── database/init.sql
├── database/migrations/
├── scripts/
├── services/mock-sistema-*
├── backend/   # br.com.banco.spider
└── frontend/
```

Diretrizes para a IA: ver `.cursorrules`.

## Documentação

- Arquitetura normativa: `docs/architecture/SPIDER-ARCH-*.md`
- **Console operacional (ARCH-013):** `docs/architecture/SPIDER-ARCH-013-console-operacional-e-visualizacao.md`
- **Roadmap oficial 016–026:** `docs/roadmap/SPIDER-ROADMAP-IMPLEMENTACAO-016-026.md`
- Console / Prompt 015: `docs/technical/SPIDER-PROMPT-015-operational-console.md`
- Guia de apresentação Mock: `docs/presentation/SPIDER-PRESENTATION-GUIDE.md`
- Fundação canônica (PROMPT-001): `docs/technical/SPIDER-PROMPT-001-canonical-foundation.md`
- Engine canônica mínima (PROMPT-002): `docs/technical/SPIDER-PROMPT-002-canonical-engine.md`
- Persistência e idempotência (PROMPT-003): `docs/technical/SPIDER-PROMPT-003-persistence-idempotency.md`
- Multi-step e retry (PROMPT-004): `docs/technical/SPIDER-PROMPT-004-multistep-retry.md`
- Waiting external e retomada (PROMPT-005): `docs/technical/SPIDER-PROMPT-005-waiting-external-resume.md`
- Perfil HTTP canônico (PROMPT-006): `docs/technical/SPIDER-PROMPT-006-canonical-http-profile.md`
- Callback Outbox (PROMPT-007): `docs/technical/SPIDER-PROMPT-007-callback-outbox.md`
- Telemetria / Operational Events (PROMPT-016): `docs/technical/SPIDER-PROMPT-016-operational-events.md`
- Saúde operacional / SLIs e SLOs provisórios (PROMPT-017): `docs/technical/SPIDER-PROMPT-017-operational-health-sli-slo.md`
- Failure Lab / jornadas operacionais (PROMPT-018): `docs/technical/SPIDER-PROMPT-018-failure-lab-operational-journeys.md`

## Console operacional (PROMPT-015)

Frontend ativo: `frontend/src/console/*` (ConsoleShell). Flags (default **false**):

```properties
spider.console.enabled=false
spider.console.http.enabled=false
spider.console.local-demo.enabled=false
spider.telemetry.enabled=false
spider.operational-health.enabled=false
spider.failure-lab.enabled=false
spider.failure-lab.http.enabled=false
spider.failure-lab.local-demo.enabled=false
```

Local-demo exige profile Spring `local-demo` **e** flag. O Cockpit Operacional exige também `spider.telemetry.enabled=true`. O Failure Lab exige `spider.failure-lab.enabled=true` (e `http`/`local-demo` conforme a superfície). Endpoints: `GET /v1/console/executions`, `/{id}`, `/{id}/events`, `/implementation`, `/presentation/readiness`, `/operational-health`, `/operational-health/definitions`, `/failure-lab/scenarios`, `POST /failure-lab/runs`, `GET /failure-lab/runs/{id}` e `/failure-lab/runs/{id}/evidence`.

Apresentação:

```powershell
.\scripts\validate-presentation.ps1
.\scripts\start-presentation.ps1
```

### Matriz decisão → componente → endpoint → teste

| Decisão | Componente | Endpoint | Teste |
|--------|------------|----------|-------|
| Read model seguro | `OperationalConsoleQueryService` | `GET /v1/console/executions*` | `OperationalConsoleE2EReadModelTest` |
| Operational Events | `SafeOperationalEventPublisher` / store | `GET /v1/console/executions/{id}/events` | `OperationalEventPublisherTest` + E2E |
| Saúde, SLIs/SLOs provisórios | `OperationalHealthAggregator` / `ProvisionalSliCalculator` / `OperationalCockpit` | `GET /v1/console/operational-health*` | `OperationalHealthAggregatorTest` + `ProvisionalSliCalculatorTest` + E2E + `ConsoleShell.test.jsx` |
| Failure Lab | `FailureLabOrchestrator` / `FailureLab` | `/v1/console/failure-lab/*` | `FailureLabEndpointE2ETest` + `FailureLab.test.jsx` |
| DenyAll console | `OperationalConsoleSecurityDefaultsConfig` | todos `/v1/console/*` | `DenyAllConsoleAuthBeansPresentTest` |
| Manifesto capabilities | `ImplementationManifestLoader` | `GET /v1/console/implementation` | `ImplementationManifestLoaderTest` |
| Presentation readiness | `PresentationReadinessUseCase` | `GET /v1/console/presentation/readiness` | E2E readiness |
| UI cockpit/apresentação | `ImplementationCockpit` / `PresentationMode` | consome API (não JSON local) | `ConsoleShell.test.jsx` |
| Legado intacto | orchestrate controller | `POST /v1/products/orchestrate` | `OrchestrateEndpointRegressionTest` |
