# MudaEdu

Fork do [PanelDX](https://github.com/leaction/PanelDX) para a migração de domínio **paneldx.com.br** → **mudaedu.com.br**. Todo o desenvolvimento de marca e URLs públicas desta linha acontece neste repositório; o PanelDX original permanece intocado.

## Documentação

- [Mapa de domínio e DNS](docs/MAPA-DOMINIO-MUDAEDU.md) — transição Registro.br → Route 53, ACM e deploy AWS.

## Pré-requisitos

- PostgreSQL do **ecossistema** (container `leaction_db`), não o `paneldx_db` do compose isolado
- Node.js e Python 3 com dependências instaladas nos diretórios `LeAction_Sys_FE` e `LeAction_SysF`

### Banco local (padrão monorepo)

| Item | Valor |
|------|--------|
| Banco | `LeAction_SysF` |
| Host | `127.0.0.1` |
| Porta | tipicamente `5433` (confira `docker port leaction_db 5432` — pode ser `5434`) |
| User | `admin` |
| Config | `LeAction_SysF/.env` (veja `.env.example`) |

O `docker-compose.yml` com `paneldx_db:5434` é só para subir o mudaedu **isolado** do restante do monorepo.

## Subir o ambiente local

Na raiz do projeto (`C:\Projetos\mudaedu`):

```powershell
.\start-local.ps1
```

Opções úteis:

- `.\start-local.ps1 -Only backend` ou `-Only frontend`
- `.\start-local.ps1 -InstallDeps` — instala dependências antes de subir
- `.\start-local.ps1 -OpenBrowser` — abre o frontend após iniciar
- `.\restart-local.ps1` — libera portas e reinicia os serviços

URLs locais típicas:

- Frontend (BFF): http://localhost:3000
- Backend Flask: http://localhost:5002

## Seed de demonstração

```powershell
.\seed-dev.ps1 1
```

Consulte `.\seed-dev.ps1 -?` ou o cabeçalho do script para perfis (`1`, `4`, `-LeadOnly`, etc.).

## Variáveis de ambiente

Copie os exemplos e ajuste segredos locais (nunca commite `.env` preenchidos):

- Raiz: `.env.example`
- Backend: `LeAction_SysF/.env`, `LeAction_SysF/.env.production.example`
- Frontend: `LeAction_Sys_FE/.env.development`, `LeAction_Sys_FE/.env.production.example`

Em produção, a URL pública alvo é **https://mudaedu.com.br** (`MUDAEDU_PUBLIC_URL` / `PANELDX_PUBLIC_URL` no Flask).
