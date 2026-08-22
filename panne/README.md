# Panne

Plataforma de inteligência de panificação. Esta pasta é a aplicação **Panne** (`panne`), independente e irmã das demais apps do workspace `leaction-ecosystem`.

Esta entrega é só a **fundação** (API, página inicial e Postgres). Não há funcionalidades de negócio.

## Pré-requisitos

- Docker com o container `leaction_db` do workspace (Postgres compartilhado)
- Python 3.12 ou superior (versão mínima oficial; `requires-python = ">=3.12"`)
- Node.js LTS do workspace: `leaction-ecosystem/.tools/node`
- npm (vem com o Node acima)

## Configuração

```powershell
cd C:\Projetos\leaction-ecosystem\panne
copy .env.example .env
```

O `.env.example` não contém credenciais. No `.env` local (não versionado), substitua `<configure-local-user>` e `<configure-local-password>` pelas credenciais do Postgres compartilhado desta estação (`leaction_db`). Ajuste o host/porta se `docker port leaction_db 5432` não for `5434`. Não copie senhas para o repositório nem para arquivos rastreados.

O script `scripts/dev/bootstrap-db.ps1` cria o banco `panne` no container `leaction_db` usando o papel administrativo já existente nesse container (sem gravar senha no repositório). Ajuste o papel no script localmente se o seu container usar outro.

## Banco

```powershell
cd C:\Projetos\leaction-ecosystem\leaction-platform
docker compose up -d db

cd C:\Projetos\leaction-ecosystem\panne\backend
# Use um interpretador Python 3.12+
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

cd ..
powershell -File .\scripts\dev\bootstrap-db.ps1
```

O Alembic sobe até `0003_ingredient_catalog`: fundação (`0001`), multiempresa (`0002`) e catálogo de ingredientes (`0003`). Sem APIs de negócio.

```powershell
cd C:\Projetos\leaction-ecosystem\panne\backend
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe current
```

## Execução

Em dois terminais:

```powershell
powershell -File C:\Projetos\leaction-ecosystem\panne\scripts\dev\start-backend.ps1
# API: http://127.0.0.1:5080/health (sem banco) e /ready (Postgres)
```

```powershell
$env:Path = "C:\Projetos\leaction-ecosystem\.tools\node;$env:Path"
powershell -File C:\Projetos\leaction-ecosystem\panne\scripts\dev\start-frontend.ps1
# UI em http://127.0.0.1:5180
```

## Testes e verificação

```powershell
cd C:\Projetos\leaction-ecosystem\panne\backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .

cd ..\frontend
$env:Path = "C:\Projetos\leaction-ecosystem\.tools\node;$env:Path"
npm test
npm run typecheck
npm run build
```

## Estrutura

```
panne/
  backend/          FastAPI + SQLAlchemy async + Alembic
  frontend/         React + TypeScript + Vite
  documentacao/     prompts, retornos, legado e arquitetura
  scripts/dev/      bootstrap do banco e start local
```

Análise estrutural de ingredientes (sem implementação): `documentacao/legado/` e `documentacao/arquitetura/`.

Limites de módulo no backend (vazios de regra): `identity_organization`, `reference_library`, `ingredient_catalog`, `formula_lab`, `calculation_engine`, `knowledge_grounding`, `compliance`, `technical_documents`, `ai_orchestration`.

## Contrato `GET /health`

```json
{
  "status": "ok",
  "service": "panne",
  "versao": "0.1.0",
  "ambiente": "local"
}
```
