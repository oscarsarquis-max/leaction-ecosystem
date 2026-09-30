# ACTIONFINANCE_REV_002_COR_002 — Encerramento das pendências da fundação

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_002_COR_002 |
| Data | 28/09/2026 |
| Prompt | PRM_002_COR_002 |
| Execução | Cursor (desenvolvedor) |
| Parecer do analista | Pendente — este relatório volta ao analista pelo proprietário |
| Autorização do proprietário | Executar somente este corretivo; sem PRM_003 |
| Gate `mvnw.cmd clean verify` | **VERDE** — Surefire 6/6; Failsafe 14/14; 0 failures, 0 errors, 0 skips; exit 0 |
| PRM_003 | Não iniciado |
| Commit / push / deploy | Não realizados |
| Spider sandbox | Preservada (`spider-postgres` no ar; volumes/processos da Spider não operados) |

## Conflito de regras (registrado, não alterado)

`.cursor/rules/ecosystem-focus.mdc` ainda descreve o foco como COR_001. O proprietário autorizou **COR_002**. A regra global do Cursor **não** foi editada. O trabalho ficou em `ActionFinance/**` e neste relatório.

## Estado git (monorepo)

| Campo | Valor |
|---|---|
| Branch | `feat/sponge-lojadepaes-145` |
| HEAD | `7177805b` |
| ActionFinance | diretório não rastreado (`?? ActionFinance/`); sem Git aninhado |
| Alterações alheias | não sobrescritas |

## Tabela D1–D5

| ID | Mudança | Evidência | Resultado | Pendência |
|---|---|---|---|---|
| D1 | Testcontainers **1.21.4** + BOM; `DockerEnvironmentDiscoverer` removido; sem pipe de máquina; Failsafe no ciclo normal | `mvnw.cmd clean verify` 28/09/2026 17:33; Testcontainers 1.21.4 conectou `npipe:////./pipe/docker_engine`; API servidor **1.55**; docker-java **3.4.2**; PG IT `postgres:17.6` | **PASSOU** | Nenhuma do gate |
| D2 | Stop sem varredura global; launchId + checkout + wrapper/server/filhos; revalidação; wrappers `run-*.ps1` | `OWNERSHIP_VERIFY_OK`; start×2 `ALREADY_RUNNING`; stop×2 `STOPPED_ALREADY`; PID inválido recusado; decoy sobreviveu | **PASSOU** | O script único `verify-start-stop.ps1` ainda corre com ocupantes residuais da porta 8091 se houver ensaio anterior; as provas pedidas foram obtidas em execuções dirigidas |
| D3 | Restore reatribui owner de schema/tabelas (incl. `flyway_schema_history`); GRANT V1; SELECT runtime; `flyway validate` 11.10.1; cleanup com separador | `BACKUP_VERIFY_OK source_version=1 source_checksum=1488219560` + validate + falha deliberada | **PASSOU** | Nenhuma |
| D4 | Vitest **4.1.11** / `@vitest/mocker` **4.1.11**; Vite 6.4.3 inalterado; sem `--force` | `npm` lint 0; test 2/2; `tsc`+build OK; `npm audit` **0 vulnerabilities** | **PASSOU** | ESLint 9.36.0 deprecated no registry (não é advisory) |
| D5 | 401 anônimo e 403 com Bearer válido em `/api/v1/payables`; evidências da **mesma** execução final copiadas antes de outros Maven | `FoundationSecurityIT` 9/9 na execução 17:33; cópia em `documents/reviews/evidence/cor-002/verify-2026-09-28T1733/` | **PASSOU** | Nenhuma |

## D1 — Testcontainers e gate Maven

Hipótese 1.21.4 confirmada nesta máquina. Descoberta efetiva: `NpipeSocketClientProviderStrategy` via `~/.testcontainers.properties` (arquivo de usuário **não** editado). Cliente negociou com Docker Desktop **29.7.2**, API **1.55**. O HTTP 400 de 1.21.3 não se repetiu. Ryuk 0.12.0 subiu. CLI Docker também responde (`desktop-linux` → `npipe:////./pipe/dockerDesktopLinuxEngine`).

Não foi aberto Docker TCP, não se usou H2, não se desligou Ryuk, não se editou `~/.testcontainers.properties`, não houve skipITs/skipTests.

Execução intermediária 17:17 (copiada em `evidence/cor-002/verify-2026-09-28T1717/`): ITs rodaram; 1 failure em `FoundationProfileIT` porque `SPRING_PROFILES_ACTIVE=local-demo` vazou do ambiente do operador. Surefire/Failsafe agora esvaziam essa variável e `ACTIONFINANCE_DEMO_AUTH_ENABLED` no processo de teste. **Não misturar** o resumo 17:17 com o gate 17:33.

### Contagem do gate final (17:33, exit 0)

| Suíte | Testes | Fail | Error | Skip |
|---|---|---|---|---|
| Surefire `DemoAuthStartupValidatorTest` | 4 | 0 | 0 | 0 |
| Surefire `ArchitectureGuardTest` | 2 | 0 | 0 | 0 |
| **Surefire total** | **6** | **0** | **0** | **0** |
| Failsafe `FoundationHealthIT` | 2 | 0 | 0 | 0 |
| Failsafe `FoundationPersistenceIT` | 1 | 0 | 0 | 0 |
| Failsafe `FoundationProfileIT` | 2 | 0 | 0 | 0 |
| Failsafe `FoundationSecurityIT` | 9 | 0 | 0 | 0 |
| **Failsafe total** | **14** | **0** | **0** | **0** |

Há WARN Hikari “connection has been closed” no arranque do HealthIT; os dois testes da classe passaram. Não foi tratado como skip.

## D2 — Parada só com propriedade de lançamento

Removida a varredura `Win32_Process` + `Stop-Process` por texto. `Stop-ActionFinanceOwnedTree` só encerra alvos **gravados** (wrapper, server, filhos) após revalidar PID + nome + `creationUtc` (ISO como UTC no Windows PowerShell 5.1) e vínculo com o checkout. PID reutilizado / metadado com nome ou horário errado → `REFUSED_STOP`. Wrapper ausente não apaga filhos ainda confirmados.

Provas com processos descartáveis do próprio ensaio (`verify-ownership.ps1`): árvore completa; wrapper sai e o filho ainda é parado pelo registro; decoy com as palavras `actionfinance java npm vite` sobrevive; metadado com `processName=java` ou `creationUtc` velho é recusado.

Start×2 e stop×2 no stack real: `STARTED` / `ALREADY_RUNNING` / `stopped … recorded-targets-validated` / `STOPPED_ALREADY`; volume `actionfinance_pgdata_17` preservado. Porta ocupada por processo não adotável continua recusada, sem kill por porta.

## D3 — Restauração

Dump `--no-owner --no-acl`. Papéis recriados. `ALTER SCHEMA` + laço explícito de `ALTER TABLE/SEQUENCE OWNER` para objetos presentes, inclusive `flyway_schema_history`. Política V1: USAGE, REVOKE CREATE do runtime, GRANT SELECT no histórico. Runtime SELECT do checksum; sem SUPERUSER/CREATEDB/CREATEROLE; sem CREATE no schema; sem propriedade de objetos. Probe DDL do migrator em transação revertida. `flyway/flyway:11.10.1 validate` no namespace do container descartável. Falha SQL deliberada sem `BACKUP_VERIFY_OK`. Cleanup só de labels desta execução; remoção de diretório exige caminho absoluto filho de `.local\verify-runs\<runId>` (separador, não só prefixo).

## D4 — Frontend

Vitest 3.2.7 → **4.1.11** (GHSA-82fw-gwwq-j7x9). Peer: Node `>=24` do projeto; Vitest 4.1.11 declara `^20 \|\| ^22 \|\| >=24` e Vite `^6 \|\| ^7 \|\| ^8`. Vite permaneceu **6.4.3**. Sem override, sem `--legacy-peer-deps`. `npm audit`: 0. Bundle sem Bearer/token de demo (o teste Vitest cobre as chamadas `fetch`). Capturas visuais do COR_001 reutilizadas; nenhuma mudança de UI/Vite de desenvolvimento.

`npm ci` falhou uma vez com EPERM em `esbuild.exe` (arquivo em uso). `npm install` + lint/test/build/audit concluíram. Residual de diretório temporário `@esbuild/.win32-x64-*` na limpeza do npm, sem falha de audit.

## D5 — Deny-by-default

`GET /api/v1/payables` sem token → 401; com Bearer operator demo → 403. Nenhuma rota de contas a pagar criada. Demais ITs de permissão, isolamento de empresa, headers de privilégio e perfil sem `local-demo` passaram na execução 17:33.

## Versões efetivas

Java 21.0.12 · Spring Boot 3.4.2 · Flyway 11.10.1 · Hibernate 6.6.5.Final · Testcontainers 1.21.4 · docker-java 3.4.2 · PostgreSQL **17.6** · checksum V1 **1488219560** · Node 24 / npm 11 · React 19.2.8 · Vite 6.4.3 · Vitest 4.1.11 · API `127.0.0.1:8091` · UI `127.0.0.1:5179` · PG `127.0.0.1:5439`

## Processos / containers / volumes (após a entrega)

| Recurso | Estado |
|---|---|
| `actionfinance-postgres-17` | Up (healthy); `127.0.0.1:5439` |
| volume `actionfinance_actionfinance_pgdata_17` | Preservado |
| volume `actionfinance_actionfinance_pgdata` (PG18) | Preservado |
| API/UI locais | Parados após as provas de start/stop |
| `spider-postgres` | Presente; não operado |

## Arquivos principais alterados

- `backend/pom.xml` — Testcontainers 1.21.4 + BOM; isolamento de env no Surefire/Failsafe
- remoção de `DockerEnvironmentDiscoverer.java`
- `scripts/dev/_lib.ps1`, `start-local.ps1`, `stop-local.ps1`, `run-backend.ps1`, `run-frontend.ps1`
- `scripts/dev/verify-backup.ps1`, `verify-ownership.ps1`, `verify-start-stop.ps1`
- `frontend/package.json`, `package-lock.json` — Vitest 4.1.11
- `backend/src/test/java/.../FoundationProfileIT.java` — isolamento de perfil
- documentos deste corretivo e evidências Maven

## O que não foi feito

PRM_003, domínio financeiro, ledger, pagamentos, UX operacional, integração Spider, commit, push, deploy, DNS, alteração de Hub/Panne/Inove, edição de regras globais do Cursor ou de `~/.testcontainers.properties`.

## Distinção de papéis

Este documento é **execução do Cursor**. Não é parecer do analista nem autorização de produção do proprietário. PRM_003 não foi emitido nem executado.
