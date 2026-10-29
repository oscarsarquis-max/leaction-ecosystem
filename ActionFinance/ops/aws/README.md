# Pacote de publicação ActionFinance (PRM_007)

Destino: `https://actionfinance.actionhub.com.br`.

As definições estão em `ops/aws/terraform/` (produto) e `ops/aws/state/` (bucket/lock do state). **Aplicadas em 30/09/2026** após o “concordo sim” do DEP_001. Publicação ainda **não** declarada (falta login humano). Detalhe em `documents/reviews/ACTIONFINANCE_REV_007.md`.

Não importar state de Hub, Spider, Panne ou School. Não usar a instância RDS `actionhub-prod`. Não usar a VPC `spider-sandbox-vpc`.

## Arquitetura

TLS no **ALB em `us-east-2`**. Serviço Fargate privado na VPC `PanelDX-vpc`. PostgreSQL RDS dedicado. Cognito User Pool dedicado (Authorization Code + client secret). Sem CloudFront. Sem NAT Gateway novo.

A tarefa web não recebe credenciais migrator e sobe com `ACTIONFINANCE_FLYWAY_ENABLED=false`. Migrations são um `run-task` da família `actionfinance-migrate` (args extra `--spring.main.web-application-type=none` só para o processo sair depois do Flyway; o schema já ficou em v7).

O `healthCheck` do container usa `curl` em `/actuator/health/liveness`. O ALB usa `/actuator/health/readiness`.

## State

1. `terraform -chdir=ops/aws/state` já aplicado (bucket `actionfinance-tfstate-253137917703` + tabela `actionfinance-tf-lock`).
2. Produto: `terraform -chdir=ops/aws/terraform init -backend-config=backend.hcl`.

Não versionar `*.tfstate`, `terraform.tfvars` nem `backend.hcl`.

## Operação

- Secrets: `scripts/ops/put-prod-secrets.ps1` (JSON via ficheiro; não imprimir).
- Roles RDS: `scripts/ops/run-rds-bootstrap.ps1`.
- Admin: `scripts/ops/run-access-admin-ecs.ps1`.
- Rollback: `desired_count=0`; se preciso `enable_public_dns=false`. Preservar RDS.

## Validação local

```powershell
cd C:\Projetos\ActionFinance\ops\aws\terraform
terraform fmt -check
terraform validate
```
