# 023 — ISO Intelligence V1 — Improvement Case Core Foundation

- Status: **Implementado (ISOI-002)**
- Date: 2026-08-19
- Sprint: **ISOI-002**
- Predecessor: [`022_ISO_Intelligence_V1_Improvement_Case_Inspection.md`](022_ISO_Intelligence_V1_Improvement_Case_Inspection.md) (**Aprovado**)
- Baseline intacta: Context-OI V1 ([`021`](021_Context_OI_V1_Baseline.md))

Fundação mínima do agregado `ImprovementCase` no QMind Core. **Não** implementa interpretação OI.

---

## 1. Objetivo

Permitir que um usuário autorizado:

1. registre um problema empresarial;
2. informe impacto e processo relacionado;
3. liste e abra o detalhe na organização corrente;
4. edite fatos básicos;
5. altere status por transições válidas;
6. mantenha isolamento total entre organizações.

Preservar:

```text
Context Readiness != ISO Conformity
Facts belong to Core.
Interpretation belongs to OI.
```

---

## 2. Modelo

Tabela `improvement_cases`:

| Campo | Notas |
|-------|--------|
| `id` | UUID (backend) |
| `organization_id` | FK; **somente** de `OrgContext` |
| `problem_statement` | texto obrigatório (trim, max 4000) |
| `impact_statement` | texto obrigatório |
| `related_process` | texto obrigatório (sem catálogo) |
| `status` | `open` \| `analyzing` \| `acting` \| `reviewing` \| `closed` |
| `created_by` | usuário autenticado |
| `created_at` / `updated_at` | timestamptz |

Semântica: fatos declarados + decisão operacional de estado. **Não** é NC, conformidade, causa raiz, finding OI ou maturidade.

---

## 3. Lifecycle

Estado inicial: `open`.

```text
open → analyzing
analyzing → open | acting
acting → analyzing | reviewing
reviewing → acting | closed
closed → reviewing
```

Transições inválidas → `409 invalid_transition`. Sem automação silenciosa. Encerramento = `closed` (sem DELETE).

---

## 4. API

Prefixo organization-scoped:

```text
POST   /api/v1/organizations/current/improvement-cases
GET    /api/v1/organizations/current/improvement-cases
GET    /api/v1/organizations/current/improvement-cases/{case_id}
PATCH  /api/v1/organizations/current/improvement-cases/{case_id}
```

- POST: body = três textos; backend define org, status `open`, autor, timestamps.
- GET coleção: org corrente, `ORDER BY updated_at DESC`.
- GET detalhe / PATCH: 404 se outro tenant (indistinguível de inexistente).
- PATCH: fatos + `status`; imutáveis: id, org, created_by, created_at.

Módulo: `backend/app/modules/improvement_cases/`.

---

## 5. Autorização

Reutilizada a escrita do **Organization Profile PATCH**:

```text
org_admin, consultant_auditor, quality_manager, platform_admin
```

Leitura: mesmos papéis de leitura organizacional (+ `reader`, `process_owner`, `action_owner`). Sem role nova.

UI: `canManageImprovementCases` / `canReadImprovementCases`.

---

## 6. Tenancy / RLS

- `OrgContext` + `X-Organization-Id`
- `tenant_connection(organization_id)`
- RLS `ENABLE` + `FORCE`; policy `tenant_isolation` via `qmind_app.current_organization_id()`
- Grants a `qmind_app`
- FE: query keys com `organizationId` + `requestGeneration`; descarte de respostas stale

---

## 7. UI

| Superfície | Comportamento |
|------------|---------------|
| Hub `/assessments` | Seção independente **Problemas em acompanhamento** |
| Vazio | “Nenhum problema está sendo acompanhado.” + “Registrar problema” se autorizado |
| Criação | Três perguntas de negócio (problema / impacto / processo) |
| Lista | problema, impacto, processo, status humanizado, atualização, Abrir |
| Detalhe `/improvement-cases/:id` | fatos, editar, transições; seções futuras honestas |

Copy de status: Aberto / Em análise / Em tratamento / Em revisão / Encerrado.

Sem linguagem de conformidade / certificação / NC.

---

## 8. Limites (fora de ISOI-002)

Não implementado:

- `ProblemContextInput` / `ProblemAnalysis` (qmind-oi intacto)
- ActionPlan XOR
- tabela de analysis runs
- Evidence / Action Item por caso
- readiness / stale / reanálise por caso
- catálogo de processos, scores, causa raiz

---

## 9. Testes

- Backend: `backend/tests/test_improvement_cases.py` (CRUD, whitespace, org do contexto, transitions, reader, A/B, RLS SQL, OpenAPI).
- Frontend: `web/src/components/OrgImprovementCasesPanel.test.tsx` (vazio, reader, criação, detalhe, status, copy; tenant switch no hook).

---

## 10. Relação com ISOI-001

ISOI-001 recomendou agregado Core + pipeline OI futuro. ISOI-002 executa **somente** a fundação Core alinhada a D1–D5.

---

## 11. Próximo incremento (ISOI-004 — não iniciado)

ActionPlan XOR `assessment_id` | `improvement_case_id` e criação de Action Items a partir de achados aceitos; Evolução do caso.

---

## Continuidade ISOI-003

Integração Problem Analysis documentada em [`024_ISO_Intelligence_V1_Problem_Analysis_Integration.md`](024_ISO_Intelligence_V1_Problem_Analysis_Integration.md).
