# Credenciais Lightsail — evidências vs backup

## Regras

1. **Nunca** criar `aws_iam_access_key` no Terraform (não vai para state/outputs/user-data).
2. Keys só em `/opt/qmind/secrets/*.env` no host, modo **`0600`**, fora do git.
3. Usuário da **aplicação** ≠ usuário de **backup** ≠ credencial **administrativa** da conta.
4. Restauração de dump: identidade **admin** (CLI local / usuário admin), nunca o uploader do servidor.

## Após `terraform apply`

```powershell
# App — somente bucket evidências (Get/Put/Delete)
aws iam create-access-key --user-name qmind-homolog-app-evidence

# Backup — PutObject em s3://…/pgdump/* apenas
aws iam create-access-key --user-name qmind-homolog-backup-uploader
```

No host (SSH/browser Lightsail):

```bash
sudo install -d -m 700 /opt/qmind/secrets
sudo tee /opt/qmind/secrets/app-evidence.env >/dev/null <<'EOF'
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-2
EOF
sudo chmod 0600 /opt/qmind/secrets/app-evidence.env

sudo tee /opt/qmind/secrets/backup-uploader.env >/dev/null <<'EOF'
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-2
EOF
sudo chmod 0600 /opt/qmind/secrets/backup-uploader.env

Formato **sem** prefixo `export` (compatível com `env_file` do Compose).
O cron de backup usa `set -a` antes do `source` para exportar as variáveis ao CLI `aws`.
Nunca imprimir o conteúdo desses arquivos em logs/`bash -x`.
```

Referenciar no Compose / cron **sem** copiar secrets para o repositório.

## Rotação

1. `aws iam create-access-key` (nova).
2. Atualizar arquivo `0600` no host; reiniciar API/worker ou cron.
3. Validar operação (upload evidência ou dry-run backup).
4. `aws iam delete-access-key --user-name … --access-key-id AKIA_ANTIGA`.
5. Registrar data da rotação no runbook / gate 011.

Periodicidade sugerida homolog: **90 dias** ou imediata se vazamento suspeito.

## Revogação de emergência

```powershell
aws iam list-access-keys --user-name qmind-homolog-app-evidence
aws iam update-access-key --user-name qmind-homolog-app-evidence --access-key-id AKIA... --status Inactive
# ou delete-access-key
```

Opcional: anexar política Deny explícita ao usuário até recriar keys.

## Mapeamento

| Identidade | Uso | Bucket |
|---|---|---|
| `*-app-evidence` | API/worker | evidências (RW+Delete) |
| `*-backup-uploader` | cron `backup-pg-homolog.sh` | backups Put no prefixo |
| Admin conta | restore, delete backups, TF | full (fora do servidor) |
