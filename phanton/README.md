# Phanton

Ferramenta de Orquestração de Pipeline Multi-Modelo.

## Estrutura

```
phanton/
├── frontend/    # Interface da aplicação
├── backend/     # API e lógica de orquestração
├── services/    # Serviços auxiliares / workers (inclui services/llm/)
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
Em bases já existentes, atualize o schema:

```powershell
cd C:\Projetos\phanton\database
.\apply-schema.ps1
```

### Sync entre máquinas (todas as apps + Phanton)

Na **origem** (esta máquina, antes de ir embora):

```powershell
cd C:\Projetos\infra
.\open-leaction-db-lan.ps1
cd ..\phanton\database
.\open-phanton-db-lan.ps1
```

No **destino** (outra máquina amanhã):

```powershell
cd C:\Projetos
.\sync-db-from-lan.ps1 -SourceHost <IP-LAN-da-origem> -Force
```

## Provedor de IA (LLM plugável)

O motor de inferência é agnóstico de vendor (`services/llm/`). Handlers usam
`LLMFactory` — você troca Google Gemini ↔ Ollama só com variáveis de ambiente.

Configure em `backend/.env` (veja `.env.example`):

| Variável | Default | Descrição |
|----------|---------|-----------|
| `LLM_PROVIDER` | `google` | `google` (Gemini) ou `ollama` (local/soberano) |
| `LLM_MODEL` | conforme provider | Ex.: `gemini-3.5-flash`, `llama3`, `llama3.1` |
| `LLM_BASE_URL` | *(vazio)* | Base do Ollama, ex. `http://127.0.0.1:11434` |
| `GEMINI_API_KEY` | — | Obrigatório se `LLM_PROVIDER=google` |
| `GEMINI_MODEL` | — | Alias legado; usado se `LLM_MODEL` estiver vazio no Google |

Aliases aceitos em `LLM_PROVIDER`: `gemini` → google; `local` → ollama.

Com Google, a fase de pesquisa (`research` / L2) pode usar **Google Search Grounding**.
No Ollama, web search é degradado com `web_search_unsupported` no `meta` (o DAG não quebra).

### Modo soberano / 100% local (Ollama)

1. Instale o [Ollama](https://ollama.com) e baixe um modelo:

```powershell
ollama pull llama3.1
ollama run llama3.1
```

2. Em `backend/.env`:

```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1
LLM_BASE_URL=http://127.0.0.1:11434
```

3. Suba o orquestrador normalmente (backend + frontend). Nenhuma chamada sai para a nuvem de LLM.

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
