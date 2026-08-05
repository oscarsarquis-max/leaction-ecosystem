# Apply inicial Lightsail — 2026-08-04

- Conta: **253137917703** (`paneldx-user-admin`)
- Comando: `terraform apply homolog.tfplan` (plano salvo; Terraform **1.15.8**)
- Resultado: **31 added, 0 changed, 0 destroyed**
- Custo incremental esperado: ~US$ 15–25/mês (além da conta existente)
- Budget: `qmind-homolog-monthly-30`

## Recursos principais

| Recurso | Valor |
|---|---|
| Lightsail | `qmind-homolog-app` (`small_3_0`, Ubuntu 24.04, `us-east-2a`) |
| IP estático | **3.20.155.196** (associado) |
| DNS API | `api.homolog.qmind.com.br` → 3.20.155.196 |
| DNS APP | `app.homolog.qmind.com.br` → 3.20.155.196 |
| S3 evidências | `qmind-homolog-evidence-20260804120548933000000002` (privado) |
| S3 backups | `qmind-homolog-pgdump-20260804120548932400000001` (privado) |
| Cognito pool | `us-east-2_ewD6ck5PM` (`deletion_protection=ACTIVE`) |
| Cognito client | `306r2id1f5gm9vk733v3rlbda6` |
| Cognito domain | `qmind-homolog-3114e5.auth.us-east-2.amazoncognito.com` |
| IAM app | `qmind-homolog-app-evidence` (**sem** access keys) |
| IAM backup | `qmind-homolog-backup-uploader` (**sem** access keys) |
| SNS | `arn:aws:sns:us-east-2:253137917703:qmind-homolog-alarms` |
| CFN alarmes LS | `qmind-homolog-ls-alarms` |
| AutoSnapshot | 06:00 UTC |

## Verificações pós-apply

| Check | Resultado |
|---|---|
| Conta 253137917703 | PASS |
| Apply = plano salvo | PASS (31/0/0) |
| Portas públicas só 80/443 | PASS (SSH ausente) |
| Buckets Block Public Access | PASS (ambos true) |
| Access keys IAM | PASS (nenhuma criada) |
| Backup CW alarm | **ALARM** (esperado — métrica ausente / breaching) |
| Alarmes Lightsail CPU/status | criados; estado INSUFFICIENT_DATA inicial |
| SNS e-mail | **PendingConfirmation** → confirmar em `gestao@leaction.com.br` |
| Contato Lightsail | **PendingVerification** → **PENDÊNCIA OBRIGATÓRIA** (não tratar alarmes LS como sucesso até confirmar) |

## Não feito (conforme autorização)

- Access keys
- Usuários Cognito / dados reais
- Compose / Caddy / cron backup / restore test
- Commit de secrets

## Próximos passos

1. Confirmar e-mails SNS + Lightsail.
2. Após confirmação Lightsail: revalidar `get-contact-methods` → `Verified`.
3. Etapa controlada: keys 0600 + Compose + migrate/seed sintético.
4. Instalar cron + teste backup/restore **antes do piloto**.
5. Registrar custo incremental diário (7 dias) vs Budget US$ 30.
