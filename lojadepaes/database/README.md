# Migrações — Loja de Pães

As revisões ficam em `migrations/versions/`. O Alembic lê `LOJADEPAES_DATABASE_URL` (prefixo da API) via `backend/app/core/config.py`. Não há `create_all()` na subida da API.

## Pré-requisito

PostgreSQL acessível na URL do ambiente. Compose de desenvolvimento (projeto Docker `lojadepaes`, porta **5438**, isolado dos outros bancos e do Compose em `phanton/database`):

```powershell
cd C:\Projetos\lojadepaes\database
docker compose up -d
```

Ou aponte `LOJADEPAES_DATABASE_URL` para um PostgreSQL já existente, em um **banco novo** `lojadepaes`. Não use os bancos de Hub, Inove, Panne, PanelDX, Phanton ou SegSense.

## Aplicar

A partir de `database/`, com o venv da API ativo:

```powershell
cd C:\Projetos\lojadepaes\backend
.\.venv\Scripts\Activate.ps1
cd ..\database
$env:PYTHONPATH = (Resolve-Path ..\backend).Path
Copy-Item ..\backend\.env .env -ErrorAction SilentlyContinue
alembic upgrade head
```

Se o `.env` já estiver em `backend\`, o Settings encontra `../.env` quando o cwd é `database/`.

## Criar revisão (quando houver modelos)

```powershell
cd C:\Projetos\lojadepaes\database
$env:PYTHONPATH = (Resolve-Path ..\backend).Path
alembic revision --autogenerate -m "descricao"
alembic upgrade head
```

Revise o arquivo gerado antes de aplicar. Não gere tabelas só para demonstrar o Alembic.

## Seed

Não roda no boot da API. Idempotente (insert se faltar, não sobrescreve texto editorial).

```powershell
cd C:\Projetos\lojadepaes\backend
.\.venv\Scripts\Activate.ps1
python -m app.seed
```

Pedidos só para o painel local (não é agenda comercial; não rode em produção):

```powershell
python -m app.seed.demo_orders
```

O seed principal **não** cria produtos de venda. Fotos de produto ficam em `lojadepaes/var/media/` (não no Postgres).

## Testes de integridade

PostgreSQL isolado `lojadepaes_test` na mesma instância `:5438`. Recusa URL que não contenha `lojadepaes_test` ou que lembre produção.

```powershell
cd C:\Projetos\lojadepaes\backend
.\.venv\Scripts\Activate.ps1
pytest
```


```powershell
alembic current
alembic history
```
