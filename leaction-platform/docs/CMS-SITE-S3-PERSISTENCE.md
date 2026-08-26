# CMS site config — persistência (não perde no deploy)

## O problema

O conteúdo do Micro-CMS (`config_key=inove4us|default`) vive no **Action Hub**, não no deploy do inove4us.  
Ainda assim, wipe de banco / restore agressivo / “sync” errado pode apagar o Postgres.

## A solução

Com `CMS_S3_BUCKET` configurado no gateway:

1. Cada **salvar** no admin (`PUT /api/admin/cms`) grava:
   - Postgres (`cms_site_config`) — leitura rápida
   - S3 `s3://{bucket}/{prefix}/site/{config_key}.json` — **fonte durável**
2. No **boot** do gateway, reidrata o Postgres a partir do S3 (se o snapshot existir).
3. Imagens do CMS já iam para o S3; o JSON do site agora segue o mesmo modelo.

Deploy de código (inove4us ECS / Hub EC2) **não** apaga objetos S3.

## Produção (checklist)

No `.env` do Action Hub (EC2):

```env
CMS_S3_BUCKET=paneldx-cms-assets-2026   # ou bucket dedicado
CMS_S3_PREFIX=cms
CMS_S3_REGION=us-east-2
```

Primeira vez (publicar o que já está no DB de prod para o S3):

```bash
cd /var/www/leaction-platform   # ou path do Hub
node scripts/push-cms-site-to-s3.js --key=inove4us
node scripts/push-cms-site-to-s3.js --key=default   # se usar
```

Reinicie o gateway. Daí em diante: edite CMS só pelo admin; cada save já snapshota.

## Local

Mesmas vars no `.env` do Hub local. Sem bucket = comportamento antigo (só Postgres).

## O que NÃO fazer

- Não espelhar `leaction_hub` inteiro de local → prod “por causa do CMS”.
- Não apagar o prefixo `cms/site/` no S3 em scripts de limpeza.
- Nunca persistir `http://localhost:4000/images/...` no JSON. Upload e `normalizeCmsLanding` reescrevem loopback para a URL pública do S3 (`paneldx-cms-assets-2026`).
