# Phanton

Ferramenta de Orquestração de Pipeline Multi-Modelo.

## Estrutura

```
phanton/
├── frontend/    # Interface da aplicação
├── backend/     # API e lógica de orquestração
├── services/    # Serviços auxiliares / workers
└── database/    # PostgreSQL local (Docker) e schema
```

## Banco de dados (local)

Credenciais padrão:

| Campo    | Valor         |
|----------|---------------|
| Host     | `localhost`   |
| Porta    | `5435` (host → 5432 no container) |
| User     | `postgres`    |
| Password | `password`    |
| Database | `orquestrador`|

Subir o PostgreSQL 15:

```powershell
cd C:\Projetos\phanton\database
docker compose up -d
```

O script `01_init.sql` é aplicado automaticamente na primeira inicialização do volume.

## Gemini (Fase L2 — Grounding)

1. Em `backend/.env`, defina `GEMINI_API_KEY` (há um placeholder em `.env.example`).
2. Modelo padrão: `gemini-3.5-flash` (suporta Google Search Grounding). Opcional: `GEMINI_MODEL`.

A fase L2 deixa de usar mock e chama o Gemini com `tools=[google_search]`.

## Backend (FastAPI)

```powershell
cd C:\Projetos\phanton\backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Health check: `GET http://127.0.0.1:8000/health`

## Frontend (Vite + React)

```powershell
cd C:\Projetos\phanton\frontend
npm run dev
```

Abra `http://localhost:5175` (porta dedicada; 5173 fica com o inove4us). O dashboard faz polling em `GET /api/pipeline/{run_id}` a cada 3s.
