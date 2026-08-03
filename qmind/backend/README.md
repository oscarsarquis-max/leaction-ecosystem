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

## Evidências (ADR-007)

- Adaptador: `STORAGE_BACKEND=memory|s3` (`app/storage/`)
- Produção: bucket **privado dedicado** em `us-east-2` (`S3_BUCKET`), chaves `org/{organization_id}/evidence/{evidence_id}/v{n}`
- `authorize` emite URL pré-assinada; `receive` confirma via **HEAD** + hash (não confia no cliente)
- `ALLOW_SIMULATED_SECURITY_PASS` pode ser `true` fora de prod até existir worker de quarentena; **proibido** com `ENVIRONMENT=prod`

```powershell
alembic upgrade head   # inclui upload_expires_at
```

## Contrato OpenAPI

- Snapshot determinístico: `openapi/openapi.json` (não editar à mão)
- Export: `python scripts/export_openapi.py`
- Drift CI: `python scripts/check_openapi_drift.py` ou `pytest tests/test_openapi_contract.py`
- Freeze: tag **`openapi-v1-initial`** (após aceite deste contrato)

## Testes

```powershell
pytest -q
# Gate completo DDL:
.\scripts\gate_phase0.ps1
```

Integração S3 real (opcional, desmarcada por padrão): ver `docs/S3_INTEGRATION_TESTS.md`.
