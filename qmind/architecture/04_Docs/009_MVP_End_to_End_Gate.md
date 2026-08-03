# QMind â€” Gate MVP ponta a ponta (domÃ­nio)

- Status: **APROVADO** (2026-08-03)
- PrÃ©-requisito: freeze `domain-docs-v0` + Report publicado (`33fd366`) + Gate Fase 0 (`008_Phase0_Technical_Gate.md`)
- Suite: `../../backend/tests/test_mvp_e2e_gate.py` (PostgreSQL real, `STORAGE_BACKEND=memory`)
- Variante S3: `../../backend/tests/test_mvp_e2e_s3_integration.py` (`pytest -m integration`, opt-in)
- Nomenclatura: database lÃ³gico **`qmind`** Â· cluster/serviÃ§o **`leaction_db`** (`localhost:5433`)

## 1. Jornada validada

```
Organization/Membership
â†’ Assessment.draft â†’ scope/team â†’ plan â†’ start
â†’ Evidence.approved
â†’ Finding.approved
â†’ ActionPlan/ActionItem.done
â†’ MaturityAssessment.approved
â†’ Report.published
â†’ Assessment.closed
â†’ Assessment.reopened
â†’ novo Report.published
â†’ versÃ£o anterior superseded
```

Caminho separado: `Assessment.closed` com **dispensa formal** (`close_waiver_reason`) sem Report publicado.

## 2. Checklist do gate

| # | CritÃ©rio | EvidÃªncia | Resultado |
|---|---|---|---|
| E1 | PapÃ©is e SoD em cada aprovaÃ§Ã£o | Finding / Maturity / ActionItem / Report: autor â‰  aprovador (403 `sod_violation`) | PASS |
| E2 | Tentativa cruzada org B em cada agregado crÃ­tico | API 404 em Assessment, Evidence, Finding, Maturity, ActionPlan, Report, Job | PASS |
| E3 | RLS leitura/escrita | `qmind_app` + `app.organization_id`: count=0 para IDs da org A sob contexto B (incl. `platform_audit_events`) | PASS |
| E4 | Snapshots imutÃ¡veis | TÃ­tulo do Finding alterado apÃ³s publish; JSON do Report permanece o original | PASS |
| E5 | VersÃ£o corrente Ãºnica | `count(*) WHERE status='published'` = 1 antes e depois do supersede | PASS |
| E6 | Cadeia de auditoria e correlaÃ§Ã£o | AÃ§Ãµes de create/approve/publish/close/reopen/supersede presentes; `correlation_id` NOT NULL; reopen com `reinforced` + `preserved_report_ids` | PASS |
| E7 | IdempotÃªncia upload / publish / Job | PUT retry-safe + receive status-guard; publish repetido â†’ published; `export-pdf` retorna mesmo `job.id` | PASS |
| E8 | Reabertura preserva histÃ³rico | Report v1 permanece `published` apÃ³s reopen; sÃ³ supersede ao publicar v3 | PASS |
| E9 | Fechamento com relatÃ³rio e com dispensa | Path principal: close apÃ³s publish; path waiver: QM + motivo nÃ£o vazio + audit | PASS |
| E10 | Rollback transacional em falha induzida | Falha em `report.publish` apÃ³s supersede in-tx â†’ v1 continua `published`, draft permanece `in_review` | PASS |
| E11 | Prod sem AUTH_MODE=dev / seguranÃ§a simulada / memory | `Settings(environment=prod, â€¦)` rejeita dev auth, `ALLOW_SIMULATED_SECURITY_PASS=true` e `STORAGE_BACKEND=memory` | PASS |
| E12 | Duas organizaÃ§Ãµes simultÃ¢neas | Org A jornada completa; Org B com Assessment prÃ³prio + denials contÃ­nuos; cleanup admin determinÃ­stico ao fim | PASS |

## 3. Ambiente da execuÃ§Ã£o

| Item | Valor |
|---|---|
| Data/hora | 2026-08-03 (~11:20 -03:00) |
| Commit base (domÃ­nio Report) | `33fd366` â€” `feat(qmind): add versioned report publication workflow` |
| Commit deste gate (testes + doc) | ver `git log -1` apÃ³s push deste documento |
| Database | `qmind` @ `localhost:5433` (Docker `leaction_db`) |
| Alembic head | `20260803_0005` |
| App role | `qmind_app` (FORCE RLS) |
| Auth nos testes | `AUTH_MODE=dev` + headers (somente local; proibido em `ENVIRONMENT=prod`) |
| Storage suÃ­te normal | `STORAGE_BACKEND=memory` |
| Storage integraÃ§Ã£o | S3 real via `QMIND_S3_INTEGRATION=1` (desselecionado por padrÃ£o) |

## 4. Resultado dos testes

```text
pytest -q
74 passed, 2 deselected, 13 warnings
```

- Desselecionados: `integration` â€” `test_storage_s3_integration.py`, `test_mvp_e2e_s3_integration.py`
- Gate E2E: `tests/test_mvp_e2e_gate.py` â€” **4 passed**
  - `test_mvp_end_to_end_two_orgs_memory`
  - `test_mvp_close_with_formal_waiver`
  - `test_mvp_prod_config_forbids_dev_auth_and_simulated_security`
  - `test_mvp_alembic_head_is_0005`

### Isolamento (evidÃªncias)

- API: org B recebe **404** ao GET/POST nos IDs da org A (Assessment, Evidence, Finding, Maturity, ActionPlan, Report, export-pdf).
- SQL RLS: sob `set_config('app.organization_id', org_b)` â†’ `count(*)=0` para linhas da org A em `assessments`, `evidences`, `findings`, `maturity_assessments`, `action_plans`, `action_items`, `reports`, `jobs`, `platform_audit_events`.
- FORCE RLS confirmado em `assessments`, `evidences`, `findings`, `reports`, `jobs`, `platform_audit_events` (`relrowsecurity=true`, `relforcerowsecurity=true`).
- Auditoria de reopen: metadata `{"reinforced": true, "preserved_report_ids": [...]}`.

### Variante S3

```powershell
cd C:\Projetos\qmind\backend
$env:QMIND_S3_INTEGRATION = "1"
$env:STORAGE_BACKEND = "s3"
# S3_BUCKET + credenciais AWS
pytest -q -m integration tests/test_mvp_e2e_s3_integration.py
```

NÃ£o executada nesta rodada (opt-in; sem bucket no ambiente local do gate).

## 5. Veredito

**APROVADO** â€” fundaÃ§Ã£o do MVP de domÃ­nio pronta para o prÃ³ximo ciclo:

1. API OpenAPI consolidada  
2. Interface React  
3. Piloto controlado  

## 6. Como reexecutar

```powershell
cd C:\Projetos\qmind\backend
$env:PYTHONPATH = "C:\Projetos\qmind\backend"
$env:STORAGE_BACKEND = "memory"
$env:ALLOW_SIMULATED_SECURITY_PASS = "true"
$env:AUTH_MODE = "dev"
$env:ENVIRONMENT = "local"
.\.venv\Scripts\python.exe -m pytest -q tests/test_mvp_e2e_gate.py
.\.venv\Scripts\python.exe -m pytest -q
```
