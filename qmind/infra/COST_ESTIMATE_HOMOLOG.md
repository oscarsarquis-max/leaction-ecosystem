# Estimativa de custo — QMind homolog (`us-east-2`)

**Status:** estimativa **pré-`terraform plan` / pré-apply**, com defaults do scaffold (`db.t4g.micro`, Fargate 0.5 vCPU / 1 GB, desired 1–2).  
Substituir por Infracost ou AWS Pricing Calculator após o primeiro `plan` com `tfvars` reais.

| Recurso | Config default | Ordem de grandeza (USD/mês) | Notas |
|---|---|---|---|
| RDS PostgreSQL | `db.t4g.micro`, 20 GB gp3, single-AZ, backup 7d | ~15–25 | Persistente; aplicar primeiro |
| ALB | 1 ALB + LCU leve | ~16–25 | Tráfego homolog baixo |
| ECS Fargate API | 0.5 vCPU / 1 GB × 1 task (24×7) | ~15–20 | Sobe com `max_capacity=2` |
| NAT Gateway | 1 NAT (se VPC usar NAT) | ~32 + dados | Cost driver; fora do módulo se já existir |
| S3 evidências | GB baixos + PUT/GET | <5 | Quarentena + PDF |
| ECR | armazenamento imagens | <5 | Tags imutáveis |
| Cognito | MAU baixos | free tier / <5 | |
| Secrets Manager | 1 secret | ~0.40 | |
| CloudWatch Logs | retenção 30d | 2–10 | Depende de volume |
| CloudWatch Alarms | ~10 alarmes | <5 | |
| SNS | notificações | <1 | |
| **Subtotal app (sem NAT)** | | **~55–95** | |
| **Com 1 NAT dedicado** | | **~90–130** | |

## Ordem de gasto no apply por etapas

1. ECR / S3 / Cognito / Secrets — baixo  
2. RDS — médio contínuo  
3. ALB + ECS — médio contínuo  
4. NAT (se criado nesta conta) — alto contínuo  

## Rollback e custo

Rollback de **deployment** (imagem/`task_definition`) não remove RDS/S3.  
`terraform destroy` em homolog só após backup e aprovação explícita.
