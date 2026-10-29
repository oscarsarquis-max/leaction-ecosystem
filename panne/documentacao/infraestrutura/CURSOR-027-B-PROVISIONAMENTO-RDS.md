# CURSOR-027-B — Provisionamento RDS `actionhub-prod`

| Campo | Valor |
|---|---|
| Status | **Provisionado, isolado, sem conectividade de aplicação** |
| Conta | `253137917703` |
| Região | `us-east-2` |
| Identidade | `arn:aws:iam::253137917703:user/paneldx-user-admin` |
| Início (UTC) | `2026-08-28T10:42:27Z` (subnet group / SG) |
| RDS create submetido (UTC) | ~`2026-08-28T10:43Z` |
| Estado `available` (UTC) | ~`2026-08-28T10:51Z` |
| Commit/push | **não** nesta passagem |
| Migrations / deploy / Fargate | **não** executados |

## Recursos criados

| Recurso | Identificador | ARN / ID sanitizado |
|---|---|---|
| DB subnet group | `actionhub-prod-private` | `arn:aws:rds:us-east-2:253137917703:subgrp:actionhub-prod-private` |
| Security group | `actionhub-prod-rds-sg` | `sg-04269196534d71e08` |
| DB instance | `actionhub-prod` | `arn:aws:rds:us-east-2:253137917703:db:actionhub-prod` |
| Master secret (gerenciado) | prefixo `rds!db-…` | `arn:aws:secretsmanager:us-east-2:253137917703:secret:rds!db-****` (status **active**) |

Subnets no group: `subnet-0a1da7a0765588962` (us-east-2a), `subnet-0693afdb3330b683a` (us-east-2b).

## Configuração efetiva

| Parâmetro | Valor aplicado |
|---|---|
| Engine / versão | postgres **17.9** |
| Classe | `db.t4g.small` |
| Multi-AZ | false |
| Storage | gp3 **20** GiB, max **100** |
| Encrypted | true (KMS na conta; key id omitido) |
| PubliclyAccessible | **false** |
| VPC | `vpc-017dc4cac16ba2c59` |
| Subnet group | `actionhub-prod-private` |
| SG | `sg-04269196534d71e08` |
| Porta | 5432 |
| DBName inicial | `actionhub_prod` |
| Master username | `actionhub_admin` |
| Backup retention | **7** |
| Backup window | `06:00-06:30` UTC |
| Maintenance | `tue:07:00-tue:07:30` UTC |
| Deletion protection | **true** |
| Copy tags to snapshots | **true** |
| Performance Insights | **true**, retenção **7** |
| Enhanced Monitoring | **off** (`MonitoringInterval=0`) |
| Auto minor version upgrade | **true** |
| Endpoint | `actionhub-prod.****.us-east-2.rds.amazonaws.com` (não publicar host completo) |
| AZ primária | us-east-2a |

Tags aplicadas: Name, Project, Product, Environment, ManagedBy, CostCenter, Criticality, DataClassification, CursorCycle=027-B.

## Validações de rede e segurança

- [x] Inbound no SG RDS: **0 regras**
- [x] Sem CIDR/SG PanelDX/bastion autorizados
- [x] Não público
- [x] Subnet group só privadas, 2 AZs
- [x] Segredo master gerenciado **active**; valor **não** lido
- [x] `paneldx-database` inalterado (available, `db.t3.micro`, public=true, backup=1, SG `sg-07bfd4f6c938cd47a`)
- [x] Sem cluster/serviço Panne em ECS; ALBs existentes sem mudança desta passagem

## Custo estimado confirmado

≈ **US$ 26–28/mês** (compute ~23,40 + gp3 20 GiB ~2,30 + secret master ~0,40), PI 7d sem custo adicional típico.

## Diferenças / alertas vs plano 027-A

1. Primeira tentativa de `create-db-instance` falhou na CLI por flag inválida `--no-monitoring-interval` (**nada criado**); retry sem a flag obteve sucesso.
2. **Auto minor version upgrade = true** (padrão seguro de patches; plano 027-A não fixava o bit — registrado aqui).
3. KMS: criptografia ativa com chave na conta (não foi necessário CMK dedicada nova).

## Estado

**Provisionado, isolado e sem conectividade de aplicação.**  
Nenhuma aplicação consegue conectar até existir regra inbound a partir de SGs futuros da Panne.

## Próximo gate (não iniciado)

CURSOR-027-C (ou nome que o Cortex definir): criar databases `panne` / `panne_demo`, roles mínimas, secrets de app, e só então connectivity SG + migrations — **mediante nova autorização**.
