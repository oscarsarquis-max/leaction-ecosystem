# ACTIONFINANCE_FND_001 — Fundação técnica local

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_FND_001 |
| Versão | 0.1 |
| Data | 25/09/2026 |
| Prompt | PRM_002 v0.2 |
| Parecer do analista (PRM_001) | Aprovado, sem ressalvas abertas |
| Autorização de execução | Proprietário entregou o PRM_002 para executar |
| Aprovação de produção / piloto | Não concedida |

## Decisões concretas desta fundação

| Tema | Escolha |
|---|---|
| Java | 21 (paridade Spider; host observado 21.0.12) |
| Spring Boot | 3.4.2; `spring-boot-starter-web` (MVC) |
| Flyway | `flyway-core` + `flyway-database-postgresql` via BOM 3.4.2 (não `starter-flyway` do Boot 4; o BOM 3.4.2 não gerencia esse starter) |
| JPA | `starter-data-jpa` ativo; `ddl-auto=none`; `open-in-view=false`; sem entidades nesta fatia |
| PostgreSQL local | imagem `postgres:18.6`; comprovada via Docker CLI + Flyway no container próprio |
| Portas | Postgres `127.0.0.1:5439`; API `127.0.0.1:8091`; UI `127.0.0.1:5179` |
| Bind | loopback |
| Schema | criado no bootstrap; Flyway `create-schemas=false`; histórico em `actionfinance.flyway_schema_history` |
| Papéis | bootstrap / migrator / runtime; runtime sem SUPERUSER/CREATEDB/CREATEROLE/CREATE |
| Demo auth | perfil `local-demo` **e** `ACTIONFINANCE_DEMO_AUTH_ENABLED=true` |
| CSRF | desabilitado: API stateless Bearer; cookie exigiria revisão |
| Readiness | `readinessState` + `db` + indicador próprio `flywaySchema` (histórico V1). O Boot 3.4.2 não registra contributor `flyway` com `flyway-core` isolado |

## Versões resolvidas nesta máquina

| Componente | Valor | Como |
|---|---|---|
| JDK host | 21.0.12 | `java -version` |
| Maven Wrapper | 3.9.16 | `.mvn/wrapper/maven-wrapper.properties` |
| Node | 24.14.0 | `node -v` |
| npm | 11.9.0 | `npm -v` |
| Spring Boot | 3.4.2 | parent POM + banner |
| Hibernate | 6.6.5.Final | log de subida |
| Flyway (override ActionFinance) | 11.10.1 | POM `flyway.version`; log de subida |
| Driver PostgreSQL | 42.7.5 | BOM 3.4.2 |
| Testcontainers (lib) | 1.21.3 | POM; ITs ainda falham no handshake Desktop 29 |
| Frontend | React 19.2.8, TypeScript 5.9.3, Vite 6.4.3, Vitest 3.2.7 | `package-lock.json` |
| PostgreSQL imagem local/testes | 17.6 | compose `actionfinance-postgres-17` + `PostgresFoundationContainer` |

COR_001: Flyway 11.10.1 em `postgres:18.6` ainda emitiu “latest supported version of PostgreSQL is 17”. A base local passou a **17.6** em volume novo `actionfinance_pgdata_17`. O volume PG18 `actionfinance_actionfinance_pgdata` foi preservado. Testcontainers continua pendente (ver REV_002_COR_001).

## Portas inventariadas (não usadas)

5433 Hub, 5434 PanelDX, 5435 Phanton, 5436 Spider, 5437 SegSense, 5438 Loja, 5545 Panne gate; 8080 Spider, 8088 SegSense, 8090 ocupada, 8095 mock; 5175/5178/5180 frontends vizinhos.

## Panne

Fonte de fatos operacionais. Poderá originar obrigações no ActionFinance quando houver contrato. Nenhuma API de títulos é assumida.
