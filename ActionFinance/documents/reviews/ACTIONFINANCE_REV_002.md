# ACTIONFINANCE_REV_002 — Provas da fundação técnica local

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_002 |
| Versão | 0.1 |
| Data | 25/09/2026 |
| Prompt | PRM_002 v0.2 |
| Parecer do analista (PRM_001) | Aprovado; R1–R4 fechados; `REV_001_ENCERRAMENTO` |
| Autorização de execução | Proprietário entregou o PRM_002 com instrução para executar |
| Aprovação de produção / piloto / decisões futuras | **Não concedida** |

## Acertos R1–R4

Preservados. Não reexecutado o PRM_001. Fonte: `documents/reviews/ACTIONFINANCE_REV_001_ENCERRAMENTO.md`.

## Comandos e resultados (sem secrets)

| Comando | Resultado |
|---|---|
| `java -version` | 21.0.12 |
| `node -v` / `npm -v` | 24.14.0 / 11.9.0 |
| `backend/mvnw.cmd -q -DskipITs test` | exit 0 — ArchUnit + `DemoAuthStartupValidatorTest` |
| `backend/mvnw.cmd failsafe:integration-test` | exit 0 **por skip** (`disabledWithoutDocker=true`). **Não é gate verde.** Testcontainers 1.20.4: `NpipeSocketClientProviderStrategy` / `docker_cli` HTTP 400 |
| `frontend` `npm test` | 2/2 passed (Vitest 3.2.4) |
| `frontend` `npm run build` | tsc + Vite OK; bundle sem token/Bearer |
| `scripts/dev/setup-local.ps1` | `SETUP_OK` `actionfinance-postgres` `127.0.0.1:5439` |
| Flyway na subida | V1 aplicada; revalidação “up to date. No migration necessary.” Checksum `1488219560` |
| `docker restart actionfinance-postgres` | healthy; mesmo checksum |
| `scripts/dev/verify-backup.ps1` | `BACKUP_VERIFY_OK flyway_rows=1`; destino `55439` removido. `GRANT` a papéis bootstrap falhou no descartável (papéis ausentes). Sem dados financeiros |

## Endpoints exercitados no host

| Pedido | Resultado |
|---|---|
| `GET /api/v1/system/info` | 200 `stage=FOUNDATION`, `financialOperationsAvailable=false`, `spiderIntegrationStatus=NOT_IMPLEMENTED` |
| `GET /api/v1/access/me` sem token / token inválido | 401 JSON `UNAUTHORIZED` |
| `GET /api/v1/access/me` viewer A + headers de privilégio | 200 `actorId` viewer A (sem escalada) |
| `GET /api/v1/access/context?companyId=` B com viewer A | 403 mensagem uniforme |
| contexto A com viewer A | 200 rótulo técnico |
| `companyId=not-a-uuid` | 400 |
| `GET /actuator/health/liveness` | 200 `UP` (também com banco próprio parado) |
| `GET /actuator/health/readiness` banco próprio no ar | 200 `UP` |
| readiness com **só** `actionfinance-postgres` parado | 503 `DOWN` em timeout limitado; liveness 200 |
| `GET /actuator/env` e `/actuator/mappings` autenticado | 404 JSON `NOT_FOUND` (não expostos) |
| desconhecido sem token | 401 |
| `Origin: https://evil.example` | 403, sem `Access-Control-Allow-Origin` |
| `Origin: http://127.0.0.1:5179` | 200 + ACAO explícito |
| UI `http://127.0.0.1:5179/` | 200 HTML ActionFinance; proxy `/api/v1/system/info` 200 real |

Papéis: `actionfinance_runtime` sem SUPERUSER/CREATEDB/CREATEROLE; `CREATE TABLE` no schema → `permission denied`.

## Matriz de testes do prompt §11

| # | Prova | Estado |
|---|---|---|
| 1 | Maven Java 21; frontend test/build | **PASSOU** |
| 2 | ArchUnit domínio / vizinhos | **PASSOU** (classe existente `FoundationStage`) |
| 3 | Testcontainers migrations / permissões / checksum | **BLOQUEADO** — engine Desktop não aceita o cliente npipe do Testcontainers 1.20.4. Equivalente operacional via compose+CLI: **PASSOU** |
| 4 | Security 401/200/403/400/sem escalada | **PASSOU** (HTTP real + testes unitários). ITs Spring+TC: **BLOQUEADO** |
| 5 | Profile / CORS / Actuator | **PASSOU** no host. `DemoAuthStartupValidatorTest` cobre flag incompleta. ITs: **BLOQUEADO** |
| 6 | Health próprio up/down + liveness | **PASSOU** no container próprio (nenhum banco vizinho parado) |
| 7 | Frontend resposta/falha/reconsulta/teclado; bundle limpo | **PASSOU** no Vitest + grep do `dist`. Layout 360 px: CSS presente; **navegador real não disponível nesta sessão** |
| 8 | Restart + backup descartável | **PASSOU** (histórico Flyway; sem dados financeiros) |

## Riscos reais

1. Flyway 10.20.1 declara suporte oficial até PostgreSQL 17 e emite warning em 18.6. V1 aplicou; combinação não é “testada pelo Flyway”.
2. Testcontainers nesta máquina não é evidência reproduzível até o cliente Docker/npipe ser corrigido.
3. Identidade demo é só instrumento de teste. Tokens em `.local/` — se vazarem, trocar com novo setup (o setup não sobrescreve arquivos existentes).
4. CSRF desabilitado só na cadeia Bearer; cookie futuro exige revisão.
5. Backup descartável não recria papéis bootstrap; prova limitada ao `flyway_schema_history`.
6. `.cursor/` está no `.gitignore` da raiz; a atualização de foco é local, não versionada pelo Git.

## Fora de ActionFinance

Somente `.cursor/rules/ecosystem-focus.mdc`: foco PRM_002. Nenhum produto vizinho alterado ou parado para impor foco.

## Não implementado (proposital)

Payable, ledger, inbox/outbox, clientes Spider/Panne/Hub, dashboards, UX de gestão, commit, push, deploy.

## Parecer posterior do analista

**DEVOLVIDO PARA CORREÇÃO; aceite pendente.** Ver [parecer completo](ACTIONFINANCE_REV_002_PARECER_ANALISTA.md) e PRM_002_COR_001. A restauração acima comprova apenas parte do histórico; erros de GRANT impedem classificá-la como restauração plenamente aprovada. Resultados históricos preservados para rastreabilidade.

Corretivo executado em 28/09/2026: [ACTIONFINANCE_REV_002_COR_001.md](ACTIONFINANCE_REV_002_COR_001.md). O restore desta data é verificável; o `mvnw verify` **não** está verde (ITs sem skip, handshake Testcontainers/Desktop 29).
