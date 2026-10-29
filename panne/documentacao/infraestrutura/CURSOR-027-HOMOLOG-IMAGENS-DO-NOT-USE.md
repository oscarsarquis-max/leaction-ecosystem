# CURSOR-027 homolog — imagens DO_NOT_USE (rebuild acidental na correção de validação)

| Tag | Digest | Status |
|---|---|---|
| `backend-027-homolog-seed-142b356-img7d` | `sha256:68a679b59d7fa3c1b5972b41fb66a17ad3d2a1b8d8d21b78652e2e4939cbf844` | **DO_NOT_USE** — rebuild acidental; não apagar; sem scan/task/deploy |
| `backend-027-homolog-seed-142b356-img7c` | `sha256:9eb41c33433e03d27dc750ac3ade1957bc5f5604127cd25799d96cb812e41096` | **DO_NOT_USE** — rebuild interrompido/parcial |
| `backend-027-homolog-seed-142b356-img7` | `sha256:4dbe9a3d68837730045e58d6f1969eb2538165010ee362ea8e27562fae9f485b` | **DO_NOT_USE** — índice OCI / sem helpers estáveis |

## Candidata única demo (aprovada) — em uso

| Tag | Digest | Scan | Deploy |
|---|---|---|---|
| `backend-027-homolog-seed-142b356-img7b` | `sha256:01c691ebd21fae0dbaf64c5cf2fad35e49bd2fa49f433d60f4be8a329abc0236` | COMPLETE CRITICAL=0 HIGH=0 | **serviço `panne-demo-api`** |

## Referências ECS

- **ACTIVE** TD `panne-*`: `panne-demo-api` → **somente img7b**.
- **INACTIVE** `panne-db-migration:8` apontava img7d — deregistrada; sem serviço.
- Serviços PanelDX/calc/leactionf — **sem** digests Panne acidentais.

## Homologação demo (estado)

- Seed `panne_demo` validado com tenant `set_config` (FORCE RLS preservado, sem BYPASSRLS, sem reseed).
- `https://demo.panne.ia.br` (CloudFront+S3) + `https://api.demo.panne.ia.br` (ALB→Fargate img7b).
- Produção lógica `panne` intocada.

Regras: não rebuild; não apagar imagens DO_NOT_USE; não deployar digests acidentais.
