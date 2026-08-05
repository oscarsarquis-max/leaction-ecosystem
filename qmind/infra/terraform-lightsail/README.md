# Terraform — QMind Lightsail (homolog / piloto)

**Perfil ativo** (ADR-010 emenda Lightsail). Não aplicar `../terraform-enterprise/`.

```powershell
cd C:\Projetos\qmind\infra\terraform-lightsail
copy terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -recursive
terraform validate
terraform plan -out=homolog.tfplan
terraform show -no-color homolog.tfplan > homolog-plan.txt
# revisar homolog-plan.txt localmente (gitignored); apply só com aprovação
```

Segurança: `CREDENTIALS.md` · backup: `../scripts/backup-pg-homolog.sh` · restore: `../scripts/RESTORE_HOMOLOG.md`.

Budget: `qmind-homolog-monthly-30` (US$ 30 → `gestao@leaction.com.br`).
