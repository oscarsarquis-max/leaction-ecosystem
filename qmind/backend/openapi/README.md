# QMind OpenAPI contract

- **Freeze tag (when approved):** `openapi-v1-initial`
- **Committed snapshot:** `openapi.json` (deterministic; do not edit by hand)
- **Source of truth:** FastAPI routes + `app/openapi_contract.py`

## Regenerate

```powershell
cd C:\Projetos\qmind\backend
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe scripts\export_openapi.py
```

## Drift check (CI)

```powershell
.\.venv\Scripts\python.exe scripts\check_openapi_drift.py
# or
pytest -q tests/test_openapi_contract.py
```

## Rules

- Stable unique `operationId` on every operation
- Errors: `ErrorBody` (`code`, `message`, `correlation_id`, `field_errors`)
- Auth: Bearer Cognito (+ local Dev headers documented)
- Tenant: `X-Organization-Id`
- Idempotency: `Idempotency-Key` on create/command ops
- Paths: `/api/v1/**` plus `/health` and `/ready` only
- Examples are synthetic — never real customer data
