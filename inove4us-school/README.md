# inove4us School — Torre de Controle B2B
#
# Aplicação **independente** do inove4us (B2C professores).
# Subdomínio previsto: school.inove4us.com.br (a definir).
# Stack alinhada à família inove4us: React + Vite | Flask | PostgreSQL dedicado.

## Stack

| Camada | Tecnologia | Porta local |
|--------|------------|-------------|
| Frontend | React 18 + Vite | `5175` |
| Backend | Flask | `5012` |
| Banco | PostgreSQL `inove4us_school` (container `leaction_db`) | host `5434` (ou a porta do seu `leaction_db`) |

## Princípio

- **Zero import** de código do `inove4us/` B2C
- Tabelas somente com prefixo `school_*`
- Banco **separado** — não misturar com o DB `inove4us` dos professores
- Comunicação futura com B2C: **API / contratos**, nunca FK cross-database

Ver arquitetura: [`README_ARCHITECTURE.md`](./README_ARCHITECTURE.md)

## Bootstrap DB

```powershell
cd C:\Projetos\leaction-ecosystem\inove4us-school\infra\scripts
.\bootstrap-db.ps1
```

## Dev local

```powershell
# 1) API
cd C:\Projetos\leaction-ecosystem\inove4us-school
copy .env.example .env   # ajuste DB_PORT se necessário
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py

# 2) UI (outro terminal)
cd C:\Projetos\leaction-ecosystem\inove4us-school\frontend
npm install
npm run dev
```

- UI: http://localhost:5175  
- Health: http://localhost:5012/api/health  

## Migrations

```text
infra/db/migrations/001_school_b2b_schema.sql
infra/db/migrations/001_school_b2b_schema.down.sql
```

## Escopo no monorepo

Pasta raiz: `inove4us-school/`. Desacoplada de `inove4us/`. Não editar o B2C ao evoluir esta app.
