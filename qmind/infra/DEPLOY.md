# Deploy AWS — QMind homologação (`us-east-2`)

Baseline de produto: tag **`mvp-fullstack-v0`**.  
Infraestrutura **própria** do QMind (não reutilizar RDS/S3/Cognito do Hub nem do inove4us).

Gate: `../architecture/04_Docs/011_Homologation_Readiness_Gate.md`.

## Arquitetura alvo

```
Internet → Route 53 (domínio homolog)
        → ALB (HTTPS / ACM)
        → ECS Fargate (API) + worker (jobs PDF)
        → RDS PostgreSQL (database lógico qmind)
        → S3 privado (evidências)
        → Cognito (OIDC)
        → Secrets Manager
```

Região: **`us-east-2`** (ADR-009).

## Identidades de banco (obrigatório)

| Papel | Uso | URL |
|---|---|---|
| Admin / migração | Alembic + seeds de catálogo | `DATABASE_URL_ADMIN` |
| Runtime | API e worker | `DATABASE_URL_APP` → role **`qmind_app`** (FORCE RLS) |

Nunca colocar a URL admin na task definition da API.

## Pré-requisitos (uma vez)

1. Conta ou isolamento de tags para `Environment=homolog`.
2. VPC com subnets públicas (ALB) e privadas (tasks + RDS) + NAT.
3. Hosted zone + certificado ACM em `us-east-2` para o hostname homolog.
4. AWS CLI autenticado com permissão para ECR/ECS/RDS/S3/Cognito/Secrets/IAM.

## Terraform

```powershell
cd C:\Projetos\qmind\infra\terraform
copy terraform.tfvars.example terraform.tfvars
# preencha vpc, subnets, domain, certificate_arn, etc.

terraform init
terraform plan -out=homolog.tfplan
terraform apply homolog.tfplan
```

Módulos neste scaffold:

- ECR (api / web / worker)
- Cognito User Pool + client
- S3 evidências (privado, versionado)
- Secrets Manager (ARN nos outputs; valores não vão para tfvars)
- RDS PostgreSQL + SG
- Security groups: ALB → ECS → RDS
- ACM (ARN existente em `us-east-2` **ou** certificado DNS criado pelo Terraform)
- ALB público: HTTP→HTTPS, TG `target_type=ip`, health `/health`
- ECS Fargate em subnets privadas (`awsvpc`), circuit breaker + rollback
- Task **execution** role (ECR/logs/secrets) ≠ task role (S3 evidências)
- CloudWatch Logs (retenção configurável)
- Autoscaling conservador (default min 1 / max 2)
- Alarmes ALB/ECS/RDS → SNS

State remoto: configurar backend S3 após o primeiro bucket de state do ecossistema (não commitar `*.tfstate`).

## Antes do primeiro apply (obrigatório)

```powershell
cd C:\Projetos\qmind\infra\terraform
copy terraform.tfvars.example terraform.tfvars
# edite apenas IDs/ARNs/não-sensíveis

terraform fmt -recursive
terraform init
terraform validate
# análise de segurança (escolha uma):
#   docker run --rm -v ${PWD}:/tf aquasec/tfsec /tf
#   docker run --rm -v ${PWD}:/tf bridgecrew/checkov -d /tf

terraform plan -out=homolog.tfplan
# revisar plano + estimar custo (AWS Pricing / Infracost)
```

### Apply por etapas (persistentes primeiro)

1. `terraform apply -target=...` ECR, S3, Cognito, Secrets, RDS (dados)
2. Validar ACM (DNS) se criado pelo Terraform
3. Push imagem `api_image_tag` para ECR
4. Apply ALB + ECS + autoscaling + alarms
5. DNS alias → `alb_dns_name` / `alb_zone_id`
6. Migrar/seed com admin; rotacionar `DATABASE_URL_APP` no secret
7. Validar itens no gate `011_Homologation_Readiness_Gate.md`

### Rollback de deployment

- Circuit breaker ECS com `rollback = true` em falha de health.
- Redeploy tag anterior (ex. `mvp-fullstack-v0`) via nova task definition / `force-new-deployment`.
- Ver output `rollback_hints`.

## Migração e seed (admin)

Com RDS acessível (bastion / VPN / task one-shot):

```powershell
cd C:\Projetos\qmind\infra\scripts
.\migrate-and-seed-homolog.ps1 -AdminDatabaseUrl $env:DATABASE_URL_ADMIN
```

Equivale a:

1. `alembic upgrade head` (admin)
2. aplicar `backend/seeds/001_maturity_catalog_v0.sql`
3. aplicar `backend/seeds/002_assessment_model_stub.sql`

## Build e push

Imagens devem ser tagadas com o **hash/tag git** (ex.: `mvp-fullstack-v0`, `82e637f`), nunca só `latest` em homolog.

```powershell
# incremento futuro: infra/scripts/build-and-push.ps1
```

## Rollback

1. Redeploy da imagem correspondente a `mvp-fullstack-v0` (ou tag homolog anterior conhecida).
2. Confirmar `/health` e `/ready`.
3. Não reverter migrações destrutivas sem plano; preferir forward-fix.

## Segurança

- `AUTH_MODE=cognito` e `ENVIRONMENT` ≠ uso de headers dev.
- `STORAGE_BACKEND=s3` com bucket dedicado.
- `ALLOW_SIMULATED_SECURITY_PASS=false` em homolog/prod.
- CORS restrito ao origin do front homolog.
