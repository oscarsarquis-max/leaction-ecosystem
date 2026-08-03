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

Módulos previstos (scaffold inicial):

- ECR
- Cognito User Pool + client
- S3 evidências (privado)
- Secrets (placeholders / random)
- RDS PostgreSQL
- Security groups
- (próximo incremento) ALB + ECS + CloudWatch alarms

State remoto: configurar backend S3 após o primeiro bucket de state do ecossistema (não commitar `*.tfstate`).

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
