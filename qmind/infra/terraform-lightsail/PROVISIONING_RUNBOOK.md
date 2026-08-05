# Runbook — provisionamento do host Lightsail (pós-apply)

Ordem obrigatória. **Não** criar dados reais de cliente antes do restore testado e do fechamento do gate 011.

## 0. Estado atual (2026-08-04 provisionado)

| Item | Status |
|---|---|
| Infra TF | **PASS** — IP `3.20.155.196` |
| SNS `gestao@leaction.com.br` | **Confirmed** |
| Contato Lightsail | **Valid** |
| Stack Compose | **UP** — Caddy + API + web + worker(placeholder) + Postgres |
| HTTPS Let's Encrypt | **PASS** — `api.` / `app.homolog.qmind.com.br` |
| Migrate + seeds (admin) | **PASS** |
| `/health` + `/ready` | **PASS** (HTTPS) |
| Backup CW alarm | **OK** (1º dump criptografado em S3) |
| Cron backup | **instalado** — `03:15` via `/opt/qmind/bin/run-backup.sh` |
| Restore V2 | **PASS** — `RESTORE_V2_20260804T124851Z.md` |
| SSH | **fechado** (só 80/443) |
| Access keys | no host `/opt/qmind/secrets/*.env` (0600/640), nunca no TF |

## 1. Confirmar e-mails (bloqueante)

Na caixa `gestao@leaction.com.br`:

1. Link **Confirm subscription** do SNS (`qmind-homolog-alarms`).
2. Link de verificação do **Lightsail contact method**.

Validar:

```powershell
aws sns list-subscriptions-by-topic `
  --topic-arn arn:aws:sns:us-east-2:253137917703:qmind-homolog-alarms `
  --region us-east-2

aws lightsail get-contact-methods --region us-east-2
```

Critério: SNS com ARN real (não `PendingConfirmation`); Lightsail `status = Verified` / `Valid`.

## 2. Credenciais controladas

Só no servidor, nunca no git/TF. Ver `CREDENTIALS.md`.

| Arquivo | User IAM | Uso |
|---|---|---|
| `/opt/qmind/secrets/app-evidence.env` | `qmind-homolog-app-evidence` | S3 evidências |
| `/opt/qmind/secrets/backup-uploader.env` | `qmind-homolog-backup-uploader` | Put `pgdump/` |

Formato `KEY=VAL` **sem** `export` (Compose `env_file`). Backup script usa `set -a` ao sourcar.

## 3. SSH temporário → provisionar → fechar

1. Descobrir IP público admin `/32`.
2. Atualizar `admin_ssh_cidrs` no tfvars → apply **só** `aws_lightsail_instance_public_ports` (nunca apply que recreate a instância por `user_data` — há `lifecycle.ignore_changes`).
3. SSH Lightsail: chave **+** certificado (`get-instance-access-details`).
4. Bootstrap: `infra/scripts/bootstrap-lightsail-host.sh` (user-data original falhou por shebang indentado + `awscli` apt).
5. Deploy código em `/opt/qmind`, Compose em `/opt/qmind/infra/compose`.
6. Fechar SSH (`admin_ssh_cidrs = []`).

## 4. Stack no host

- Docker + Compose  
- Postgres (sem publish público)  
- FastAPI + worker placeholder + React via Caddy  
- HTTPS: `api.homolog.qmind.com.br` + `app.homolog.qmind.com.br`

## 5. Migrate / seed

Somente identidade admin (`qmind_admin`) — nunca `qmind_app` para migrate.  
Após migrate: `ALTER ROLE qmind_app PASSWORD …` alinhado ao `.env.homolog`.

## 6. Backup + restore (antes do piloto)

1. Cron: `/opt/qmind/bin/run-backup.sh` → `backup-pg-homolog.sh`  
2. Restore com identidade **admin** (`RESTORE_HOMOLOG.md`) — **pendente gate V2**.  
3. Alarme `qmind-homolog-backup-failed` → **OK** após 1º dump.

## 7. Gate runtime (011)

| Check | Status |
|---|---|
| `/health`, `/ready` HTTPS | PASS |
| Cognito wired (pool/client) | PASS (login e2e pendente) |
| Isolamento 2 orgs | pendente |
| Evidências S3 | pendente |
| Jornada completa | pendente |
| SSH fechado | PASS |
| Restore testado | pendente |

## 8. Monitoramento 7 dias (pós-liberação; não bloqueia piloto)

Ver `OBSERVATION_7D_20260804.md`.

```powershell
# Operador (diário)
.\infra\scripts\observe-homolog-daily.ps1
# Host (cron 20 11 * * * UTC): /opt/qmind/bin/observe-homolog-host.sh
```

Artefatos em `infra/terraform-lightsail/observe/`. Budget US$ 30; gatilhos de interrupção no doc de observação.

## Notas operacionais

- User-data TF corrigido (shebang sem indent + AWS CLI v2); `lifecycle.ignore_changes = [user_data]` evita replace acidental.
- Worker Compose: `python -m app.worker` (PDF real; V7b PASS).
- `ENVIRONMENT=homolog` no settings do backend.
- Apex `qmind.com.br` sem A/AAAA — app só em `*.homolog.qmind.com.br`.
