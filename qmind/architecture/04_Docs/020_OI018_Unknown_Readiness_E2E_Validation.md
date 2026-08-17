# 020 — OI-018 Unknown Readiness E2E Validation

- Status: Completed
- Date: 2026-08-17
- Sprint: **OI-018**
- Result: **PASS** (no code fixes)

## Objetivo

Validar ponta a ponta que `quality_structure = "unknown"` (e `certification_status = "unknown"`) permanece fato armazenado, mas gera lacuna de Context Readiness após OI-017.

## Commits validados

| Componente | Commit | Nota |
|------------|--------|------|
| **qmind-oi** | `5d3bd81` | `fix(readiness): treat unknown context values as missing` |
| **QMind Core** (monorepo `qmind/`) | `58ed5d7` | HEAD com UI/integração OI + nota LIM-OI-016-01 |

## Ambiente

| Peça | Detalhe |
|------|---------|
| Core API | `http://127.0.0.1:8009` |
| OI API | `http://127.0.0.1:8011` (reiniciado com código `5d3bd81`) |
| Postgres | `leaction_db` / `qmind_dev` `:5433` |
| Auth | `AUTH_MODE=dev` |
| Config | `QMIND_OI_BASE_URL=http://127.0.0.1:8011` |

## Cenário principal

Profile inicial:

- campos de contexto preenchidos (`trade_name`, `summary`, `industry`, `business_model`, `employee_range`, `unit_count`)
- `certification_status = "in_progress"`
- **`quality_structure = "unknown"`**

Script: `backend/scripts/smoke_oi018_unknown_readiness.py` (**33/33 PASS**).

## Resultados

### Antes de completar o campo

| Check | Resultado |
|-------|-----------|
| Fato no Core | `quality_structure == "unknown"` (não null / não `""`) |
| Envelope → OI | profile com `"unknown"` |
| Schema | `1.0`; `core_organization_id` = tenant |
| Clause 4 / 7 | lacuna `quality_structure` em `supporting_facts` |
| Summary | “Estrutura responsável pela qualidade” (sem chave técnica) |
| Run 1 | persistido |

### Após PATCH `quality_structure = "formal"`

| Check | Resultado |
|-------|-----------|
| Profile | atualizado para `formal` |
| Run 1 | snapshot intacto; sem run extra no PATCH |
| Stale UI | coberto por Vitest (`oi-analysis-stale`) |

### Após reanálise

| Check | Resultado |
|-------|-----------|
| Run 2 | criado |
| Run 1 | preservado |
| Facts | `quality_structure` ausente |
| Summaries | cláusulas READY (sem lacuna de qualidade) |

### `certification_status = "unknown"`

Smoke técnico: fato preservado; `supporting_facts` contém `certification_status`; summary com “Situação da certificação”.

### Completar → foco

Vitest `OrgIntelligenceContextLoop`: Completar abre edição e foca o campo da lacuna conhecida.

### OI indisponível

Não reexecutado (inalterado desde OI-016; evidência prévia 502 `oi_unavailable`).

## Suítes

| Suite | Resultado |
|-------|-----------|
| OI ruff / mypy / pytest | OK / OK / **73 passed** |
| Core OI + profile pytest | **31 passed** |
| Contract compat | **compatible** |
| FE OI/context Vitest | **10 passed** |
| FE build | OK |

## Bugs

Nenhum **BUG-OI-018-XX**.

## Limitações

- Completar/stale validados por testes de componente + API E2E (sem clique manual no browser nesta sessão).
- OI foi reiniciado antes do smoke para carregar `5d3bd81`.

## Relação com LIM-OI-016-01

Comportamento esperado pós OI-017 confirmado em ambiente integrado.
