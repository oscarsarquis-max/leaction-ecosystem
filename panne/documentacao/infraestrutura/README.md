# Infraestrutura Panne — índice

Documentos de preparação de nuvem (sem deploy automático nestes arquivos).

| Documento | Conteúdo |
|---|---|
| [AUDITORIA-AWS-DEPLOY-PANNE-2026-08-28.md](AUDITORIA-AWS-DEPLOY-PANNE-2026-08-28.md) | Auditoria somente leitura da conta AWS (contexto) |
| [HANDOFF-CURSOR-027-A-GATE-RDS.md](HANDOFF-CURSOR-027-A-GATE-RDS.md) | Gate CURSOR-027-A (especificação) |
| [HANDOFF-CURSOR-027-B-RDS.md](HANDOFF-CURSOR-027-B-RDS.md) | Handoff pós-provisionamento RDS 027-B |
| [HANDOFF-CURSOR-027-C1.md](HANDOFF-CURSOR-027-C1.md) | Handoff fundação de acesso 027-C1 |
| [HANDOFF-CURSOR-027-C2.md](HANDOFF-CURSOR-027-C2.md) | Handoff bootstrap C2 (parcial) |
| [HANDOFF-CURSOR-027-C2D.md](HANDOFF-CURSOR-027-C2D.md) | Handoff diagnóstico C2D |
| [HANDOFF-CURSOR-027-C2-B2.md](HANDOFF-CURSOR-027-C2-B2.md) | Handoff B2 (falha parcial / DBs criados) |
| [HANDOFF-CURSOR-027-C2-H1.md](HANDOFF-CURSOR-027-C2-H1.md) | Handoff H1 — C2 concluído |
| [CURSOR-027-C2-B2-BOOTSTRAP.md](CURSOR-027-C2-B2-BOOTSTRAP.md) | B2: ownership OK; harden 42501 |
| [CURSOR-027-C2-H1-HARDENING.md](CURSOR-027-C2-H1-HARDENING.md) | H1: harden/validação sem master |
| [CURSOR-027-C1-FUNDACAO-ACESSO.md](CURSOR-027-C1-FUNDACAO-ACESSO.md) | SGs, secrets, IAM, ECR, logs |
| [CURSOR-027-C2-BOOTSTRAP-PARCIAL.md](CURSOR-027-C2-BOOTSTRAP-PARCIAL.md) | Evidência C2 parcial / scan |
| [CURSOR-027-C2D-DIAGNOSTICO.md](CURSOR-027-C2D-DIAGNOSTICO.md) | Diagnóstico offline, causa raiz, plano (sem execução) |
| [CURSOR-027-C2D-INCIDENTE-PROCESSO.md](CURSOR-027-C2D-INCIDENTE-PROCESSO.md) | Gate de scan violado (charmap) |
| [CURSOR-027-C2D-VULNERABILIDADES.md](CURSOR-027-C2D-VULNERABILIDADES.md) | 8 CRITICAL + fail-closed |
| [CURSOR-027-C2D-FECHAMENTO-ACESSO.md](CURSOR-027-C2D-FECHAMENTO-ACESSO.md) | Inbound/master revogados |
| [ADR-RDS-ACTIONHUB-PROD-CURSOR-027-A.md](ADR-RDS-ACTIONHUB-PROD-CURSOR-027-A.md) | Decisão: novo RDS; não usar PanelDX DB |
| [PLANO-PROVISIONAMENTO-RDS-ACTIONHUB-PROD-CURSOR-027-A.md](PLANO-PROVISIONAMENTO-RDS-ACTIONHUB-PROD-CURSOR-027-A.md) | Plano de rede, SG, roles, Alembic, rollback |
| [CUSTO-RDS-ACTIONHUB-PROD-CURSOR-027-A.md](CUSTO-RDS-ACTIONHUB-PROD-CURSOR-027-A.md) | Estimativa mensal e micro vs small |
| [CHECKLIST-RDS-ACTIONHUB-PROD-CURSOR-027-A.md](CHECKLIST-RDS-ACTIONHUB-PROD-CURSOR-027-A.md) | Checklist de segurança e validação pós-create |

## Estado

- **CURSOR-027-A/B/C1:** RDS + fundação de acesso.
- **CURSOR-027-C2 (B2+H1):** **concluído** — roles, DBs, ACLs, harden, TLS, SyncStatus. Acesso bootstrap fechado.
- C3 / Alembic / deploy: **não** iniciados — aguarda gate.
