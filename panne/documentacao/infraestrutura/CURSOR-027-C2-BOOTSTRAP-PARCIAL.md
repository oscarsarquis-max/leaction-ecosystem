# CURSOR-027-C2 — Bootstrap (criação parcial / gate de scan)

| Campo | Valor |
|---|---|
| Status | **INTERROMPIDO — criação parcial** |
| Data (UTC) | 2026-08-28 |
| Task | `…/task/paneldx-cluster/ddb2985f3ec7486384e47728903400c5` |
| Task definition | `panne-db-bootstrap:1` |
| Exit code container | **2** (`ERROR: unhandled ProgrammingError`) |
| Imagem | `panne/backend:db-bootstrap-027-c2-86374c3908f3` — **`DO_NOT_RUN`** |
| Digest | `sha256:87d4cef31efb840834f842103997b3a50f455b4e434073567013075c5b5da65e` — **`DO_NOT_RUN`** |
| Pós-C2D | Ver [CURSOR-027-C2D-DIAGNOSTICO.md](CURSOR-027-C2D-DIAGNOSTICO.md) — TD INACTIVE; inbound/master fechados |
| Plataforma | linux/arm64 |
| Alembic / seed / unaccent | **não** executados |

## Scan ECR

| Severidade | Contagem |
|---|---|
| CRITICAL | **8** (ex.: CVE-2026-33845 gnutls28, e outras no base Debian) |
| HIGH | 49 |
| MEDIUM | 45 |
| LOW | 6 |

**Falha de processo:** o parse do relatório de scan quebrou no PowerShell (`charmap`); a task foi iniciada **antes** de aplicar o gate CRITICAL. Em seguida a task falhou sozinha (exit 2). Mitigação candidata (não aplicada como aceite): CVEs estão no base `python:3.12.8-slim-bookworm`; o entrypoint Python/psycopg **não** expõe serviço DTLS/GnuTLS — risco residual de base OS em tarefa one-shot efêmera. **Requer decisão explícita** do proprietário para aceitar ou reconstruir com base mais nova.

## O que o log comprova (sanitizado)

```
bootstrap_start cycle=027-C2
secret_loaded … (4 secrets, só nomes/users/dbs)
actionhub_prod_intact=true
role_created=panne_prod_migrator
role_created=panne_prod_runtime
role_created=panne_demo_migrator
role_created=panne_demo_runtime
role_attrs_ok=… (4)
ERROR: unhandled ProgrammingError
```

## Objetos provavelmente existentes

| Objeto | Estado |
|---|---|
| Roles `panne_prod_migrator`, `panne_prod_runtime`, `panne_demo_migrator`, `panne_demo_runtime` | **criadas** (attrs sem superuser/createdb/createrole/replication/bypassrls) |
| Databases `panne`, `panne_demo` | **não confirmados** (falha antes/no `CREATE DATABASE`) |
| Grants / schema harden / isolation tests | **não** |
| Secrets `syncStatus` | ainda `pending_postgres_role_bootstrap` (metadata não atualizada) |
| `actionhub_prod` | intacto no momento do log |

## Fechamento seguro — NÃO executado

Por falha parcial, **mantidos** deliberadamente:

- inbound bootstrap SG → RDS SG (diagnóstico);
- permissão da task role ao master secret;
- task definition `panne-db-bootstrap:1` (referência);
- imagem no ECR por digest;
- logs 30 dias.

**Não** removidos objetos Postgres. **Não** houve retry cego.

## Causa provável (hipótese)

`ProgrammingError` logo após criação das roles — tipicamente `CREATE DATABASE` / transição `autocommit` no psycopg3. Correção candidata no código (não reexecutada): garantir `commit`/fechar cursores antes de `conn.autocommit = True` e registrar `exc.sqlstate` sem secrets.

## Arquivos do bootstrap (contexto isolado)

`panne/infra/db-bootstrap-c2/` — Dockerfile, requirements, bootstrap.py, .dockerignore

## Custo da execução

Fargate ARM64 0.25 vCPU / 0.5 GB por poucos minutos: **centavos**; ECR storage da imagem: baixo.

## Próximas opções (aguardando orientação)

**A)** Aceitar risco CRITICAL do base (documentado) + autorizar correção do `CREATE DATABASE` e **reexecução** C2 idempotente.  
**B)** Reconstruir imagem com base mais recente sem CRITICAL, depois reexecutar.  
**C)** Diagnóstico SQL controlado (nova task/read-only) para listar DBs/roles antes de qualquer mutate.

PanelDX: sem alteração nesta passagem.
