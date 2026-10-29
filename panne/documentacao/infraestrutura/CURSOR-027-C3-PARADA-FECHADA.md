# CURSOR-027-C3 — imagem canônica + Alembic (PARADA FECHADA)

| Campo | Valor |
|---|---|
| Status | **FALHA na task demo** — parado fechado, sem retry AWS |
| Data | 2026-08-28 |
| Fonte | `origin/main@142b35636e9b03715eaa42196ecea4548d9c6412` (HEAD remoto = mesmo SHA; consolidação `5cc13ba` ancestral) |
| Imagem | `backend-027-c3-142b356-img1` |
| Digest | `sha256:b4625c5ca416cd014d89f3e65d849fa740edc5f1ea8a16352981c3bd84e4dc2a` |
| Scan | COMPLETE, CRITICAL=0, HIGH=0 |
| Snapshot | `actionhub-prod-pre-panne-migrations-20260828-151146` (**available**) |
| Demo task | `…/3b39fd9a719a4e8bb6d3d83f43d90560` **exit 2** |
| Prod task | **não executada** |
| AuthorizedRunId demo | `cursor-027-c3-migrate-demo-authorized-once` (clientToken consumido) |

## Causa raiz (demo)

Dockerfile define `ENTRYPOINT ["uvicorn", ...]`. A task definition só sobrescreveu `command`, não o entrypoint. A task executou efetivamente:

`uvicorn python -u /app/migrate_runner.py` → `Error: No such option '-u'.`

Correção necessária (próxima autorização): sobrescrever `entryPoint` na TD **ou** usar ENTRYPOINT neutro na imagem + CMD uvicorn.

## O que já foi validado offline (antes da AWS)

1. **Alembic:** head única `0020_inventory_procurement`; cadeia linear 20 revisões; `unaccent` em `0006_knowledge_grounding`.
2. **FORCE RLS:** migrator `NOBYPASSRLS` não consegue `INSERT` em catálogos após 0009 sem relaxar FORCE. Runner aplica `upgrade +1` com `NO FORCE` / `FORCE` como owner (sem `ALTER ROLE`, sem master).
3. **Local PG17:** migrator owner não-superuser → head OK; `unaccent` OK; idempotência OK; fingerprint `d16e92540d7208b6e11fdae5d7c3f5662cdf0e44cd12c199b30ef460d98e97cd`; runtime sem CREATE/DDL.
4. **Suíte backend (admin local histórico):** **298 passed**, 1 skipped.
5. **Suíte no DB migrator+FORCE:** falhas esperadas por RLS (admin histórico diverge do contrato RDS).

## AWS concluído antes da falha

- Role `panne-db-migration-task-role` (só secrets migrator demo/prod + logs)
- Log group `/ecs/panne/db-migrations` retenção 30d
- Snapshot manual available; deletion protection intacta
- Sem inbound bootstrap adicional; RDS SG só prod/demo Fargate
- Master ausente da migration task role
- TD demo deregistrada; 0 RUNNING/PENDING

## Não feito

- Migration em `panne_demo` / `panne` (schema permanece vazio de Alembic)
- Seed / serviço ECS / ALB / DNS
- Segunda task / correção automática

## Próximo gate

Solicitar **nova autorização CURSOR-027-C3-H2** (ou C3-fix) para:

1. ajustar entrypoint/CMD da imagem ou TD;
2. rebuild/tag/digest novos + scan CRITICAL=0 HIGH=0;
3. **uma** task demo com novo AuthorizedRunId;
4. produção somente após demo exit 0.

Snapshot `actionhub-prod-pre-panne-migrations-20260828-151146` permanece válido para reuso se autorizado.
