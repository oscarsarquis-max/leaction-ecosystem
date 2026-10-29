# Handoff CURSOR-027-B — RDS `actionhub-prod` provisionado

| Campo | Valor |
|---|---|
| Data | 2026-08-28 |
| Fase | Provisionamento controlado **concluído** |
| Estado | available · isolado · **zero inbound** |
| Documentação detalhada | [CURSOR-027-B-PROVISIONAMENTO-RDS.md](CURSOR-027-B-PROVISIONAMENTO-RDS.md) |

## IDs úteis (sem segredos)

- RDS: `actionhub-prod`
- SG: `sg-04269196534d71e08` (`actionhub-prod-rds-sg`)
- Subnet group: `actionhub-prod-private`
- Master secret: gerenciado (`rds!db-…`, status active) — **não** consultar valor sem necessidade

## Bloqueios mantidos

- Sem Fargate / DNS / ACM / ALB / buckets
- Sem DBs `panne` / `panne_demo`
- Sem roles app / `unaccent` / Alembic / deploy
- Sem commit/push automático
- Sem alteração PanelDX

## Próxima autorização necessária

Autorizar bootstrap lógico (databases + roles + secrets app) e/ou regras inbound dos SGs Panne — **somente com ordem explícita**.
