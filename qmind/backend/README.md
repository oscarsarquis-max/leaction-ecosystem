# QMind backend

- **Database lógico:** `qmind`
- **Cluster/serviço:** `leaction_db` (`localhost:5433`)
- Freeze de domínio: **`domain-docs-v0`**
- Gate Fase 0: `scripts/gate_phase0.ps1` → `../architecture/04_Docs/008_Phase0_Technical_Gate.md`

## Roles de banco

| Uso | Role | Notas |
|---|---|---|
| Migrações Alembic / seeds | owner (`admin` local) | Único com DDL |
| Runtime tenant (API) | **`qmind_app`** | Sem ownership, sem `BYPASSRLS`, FORCE RLS |
| Bootstrap identidade (user/membership) | admin URL | Só upsert/listagem cross-org; dados de negócio via `qmind_app` |

## Quick start

```powershell
cd C:\Projetos\qmind\backend
copy .env.example .env   # preencher credenciais locais; nunca commitar .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = $env:DATABASE_URL_ADMIN
alembic upgrade head
Get-Content seeds\001_maturity_catalog_v0.sql -Raw | docker exec -i leaction_db psql -U admin -d qmind
Get-Content seeds\002_assessment_model_stub.sql -Raw | docker exec -i leaction_db psql -U admin -d qmind
uvicorn app.main:app --reload --port 8008
```

`AUTH_MODE=dev` é **proibido** com `ENVIRONMENT=prod` (falha na carga de settings). Em local: headers `X-Dev-User-Sub`, `X-Dev-User-Email`; rotas tenant exigem `X-Organization-Id` validado contra Membership ativa.

## Testes

```powershell
pytest -q
# Gate completo DDL:
.\scripts\gate_phase0.ps1
```
