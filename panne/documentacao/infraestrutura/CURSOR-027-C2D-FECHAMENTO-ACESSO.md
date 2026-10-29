# CURSOR-027-C2D — Fechamento de acesso (evidência)

Data: 2026-08-28.

## Inbound RDS `actionhub-prod-rds-sg` (`sg-04269196534d71e08`)

Removido: origem `panne-db-bootstrap-sg` (`sg-0c7a0ce1c81ed4cf6`) porta 5432.

Restante (apenas app):

- `sg-0b4dcda30650d419e` — Panne prod Fargate  
- `sg-0f41648d1720bca80` — Panne demo Fargate  

Sem CIDR público.

## IAM `panne-db-bootstrap-task-role`

Policy inline `panne-db-bootstrap-inline` **sem** ARN do master managed secret (`rds!db-…` ausente).

Permanece: Get/Describe/Put em `panne/prod|demo/db/*` + logs do log group bootstrap.

## Tasks / TD

- RUNNING bootstrap/diag: 0  
- `panne-db-bootstrap:1`: INACTIVE  
- Sem TD diagnóstica registrada nesta passagem  

## Preservado

- Roles parciais no RDS (não DROP)  
- Secrets com syncStatus pending  
- Imagem ECR + digest vulnerável (auditoria)  
- CloudWatch `/ecs/panne/db-bootstrap`  
