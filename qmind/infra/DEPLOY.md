# Deploy AWS — QMind homologação (`us-east-2`)

Baseline: **`mvp-fullstack-v0`**.  
Fase: **ADR-010** — Amazon **Lightsail** + S3 + Cognito.  
Domínio: **`qmind.com.br`** (Route 53 `Z10252021E8KYKLG3TEOS`).  
Enterprise ECS/RDS: `terraform-enterprise/` — **não apply agora**.

Gate: `../architecture/04_Docs/011_Homologation_Readiness_Gate.md`.

## Arquitetura

```
Route 53
  api.homolog.qmind.com.br ──┐
  app.homolog.qmind.com.br ──┼→ IP estático Lightsail
                             ▼
Lightsail Ubuntu (small_3_0 ~2 GB)
  ├── Caddy (HTTPS Let's Encrypt)
  ├── React / FastAPI / Worker
  └── PostgreSQL (Compose, sem porta pública)
         └── pg_dump → S3 backups

S3 evidências · Cognito
```

Budget: `qmind-homolog-monthly-30` (US$ 30 → `gestao@leaction.com.br`).

## Terraform Lightsail

```powershell
cd C:\Projetos\qmind\infra\terraform-lightsail
copy terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -recursive
terraform validate
terraform plan -out=homolog.tfplan
# revisar; apply só após OK explícito
```

Após apply:

1. Criar access keys **fora do TF** (`CREDENTIALS.md`): app-evidence e backup-uploader → `/opt/qmind/secrets/*.env` modo `0600`.
2. Compose + Caddy; migrate/seed (admin).
3. Instalar cron de backup (`scripts/install-backup-cron.sh`) antes de dados reais / piloto.
4. Exercício de restore (`scripts/RESTORE_HOMOLOG.md`) — gate V2.
5. SSH: `admin_ssh_cidrs = []` no apply inicial; se abrir, só IP `/32` (nunca `0.0.0.0/0`).
6. AutoSnapshot Lightsail já habilitado no módulo (06:00 UTC default).
7. Confirmar **dois** e-mails em `gestao@leaction.com.br`: assinatura SNS + contato Lightsail.
8. Alarme de backup fica em ALARM até o primeiro `backup-pg-homolog.sh` bem-sucedido (`treat_missing_data=breaching`).

## Não criar agora

ALB, ECS/Fargate, RDS, NAT, API Gateway, ACM no ALB, autoscaling.

## Custo

Ver `COST_ESTIMATE_HOMOLOG.md` — típico **~US$ 15–25/mês**; alerta em **US$ 30**.
