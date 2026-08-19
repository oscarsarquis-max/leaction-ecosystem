# 025 — ISO Intelligence V1 — Finding to Action

- Status: **Implementado (ISOI-004)**
- Date: 2026-08-19
- Sprint: **ISOI-004**
- Predecessor: [`024`](024_ISO_Intelligence_V1_Problem_Analysis_Integration.md)
- OI: **sem alteração**

---

## 1. Objetivo

Transformar recomendação de achado OI em ActionItem operacional, com decisão humana explícita e rastreabilidade ao run/finding imutáveis.

```text
ProblemAnalysis (snapshot)
  → decisão humana (owner + due)
  → ActionPlan(improvement_case_id)
  → ActionItem(source_analysis_run_id, source_finding_code)
```

---

## 2. Decisão humana

Recomendação OI **não** cria ação. Somente `POST …/findings/{code}/actions` após confirmação. Existência do ActionItem = recomendação aceita/operacionalizada. Sem rejeição nesta V1.

---

## 3. ActionPlan XOR

```text
(assessment_id NOT NULL AND improvement_case_id IS NULL)
OR
(assessment_id IS NULL AND improvement_case_id NOT NULL)
```

CHECK `ck_action_plans_origin_xor`. Planos Assessment existentes preservados (`assessment_id` tornou-se nullable; dados antigos válidos). Um plano por ImprovementCase (`uq_action_plans_improvement_case`).

---

## 4. Rastreabilidade

ActionItem:

- `source_analysis_run_id` + `source_finding_code` (ambos nulos **ou** ambos preenchidos)
- Unique parcial `(org, run, code)` quando preenchidos
- Texto derivado do snapshot no backend; run imutável

---

## 5. Idempotência

Duplicata → `409 finding_action_exists`. Índice único + checagem prévia.

---

## 6. API

```text
POST …/improvement-cases/{case_id}/analysis-runs/{run_id}/findings/{finding_code}/actions
GET  …/improvement-cases/{case_id}/actions
```

Body: `owner_membership_id`, `due_at` apenas.

---

## 7. Autorização

Criação: `org_admin` | `consultant_auditor` | `quality_manager` (interseção case write ∩ action create). Reader: só leitura.

---

## 8. UI

Achado → Criar ação (form RO + owner/prazo) → Ação criada; seção Ações lista itens; link origem run/finding.

---

## 9. Stale

Criar/alterar ActionItem **não** altera fingerprint/stale da análise.

---

## 10. Continuidade (ISOI-005)

Evolução do caso (OutcomeObservation + projeção de evolução):  
[`026_ISO_Intelligence_V1_Improvement_Case_Evolution.md`](026_ISO_Intelligence_V1_Improvement_Case_Evolution.md).
