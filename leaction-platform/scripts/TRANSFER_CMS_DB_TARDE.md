# Transferência CMS (início da tarde) — patches de banco

Ordem no Postgres `leaction_hub` (local → prod / LAN):

1. `shared/database/patch_cms_headless.sql` — cria `cms_posts` + índices  
2. `shared/database/patch_cms_actionhub_destino.sql` — inclui destino `actionhub`

## Local

```powershell
cd C:\Projetos\leaction-platform
node scripts/apply-cms-headless-patch.js
node scripts/apply-cms-actionhub-destino.js
```

## Produção (EC2 Action Hub)

Após deploy, com `DATABASE_URL` do `.env` do gateway:

```bash
cd /var/www/leaction-platform
node scripts/apply-cms-headless-patch.js
node scripts/apply-cms-actionhub-destino.js
```

## LAN (máquina destino)

Os SQL já vão no git. Depois do `git pull`:

```powershell
cd C:\Projetos
.\sync-db-from-lan.ps1 -SourceHost <IP_ORIGEM> -CompareOnly
# se precisar espelhar dados:
.\sync-db-from-lan.ps1 -SourceHost <IP_ORIGEM> -Force
```

Patches DDL são idempotentes (`IF NOT EXISTS` / `DROP CONSTRAINT IF EXISTS`).
