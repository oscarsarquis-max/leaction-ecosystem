# Handoff CURSOR-027-C1 — Fundação pronta; gate C2

| Campo | Valor |
|---|---|
| Estado | SGs + secrets + IAM + ECR + logs **criados** |
| Bootstrap Postgres | **bloqueado** |
| Doc | [CURSOR-027-C1-FUNDACAO-ACESSO.md](CURSOR-027-C1-FUNDACAO-ACESSO.md) |

## IDs rápidos

- prod SG `sg-0b4dcda30650d419e` · demo `sg-0f41648d1720bca80` · bootstrap `sg-0c7a0ce1c81ed4cf6`
- RDS SG `sg-04269196534d71e08` (3× inbound 5432 por SG-ref)
- ECR `panne/backend` (vazio, scan+immutable+lifecycle)
- Roles `panne-ecs-task-execution-role` / `panne-db-bootstrap-task-role`
- Log `/ecs/panne/db-bootstrap` (30d)

## Gate CURSOR-027-C2

Autoriza a próxima passagem para: imagem bootstrap + task definition one-shot + criação segura de databases/roles PostgreSQL (ainda sem Alembic de app, salvo decisão explícita)?
