# CURSOR-027-C2-H1 — Hardening final (sem master)

| Campo | Valor |
|---|---|
| Status | **SUCESSO** |
| Data | 2026-08-28 |
| AuthorizedRunId / clientToken | `cursor-027-c2-h1-hardening-authorized-once` |
| Task | `…/paneldx-cluster/256c29cba97847879b500d4d4fb1aa79` |
| TD | `panne-db-bootstrap:5` (deregistrada após run) |
| Exit | **0** |
| Imagem | `db-bootstrap-027-c2-h1-753d8eb-img5` |
| Digest | `sha256:b8053869cc40d0d7ac63c4b8cfa3407bfa2ec571b715ee5a3bf9d4c125002eb9` |
| Scan | COMPLETE, CRITICAL=0, HIGH=0 |
| Master secret | **não usado** |
| Segunda execução | **não** |

## Princípio

Hardening executado pela migrator de cada ambiente (`ALTER DEFAULT PRIVILEGES` **sem** `FOR ROLE`). Sem CREATE/ALTER ROLE, sem CREATE DATABASE, sem membership do master.

## Estado inicial observado

- DBs `panne` / `panne_demo` existentes com owners corretos (pós-B2)
- Database grants parciais; schema harden incompleto
- Roles seguras; senhas sincronizadas
- Acesso bootstrap fechado; master ausente da task role

## Contrato aplicado

| Superfície | Contrato |
|---|---|
| DATABASE | PUBLIC sem CONNECT/TEMP; migrator+runtime CONNECT; migrator TEMP; runtime sem TEMP; cross-env sem CONNECT |
| SCHEMA public | PUBLIC sem CREATE; migrator USAGE+CREATE; runtime USAGE only |
| Default privileges | tabelas: SIDU → runtime; sequences: USAGE+SELECT → runtime; functions: EXECUTE → runtime, PUBLIC revogado |

## Validação (logs)

- Isolamento cruzado negado / próprio ambiente ok
- `tls_ok=ssl_show:on`
- Runtime DDL negado; DML ok via default privileges
- Probes removidos
- `master_membership_none=true`
- `h1_success`

## Secrets

Tag `SyncStatus=postgres_role_bootstrapped` nos quatro secrets Panne (sem round-trip de valor).

## Fechamento

- Inbound bootstrap removido (RDS SG: só prod/demo Fargate)
- Master continua ausente da task role
- 0 RUNNING; 0 TD ACTIVE
- Imagem/SBOM/scan/logs preservados

## C2

Bootstrap PostgreSQL Panne (roles + DBs + ACLs + harden + sync tags) **concluído** nesta passagem H1.

## Gate seguinte

**CURSOR-027-C3** (Alembic / app deploy) — aguarda autorização explícita.
