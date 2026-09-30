# ACTIONFINANCE_REV_002_COR_001 — Fechamento da fundação local

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_002_COR_001 |
| Data | 28/09/2026 |
| Prompt | PRM_002_COR_001 |
| Gate `mvnw verify` | **NÃO VERDE** — ITs executadas e falharam; zero skips |
| PRM_003 | Não iniciado |
| Commit / push / deploy | Não realizados |
| Spider sandbox | Preservada no ar |

## Tabela C1–C7

| ID | Arquivos | Prova | Resultado |
|---|---|---|---|
| C1 | `backend/pom.xml` (Failsafe `integration-test`+`verify`, Testcontainers 1.21.3); remoção do npipe versionado; `DockerEnvironmentDiscoverer`; ITs sem `disabledWithoutDocker` | `mvnw verify`: Surefire 6/6; Failsafe 4 classes, 0 skip, 4 errors | **PENDENTE** |
| C2 | `compose.yaml` `postgres:17.6` + volume `actionfinance_pgdata_17`; Flyway **11.10.1**; mesma tag nos ITs | Log local: `PostgreSQL 17.6`, sem warning “support has not been tested”. Flyway 11.10.1 em PG 18.6 ainda avisava suporte até 17 — por isso o volume 18 não foi reutilizado | **PASSOU** |
| C3 | `scripts/dev/verify-backup.ps1` | `BACKUP_VERIFY_OK source_checksum=1488219560 restored_checksum=1488219560` + falha deliberada sem sucesso falso | **PASSOU** |
| C4 | `start-local.ps1`, `stop-local.ps1`, `_lib.ps1` | Start×2 = `ALREADY_RUNNING`. Stop×2 = `STOPPED_ALREADY` + volume 17 preservado. Ownership por command line ActionFinance, não por nome `java`/`node` | **PASSOU** com ressalva de wrappers |
| C5 | `SecurityConfiguration.java` `denyAll` + permissões explícitas | `GET /api/v1/payables` sem token → 401. ITs de segurança não rodaram (C1) | **PASSOU** no host; ITs pendentes |
| C6 | `DemoAuthStartupValidator` recusa `0.0.0.0` / `::` / não loopback e override `SERVER_ADDRESS` | 4 testes unitários verdes | **PASSOU** |
| C7 | ESLint 9, Vite 6.4.3, Vitest 3.2.7, Playwright | `lint` 0 erros; `test` 2/2; `build` OK; bundle sem Bearer/token; captura 360/1280 sem overflow X; Tab no botão | **PASSOU** com residual npm |

## C1 — causa observada (não é “Docker ausente”)

CLI Docker 29.7.2 funciona (`desktop-linux` → `npipe:////./pipe/dockerDesktopLinuxEngine`). `~/.testcontainers.properties` (não alterado) força `NpipeSocketClientProviderStrategy`.

Tentativas seguras: Testcontainers 1.21.3; descoberta do contexto via CLI; `TESTCONTAINERS_DOCKER_CLIENT_STRATEGY=EnvironmentAndSystemPropertyClientProviderStrategy`; `DOCKER_HOST` do contexto; `DOCKER_API_VERSION=1.44`; pipe `docker_cli` (404). Em todos os casos o cliente Java recebe **HTTP 400** em `/info` com corpo stub e label `com.docker.desktop.address=npipe://\\.\pipe\docker_cli`.

Não foi aberto TCP sem autenticação, não se desligou a segurança do Docker, não se desabilitou Ryuk, não se editou a config global, não se usou H2.

Contagem Failsafe: **4 errors, 0 failures, 0 skipped**. O gate falha de propósito.

Caminho unit-only (não é aceite): `mvnw -DskipITs test` ou perfil `unit-only`.

## C2 — transição PostgreSQL

| Recurso | Estado |
|---|---|
| `actionfinance-postgres` / volume `actionfinance_actionfinance_pgdata` (PG 18.6) | **Preservado** (volume intacto; container antigo saiu no recreate do Compose ao mudar o nome) |
| `actionfinance-postgres-17` / `actionfinance_actionfinance_pgdata_17` | Ativo; imagem `postgres:17.6`; porta `127.0.0.1:5439` |
| Rollback | `docker compose stop`; voltar compose à 18.6 + volume antigo; **não** apontar 17 ao volume 18 |

Documentação Flyway consultada (25/09/2026) lista PG 18 na linha atual do produto; o artefato **11.10.1** usado com Boot 3.4.2 ainda declara suporte testado até 17.

## C3

Dump `--no-owner --no-acl`, papéis reaplicados, checksum idêntico, owner `actionfinance_migrator`, runtime sem SUPERUSER/CREATEDB/CREATEROLE, `CREATE TABLE` negado, falha deliberada com exit ≠ 0. Sem dados financeiros.

A prova histórica do REV_002 (GRANT falho + `BACKUP_VERIFY_OK`) permanece **parcial**. Esta execução substitui o aceite de restore.

## C7 — auditoria npm

Corrigido de forma compatível (sem `--force`):

| Pacote | Antes | Depois | Advisories |
|---|---|---|---|
| vite | 6.3.5 (high agregado) | **6.4.3** | GHSA-g4jq-h2w9-997c, GHSA-jqfw-vq24-v9c3, GHSA-93m4-6634-74q7, GHSA-4w7w-66w2-5vf9, GHSA-p9ff-h696-f583, GHSA-v6wh-96g9-6wx3, GHSA-fx2h-pf6j-xcff |
| vitest | 3.2.4 (critical UI) | **3.2.7** | GHSA-5xrq-8626-4rwp fechado |

Residual **não autoaceito**: `@vitest/mocker` / vitest 3.2.7 — GHSA-82fw-gwwq-j7x9 (moderate, path traversal no mocker). Correção via `npm audit fix --force` instala vitest 5 (breaking). Uso atual: `vitest run`, sem UI server. Devolvido ao analista.

ESLint 9.36.0 está deprecated no registry; não é advisory de segurança.

## Screenshots

`documents/reviews/screenshots/cor-001/` — desktop 1280, mobile 360, falha de API e reconsulta. Captura Playwright: overflowX=false; foco Tab em “Verificar novamente”.

## Versões e portas efetivas

Java 21.0.12 · Boot 3.4.2 · Flyway 11.10.1 · Hibernate 6.6.5.Final · Testcontainers 1.21.3 · Postgres **17.6** · Node 24 / npm 11 · React 19.2.8 · Vite 6.4.3 · Vitest 3.2.7 · API `127.0.0.1:8091` · UI `127.0.0.1:5179` · PG `127.0.0.1:5439`

## O que não foi feito

PRM_003, domínio financeiro, UX operacional, integração Spider, commit, push, deploy, alteração de Hub/Panne/Inove/DNS. Spider não foi parada.

## Pendências para o analista

1. C1 / `mvnw verify` — handshake docker-java × Docker Desktop 29.
2. Residual GHSA-82fw-gwwq-j7x9 vs upgrade major do Vitest.
3. Container legado `actionfinance-postgres` não existe mais; o **volume PG18** permanece para rollback.
