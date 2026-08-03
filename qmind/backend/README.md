# QMind backend

DDL v0 e migrações Alembic alinhados ao freeze documental **`domain-docs-v0`**.

Ver: [`../architecture/03_Database/003_DDL_v0.md`](../architecture/03_Database/003_DDL_v0.md).

## Quick start

```powershell
cd C:\Projetos\qmind\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = "postgresql+psycopg://admin:password123@localhost:5433/qmind"
alembic upgrade head
# seeds (catálogos globais — separados da migração)
Get-Content seeds\001_maturity_catalog_v0.sql -Raw | docker exec -i leaction_db psql -U admin -d qmind
Get-Content seeds\002_assessment_model_stub.sql -Raw | docker exec -i leaction_db psql -U admin -d qmind
pytest -q
```
