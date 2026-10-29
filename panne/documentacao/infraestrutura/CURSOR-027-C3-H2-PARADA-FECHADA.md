# CURSOR-027-C3-H2 — PARADA FECHADA (demo exit 1)

| Campo | Valor |
|---|---|
| Status | **FALHA demo** — fechado; produção **não** executada; sem retry |
| Task | `…/0501b07f068a41a6ba256277b65dabce` |
| TD | `panne-db-migration:3` (entryPoint correto; deregistrada) |
| Exit | **1** |
| AuthorizedRunId | `cursor-027-c3-h2-migrate-demo-authorized-once` (consumido) |
| Digest | `sha256:b4625c5ca416cd014d89f3e65d849fa740edc5f1ea8a16352981c3bd84e4dc2a` (inalterado) |
| Snapshot | `actionhub-prod-pre-panne-migrations-20260828-151146` available |

## Diagnóstico H2 (antes da task)

Ver [CURSOR-027-C3-H2-DIAGNOSTICO.md](CURSOR-027-C3-H2-DIAGNOSTICO.md). Entrypoint override **corrigiu** o problema uvicorn.

## Causa da falha H2

1. Preflight TLS/owner **OK** (`ssl=on`, `panne_demo_migrator` / `panne_demo`).
2. `alembic current` falhou em `alembic/env.py` → `config.set_main_option("sqlalchemy.url", …)`.
3. Senha URL-encoded contém `%XX`; `ConfigParser` interpreta `%` como interpolação → `ValueError: invalid interpolation syntax`.
4. Nenhuma migration aplicada (falha antes do upgrade).

## Vazamento operacional (ação imediata)

O traceback do Alembic incluiu a URL completa (com senha) nos logs da task (`/ecs/panne/db-migrations`).

**Recomendado antes do próximo gate:** rotacionar o secret `panne/demo/db/migrator` e tratar o stream CloudWatch da task `0501b07f…` como sensível (retenção/exclusão conforme política). Logs locais foram sanitizados na workstation.

Produção **não** foi tocada; secret prod não aparece nesse stream.

## Correção necessária (próximo gate, sem rebuild obrigatório se runner for atualizado na imagem)

No runner / env de migration:

- passar URL ao Alembic com `%` escapado (`%%`) **ou** `ConfigParser(interpolation=None)`;
- **nunca** imprimir stderr bruto do Alembic sem redigir URLs/credenciais;
- preferir validar `alembic_version` via psycopg (já autenticado) em vez de `alembic current` pré-flight se o env.py for sensível a interpolação.

Se a correção exigir novo arquivo na imagem → novo digest + scan. Se for só TD/env → confirmar se o runner na imagem atual pode receber patch sem rebuild (nesta imagem o runner é estático → **rebuild necessário**).

## Fechamento

- 0 RUNNING/PENDING
- 0 TD ACTIVE `panne-db-migration`
- RDS SG somente prod/demo Fargate
- migration role sem master
- snapshot / imagem / scan preservados
- sem segunda task; sem C4

## Gate seguinte

Solicitar **CURSOR-027-C3-H3**:

1. rotacionar secret demo migrator (se ainda não feito);
2. corrigir interpolação + redaction no runner;
3. nova imagem/digest + scan CRITICAL=0 HIGH=0;
4. um AuthorizedRunId demo novo;
5. produção só após demo exit 0.
