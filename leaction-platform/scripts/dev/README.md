# Action Hub — dev local estável

Os três processos do Hub (Gateway, Marketplace, Next) precisam subir **na ordem certa**, com o **mesmo `DATABASE_URL`** e **sem processos órfãos** nas portas. Subir cada um “na mão” costuma falhar no Windows (reloders Flask, `npm run dev` do gateway com flag Node 22, porta Postgres errada).

## Comandos

Na raiz `leaction-platform`:

```powershell
.\scripts\dev\start-hub.ps1          # sobe tudo + healthchecks
.\scripts\dev\status-hub.ps1         # verifica Postgres / :4001 / :4012 / :4000
.\scripts\dev\stop-hub.ps1           # mata órfãos nas portas do Hub
.\scripts\dev\restart-hub-service.ps1 -Service marketplace  # reinício pontual
.\scripts\dev\restart-hub-service.ps1 -Service gateway
```

Opções:

```powershell
.\scripts\dev\start-hub.ps1 -SkipFrontend   # só API
.\scripts\dev\start-hub.ps1 -ForceRestart   # limpa portas mesmo se já houver algo
```

Logs: `.dev-logs/*.log`

## Portas

| Serviço        | Porta | Health                                      |
|----------------|-------|---------------------------------------------|
| Action Hub FE  | 4000  | `http://127.0.0.1:4000/api/health`          |
| Gateway        | 4001  | `http://127.0.0.1:4001/health`              |
| Marketplace    | 4012  | `http://127.0.0.1:4012/api/marketplace/health` |
| Postgres       | 5434  | container `leaction_db` (`docker compose up -d db`) |

## Pré-requisitos

1. `.env` na raiz do `leaction-platform` com `DATABASE_URL` apontando para `localhost:5434`
2. `frontend/action-hub/.env.local` com `HUB_GATEWAY_INTERNAL_URL` e `MARKETPLACE_INTERNAL_URL`
3. Venv do plugin: `backend\.venv` com `requirements.txt`
4. Node 20+ (o repo traz `.tools\node`)

## O que o start faz de diferente

1. Confere Postgres (sobe `docker compose up -d db` se a porta estiver fechada)
2. **Mata** listeners/órfãos em 4000/4001/4012 antes de subir
3. Gateway com `node server.js` (sem `--use-system-ca`, que quebra no Node 20)
4. Marketplace com `MARKETPLACE_USE_RELOADER=0` (evita processos duplicados no Windows)
5. Só declara pronto depois dos healthchecks (inclui `/api/marketplace/curation`)
