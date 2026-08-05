# Restore homolog — identidade administrativa

Restauração **não** usa as keys do servidor (`app-evidence` / `backup-uploader`).

## Pré-requisitos

- Credencial admin da conta (ou papel com `s3:GetObject` + `s3:DeleteObject` no bucket de backups).
- Chave GPG ou arquivo openssl usado na criptografia do dump.
- Instância efêmera ou a própria Lightsail em janela de manutenção.
- Nenhum dado de cliente real sem autorização.

## Passos

```bash
# 1) Baixar (admin)
aws s3 cp s3://BUCKET/pgdump/qmind-STAMP.sql.enc ./dump.enc --region us-east-2

# 2) Descriptografar
openssl enc -d -aes-256-cbc -pbkdf2 -in dump.enc -out dump.sql -pass file:/path/to/backup-openssl.key
# ou gpg --decrypt

# 3) Restaurar no Postgres do Compose (exemplo)
docker compose -f docker-compose.homolog.yml exec -T db \
  psql -U qmind_admin -d qmind < dump.sql
```

## Teste obrigatório antes do piloto

1. Gerar dump com `backup-pg-homolog.sh`.
2. Restore em base **temporária** (não sobrescrever `qmind` live):

```bash
# No host (SSH /32 temporário), após baixar o .enc com identidade admin:
sudo DUMP_ENC=/tmp/qmind-STAMP.sql.enc /opt/qmind/bin/restore-test-homolog.sh
# Script: infra/scripts/restore-test-homolog.sh
# Cria qmind_restore_v2 → valida → DROP; evidência em /opt/qmind/restore-evidence/
```

3. Validar estrutura, seeds, FORCE RLS e counts vs live (o script já faz).
4. Registrar evidência no gate **011** item V2.
5. Fechar SSH (`admin_ssh_cidrs = []`).

### Evidência 2026-08-04

**PASS** — dump `qmind-20260804T124003Z.sql.enc` → temp `qmind_restore_v2` → dropped.  
Relatório: `../terraform-lightsail/RESTORE_V2_20260804T124851Z.md`.

## Falha de backup

Alarme CloudWatch `*-backup-failed` (métrica `QMind/Homolog` / `BackupSuccess`).  
Se o cron falhar, a métrica fica ausente → `treat_missing_data = breaching` (após o primeiro dia com cron ativo).
