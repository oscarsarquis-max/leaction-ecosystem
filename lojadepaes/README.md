# Loja de Pães

Prévia da experiência **Despertar do Levain**. Protótipo navegável para criar uma combinação de pão; agendamento e pedido são demonstrativos. O domínio `lojadepaes.com.br` está em transição para a AWS — DNS e publicação ficam para outra etapa.

Aplicação em `C:\Projetos\lojadepaes`. O assistente na vitrine continua demonstrativo (não grava pedido). Há modelo de pedidos e fronteira financeira para o ActionHub, sem cobrança real.

## Stack

| Pasta | Responsabilidade |
|---|---|
| `frontend/` | React + TypeScript + Vite (porta **5175**). Responsividade permanente a partir de 320 px. |
| `backend/` | FastAPI + SQLAlchemy 2 (porta **5075**, prefixo `/api/v1`) |
| `database/` | Alembic e Compose do PostgreSQL de desenvolvimento (porta **5438**) |
| `services/` | Reserva para integrações futuras — vazia nesta etapa |
| `readme/` | Arquitetura e fluxo de desenvolvimento |

## Pré-requisitos

- Node.js 20+ e npm
- Python 3.12+
- Docker Desktop, **ou** um PostgreSQL acessível (banco novo `lojadepaes`)

## Instalação (PowerShell)

```powershell
cd C:\Projetos\lojadepaes\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env

cd C:\Projetos\lojadepaes\frontend
npm install
Copy-Item .env.example .env
```

## Variáveis de ambiente

Não versione `.env`. Exemplos:

- `backend/.env.example` — `LOJADEPAES_DATABASE_URL`, `LOJADEPAES_TEST_DATABASE_URL`, fuso `LOJADEPAES_BAKERY_TIMEZONE`, CORS, host/porta
- `readme/data-model.md`, `readme/business-rules.md`, `readme/actionhub-integration.md`, `readme/admin-products.md`
- `frontend/.env.example` — `VITE_API_BASE_URL` (só URL pública da API; nada de senha)

A loja continua navegável se a API estiver fora do ar. A UI **não** usa `/health` nem `/ready` para banners.

## Subir localmente

PostgreSQL próprio (não reutiliza `:5432`/`:5433` de outras apps):

```powershell
cd C:\Projetos\lojadepaes\database
docker compose up -d
```

Migrações (baseline vazio, sem tabelas de negócio):

```powershell
cd C:\Projetos\lojadepaes\backend
.\.venv\Scripts\Activate.ps1
cd ..\database
$env:PYTHONPATH = (Resolve-Path ..\backend).Path
alembic upgrade head
```

API e frontend, em dois terminais:

```powershell
cd C:\Projetos\lojadepaes\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 5075
```

```powershell
cd C:\Projetos\lojadepaes\frontend
npm run dev
```

| Superfície | Endereço |
|---|---|
| Loja | http://127.0.0.1:5175 |
| Gestão de pedidos | http://127.0.0.1:5175/admin/pedidos |
| Gestão de produtos | http://127.0.0.1:5175/admin/produtos |
| Agenda de fornadas | http://127.0.0.1:5175/admin/agenda |
| API health | http://127.0.0.1:5075/api/v1/health |
| API ready | http://127.0.0.1:5075/api/v1/ready |
| PostgreSQL | `127.0.0.1:5438` (usuário/banco `lojadepaes`) |

Alternativa sem Docker: crie o banco `lojadepaes` num PostgreSQL já instalado e ajuste `LOJADEPAES_DATABASE_URL`. Não aponte para os bancos de Hub, Inove, Panne, PanelDX, Phanton ou SegSense.

## Lint, tipos, testes e build

```powershell
cd C:\Projetos\lojadepaes\backend
.\.venv\Scripts\Activate.ps1
ruff check app tests
pytest

cd C:\Projetos\lojadepaes\frontend
npm run lint
npm run typecheck
npm test
npm run build
```

## Migrações

Ver `database/README.md`. Comandos a partir de `database/` com `PYTHONPATH` no `backend`. Não há `create_all()` na API.

Seed demonstrativo (não sobe com a API; só `LOJADEPAES_ENV` local/development/test/demo):

```powershell
cd C:\Projetos\lojadepaes\backend
.\.venv\Scripts\Activate.ps1
python -m app.seed
```

Pedidos de demonstração (opcional, só para ver o painel; não preenche operação real). Referências `DEMO-*`, cliente `demo@example.test`, fornada `DEMO-NAO-COMERCIAL` fechada. Não inventa preço comercial:

```powershell
python -m app.seed.demo_orders
```

## Gestão

O login fica no cabeçalho da vitrine (campos Login, Senha e Entrar). Não use uma página separada. O atalho antigo http://127.0.0.1:5175/admin/login volta para a vitrine e foca o formulário.

Editor de produtos: http://127.0.0.1:5175/admin/produtos

Pedidos: http://127.0.0.1:5175/admin/pedidos

Agenda: http://127.0.0.1:5175/admin/agenda

Sem conta local, a API administrativa responde **503**. Não há senha padrão. No servidor, configure o primeiro administrador (entrada oculta; o comando grava só o hash e o segredo no `.env`, que permanece fora do Git):

```powershell
Set-Location C:\Projetos\lojadepaes\backend; & .\.venv\Scripts\Activate.ps1; python -m app.admin
```

Reinicie a API (`uvicorn app.main:app --reload --host 127.0.0.1 --port 5075`) para ler a configuração. Para substituir uma conta já existente, o comando pede a palavra `SUBSTITUIR` ou aceite `--replace`.

Guia curto do editor: `readme/admin-products.md`.

Sessão em cookie `HttpOnly` + CSRF no cabeçalho `X-CSRF-Token`. Logout invalida a sessão no Postgres. Em HTTPS de implantação, `LOJADEPAES_COOKIE_SECURE=true`.

Testes de integridade usam o banco isolado `lojadepaes_test` (`LOJADEPAES_TEST_DATABASE_URL`).

## O que permanece demonstrativo

- Assistente de quatro etapas (massa, inclusões, formato, calendário) — não grava pedido
- Mural editorial e biblioteca do padeiro
- Seleção de pães padrão no navegador, sem checkout, cobrança ActionHub, reserva de fornada, receitas (virão do Panne) ou contas de cliente

O protótipo vanilla original está em `frontend/prototype/`. Logo oficial: `frontend/images/lojadepaeslogo.png`.
