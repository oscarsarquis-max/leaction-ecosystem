# 024 — ISO Intelligence V1 — Problem Analysis Integration

- Status: **Implementado (ISOI-003)**
- Date: 2026-08-19
- Sprint: **ISOI-003**
- OI counterpart: `qmind-oi/docs/architecture/010-problem-analysis-4-1-4-4-v1.md`
- Predecessor Core: [`023`](023_ISO_Intelligence_V1_Improvement_Case_Core_Foundation.md)

---

## 1. Objective

Integrate Problem Analysis 4.1/4.4 into ImprovementCase detail:

```text
Case + Profile → ProblemContextInput → OI HTTP → ProblemAnalysis
→ guards → improvement_case_analysis_runs → UI Contexto/Análise
```

No Action Items. Context-OI V1 `/analyze` unchanged.

---

## 2. Input assembly (Core)

`problem_context_builder.build_problem_context_input`:

- org id from `OrgContext`
- case facts from ImprovementCase
- profile facts from Organization Profile
- `source.component = improvement-case-problem-analysis`
- no ISO rules in Core

---

## 3. HTTP

`OrganizationalIntelligenceClient.analyze_problem` →  
`POST {QMIND_OI_BASE_URL}/api/v1/organizational-intelligence/problem-analysis`

Errors: `oi_not_configured`, `oi_timeout`, `oi_unavailable`, `oi_error`, `oi_bad_response`, `oi_invalid_response`.

---

## 4. Guards

Before persist:

- `core_organization_id` == OrgContext org → else `oi_organization_mismatch`
- `improvement_case_id` == path case → else `oi_improvement_case_mismatch`

Failure never inserts a run.

---

## 5. Persistence

Table `improvement_case_analysis_runs` (append-only):

`id, organization_id, improvement_case_id, schema_version, request_id, correlation_id, generated_at, input_fingerprint, analysis jsonb, created_at`

RLS FORCE + tenant policy. Distinct from `organization_intelligence_runs`.

---

## 6. Fingerprint / stale

SHA-256 of canonical JSON: `schema_version` + `organization_profile` + `problem`.  
Excludes request/correlation/timestamps/source/status.

Latest run `is_stale` when fingerprint ≠ current facts. Status-only case change does not stale.

---

## 7. API

```text
POST/GET .../improvement-cases/{case_id}/analysis-runs
GET  .../improvement-cases/{case_id}/analysis-runs/{run_id}
```

Write roles = ImprovementCase write. Reader lists/views only.

---

## 8. UI

`/improvement-cases/:id`: Contexto + Análise funcionais; histórico simples; Ações/Evolução placeholders; disclaimer ISO colapsável.

---

## 9. Limits

No ActionPlan XOR, evidence, evolution, LLM, NC, scores, clauses 5–10 rules.
