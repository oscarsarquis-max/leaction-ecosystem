# Handoff CURSOR-027-A — Gate RDS `actionhub-prod`

| Campo | Valor |
|---|---|
| Data | 2026-08-28 |
| Fase | **Especificação + custo + gate** |
| Provisionamento | **NÃO executado** |
| Deploy Panne | **NÃO executado** |
| Commit/push | **NÃO** nesta passagem |
| Mutações AWS | **Nenhuma** |

## Decisão registrada

- Novo RDS PostgreSQL `actionhub-prod` em `us-east-2`.
- **Não** usar `paneldx-database` para Panne.
- Classe recomendada: `db.t4g.small` (não micro).
- Próximo passo: autorização explícita para executar o [plano de provisionamento](PLANO-PROVISIONAMENTO-RDS-ACTIONHUB-PROD-CURSOR-027-A.md).

## Documentos

| Arquivo | Papel |
|---|---|
| [ADR-RDS-ACTIONHUB-PROD-CURSOR-027-A.md](ADR-RDS-ACTIONHUB-PROD-CURSOR-027-A.md) | Decisão arquitetural |
| [PLANO-PROVISIONAMENTO-RDS-ACTIONHUB-PROD-CURSOR-027-A.md](PLANO-PROVISIONAMENTO-RDS-ACTIONHUB-PROD-CURSOR-027-A.md) | Plano, rede, roles, Alembic, rollback, CLI sanitizada |
| [CUSTO-RDS-ACTIONHUB-PROD-CURSOR-027-A.md](CUSTO-RDS-ACTIONHUB-PROD-CURSOR-027-A.md) | Custo e micro vs small |
| [CHECKLIST-RDS-ACTIONHUB-PROD-CURSOR-027-A.md](CHECKLIST-RDS-ACTIONHUB-PROD-CURSOR-027-A.md) | Segurança e validação |
| [AUDITORIA-AWS-DEPLOY-PANNE-2026-08-28.md](AUDITORIA-AWS-DEPLOY-PANNE-2026-08-28.md) | Contexto de inventário prévio |

## Pergunta de gate

**Autoriza o provisionamento do RDS `actionhub-prod` conforme o plano CURSOR-027-A (criar subnet group privado, SG, instância `db.t4g.small` Postgres 17.9, secrets master gerenciado), sem ainda criar apps Fargate nem migrar dados?**

Resposta esperada: sim/não explícito do proprietário ou Cortex.
