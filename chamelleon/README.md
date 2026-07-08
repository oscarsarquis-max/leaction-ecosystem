# Chamelleon

Monorepo da plataforma Chamelleon: backend Flask, frontend React e PostgreSQL.

## Estrutura

| Diretório   | Descrição                                      |
|-------------|------------------------------------------------|
| `backend/`  | API Python (Flask)                             |
| `frontend/` | Interface React (Vite)                         |
| `database/` | Scripts SQL e migrações                        |

## Pré-requisitos

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+

## Início rápido

```powershell
# Na raiz do projeto Chamelleon
.\start-local.ps1
```

Ou manualmente:

```bash
# Backend (venv próprio do Chamelleon)
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py

# Frontend
cd frontend
npm install
npm run dev
```

Copie `.env.example` para `.env` e `backend/.env`, e ajuste `DATABASE_URL`.
