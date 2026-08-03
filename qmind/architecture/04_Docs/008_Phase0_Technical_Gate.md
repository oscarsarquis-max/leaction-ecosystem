# QMind — Gate técnico Fase 0 (pré-API)

- Status: **APROVADO** (2026-08-03)
- Pré-requisito: freeze `domain-docs-v0` + DDL v0 (`003_DDL_v0.md`) + emenda `007`
- Script: `../../backend/scripts/gate_phase0.ps1`
- Nomenclatura: database lógico **`qmind`** · cluster/serviço **`leaction_db`**

## 1. Nomenclatura (confirmação)

| Nome | Papel |
|---|---|
| `qmind` | **Base lógica dedicada** (PostgreSQL database) |
| `leaction_db` | **Serviço/cluster** Postgres compartilhado do monorepo |
| schema `public` / `qmind_app` | Objetos da base `qmind` apenas — helpers em `qmind_app` |

Não usar `leaction_db` como sinônimo de database da aplicação.

## 2. Checklist do gate

| # | Critério | Evidência | Resultado |
|---|---|---|---|
| G1 | Migração desde banco vazio | `DROP/CREATE DATABASE qmind` + `alembic upgrade head` | _(preencher pelo script)_ |
| G2 | Execução repetida sem efeitos indevidos | segundo `alembic upgrade head` = no-op (já em head) | _ |
| G3 | Downgrade / rollback documentado | `alembic downgrade base` + re-upgrade **ou** procedimento em §3 | _ |
| G4 | App user sem ownership nem BYPASSRLS | `qmind_app`: not superuser, not bypassrls; tables owned by `admin` | _ |
| G5 | FORCE RLS ou separação segura do owner | `relforcerowsecurity = true` nas tabelas tenant | _ |
| G6 | Backup e restauração do esquema | `pg_dump -s` + restore em DB temporário | _ |
| G7 | Isolamento R/W/U/D entre 2 orgs | `pytest` (incl. CRUD) | _ |
| G8 | Seeds em ambiente limpo | seeds após migrate em DB recém-criado; reaplicação idempotente | _ |

## 3. Rollback documentado

### Preferido (dev / vazio)

```powershell
cd C:\Projetos\qmind\backend
$env:DATABASE_URL = "postgresql+psycopg://admin:password123@localhost:5433/qmind"
alembic downgrade base
alembic upgrade head
```

`downgrade` da revisão `20260803_0001` remove tabelas/schema/role `qmind_app` (destrutivo — só em ambientes sem dados de cliente).

### Alternativa operacional

1. `pg_dump -Fc -d qmind -f qmind_prechange.dump` (antes de migrar).
2. Em falha: `DROP DATABASE qmind; CREATE DATABASE qmind; pg_restore -d qmind qmind_prechange.dump`.



## 4. Resultado do gate (ultima execucao)

- Data/hora: 2026-08-03 10:25:15 -03:00
- Executor: gate_phase0.ps1
- **Veredito:** `APROVADO`
- Notas:
  - G1: PASS - upgrade head on empty DB -> 20260803_0001
  - G2: PASS - second upgrade head OK (no-op)
  - G8: PASS - seeds clean+reapply OK (criteria=18 models=1)
  - G4: PASS - qmind_app no super/bypass; owner=admin
  - G5: PASS - FORCE RLS on assessments
  - G7: PASS - pytest isolation CRUD OK
  - G6: PASS - pg_dump -s restore OK
  - G3: PASS - downgrade base removed tables; re-upgrade OK

## 5. Pós-gate

Com veredito **APROVADO**, iniciar fundação FastAPI: config, pool `qmind`, contexto de organização, Cognito OIDC, health, módulo Organization/Membership.


