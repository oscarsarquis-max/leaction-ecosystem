# CURSOR-027-C2-B2 — Bootstrap (falha fechada)

| Campo | Valor |
|---|---|
| Status | **FALHOU — fechado** (sem B3) |
| Data | 2026-08-28 |
| AuthorizedRunId / clientToken | `cursor-027-c2-b2-owner-authorized-once` |
| Task | `…/paneldx-cluster/29d758ed25ef405f8080be35b53aa72d` |
| TD | `panne-db-bootstrap:4` (deregistrada) |
| Exit | **2** |
| Imagem | `db-bootstrap-027-c2-b2-753d8eb-img4` |
| Digest | `sha256:b0447b633d2f7510ff85bc82e0cdc5387ffe8e148492d6993ff1e4137f605186` |
| Scan | COMPLETE, CRITICAL=0, HIGH=0 |
| Segunda execução | **não** |

## Correção de ownership (funcionou)

Sintaxe PG17 efetivamente usada e testada:

`GRANT <migrator> TO <master> WITH ADMIN FALSE, INHERIT FALSE, SET TRUE`

Fluxo por ambiente: validar attrs → grant SET → `CREATE DATABASE … OWNER` → revoke no `finally` → confirmar ausência de SET.

## Estado ao falhar

| Item | Estado |
|---|---|
| `panne` | **criado**, owner `panne_prod_migrator` |
| `panne_demo` | **criado**, owner `panne_demo_migrator` |
| Memberships SET master→migrator | **revogadas** (confirmado no log) |
| Database ACLs CONNECT | **aplicadas** (`database_grants_ok` ×2) |
| Schema harden / default privileges | **falhou** — `42501` *permission denied to change default privileges* |
| Isolation / TLS checks | **não** executados |
| SyncStatus tags | **não** aplicadas |
| Alembic / seed / unaccent | **não** |
| `actionhub_prod` | intacto no início |

## Causa da falha

`ALTER DEFAULT PRIVILEGES FOR ROLE <migrator>` exige poder `SET ROLE` para a migrator. O membership SET foi revogado após `CREATE DATABASE` (correto para ownership) e **não** foi reaberto para a etapa de harden.

## Fechamento

- Inbound bootstrap removido (só prod/demo Fargate)
- Master ausente da task role
- 0 RUNNING; 0 TD ACTIVE
- img2/img3 permanecem `DO_NOT_RUN`
- Sem retry automático

## Próximo gate (não executado)

Corrigir `harden_schema` com membership SET temporária (mesma sintaxe, `finally` revoke) **somente** sob nova autorização — não é B3 nesta passagem.
