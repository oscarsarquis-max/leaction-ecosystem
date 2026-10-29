# Ensaio de restore isolado — PRM_007

Plano curto antes da execução. Restore isolado já previsto no [DEP_001](ACTIONFINANCE_DEP_001.md). Sem nova aprovação geral. Sem alteração de recurso compartilhado.

| Item | Valor |
|---|---|
| Origem | RDS `actionfinance` (`db.t4g.micro`, PG 17.9, privado, cifrado, retenção 7 dias) |
| Backup usado | PITR `UseLatestRestorableTime` (não dump local). Snapshot automático existente: `rds:actionfinance-2026-09-30-13-45` (cifrado; mais antigo que o ponto PITR) |
| Destino | **Nova** instância `actionfinance-restore-prm007` |
| Rede | Mesmo `actionfinance-private` + `sg-014d62a41c4069157`; `PubliclyAccessible=false`; sem DNS público |
| Cifra | Herdada da origem (KMS da instância) |
| Master | PITR Postgres não aceita `ManageMasterUserPassword`; a prova liga ao restaurado com o secret master da origem, sem imprimir o valor. Não aponta o JDBC de produção para o destino. |
| App / ingresso | Não apontados para o destino. Sem tarefa web, sem e-mail, sem integração |
| Custo transitório | `db.t4g.micro` US$ 0,016/h + gp3. Ensaio previsto **1–2 h** → **≪ US$ 1**. Sem NAT Gateway, sem IP público, sem ALB extra. **Não é gasto material além do plano.** |
| Duração prevista | 15–25 min até `available` + 10 min de verificação + 10–15 min de exclusão |
| Verificações | Flyway, contagens (cadastro/vínculo/auditoria/factos), owners/grants, runtime sem DDL/DELETE de factos, invalidar só `SPRING_SESSION` no restaurado |
| Limpeza | `delete-db-instance --skip-final-snapshot` só do ID `actionfinance-restore-prm007`. Origem, backups de 7 dias, secrets, ECS e `paneldx-alb` preservados |

Não é compromisso formal de RTO/RPO. O tempo medido é só deste ensaio.
