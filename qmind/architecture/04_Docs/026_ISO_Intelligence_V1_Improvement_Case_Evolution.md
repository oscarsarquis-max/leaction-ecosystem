# 026 — ISO Intelligence V1 — Improvement Case Evolution

- Status: **Implementado (ISOI-005)**
- Date: 2026-08-19
- Sprint: **ISOI-005**
- Predecessor: [`025`](025_ISO_Intelligence_V1_Finding_to_Action.md)
- OI: **sem alteração** (`qmind-oi` permanece em `2d78eff`)

---

## 1. Objetivo

Fechar o primeiro ciclo utilizável da ISO Intelligence V1:

```text
Problema → Contexto → Análise → Achado → Ação
→ Observação do resultado → Reanálise → Evolução
```

Preservar:

```text
Context torna o problema compreensível.
Intelligence torna o problema tratável.
Evolution verifica se a situação observada mudou.
```

E:

```text
Evolução da gestão ≠ evolução do resultado empresarial.
```

---

## 2. OutcomeObservation (fato declaratório)

Entidade append-only `ImprovementCaseOutcomeObservation` / tabela
`improvement_case_outcome_observations`.

Campos: `id`, `organization_id`, `improvement_case_id`, `result_direction`,
`observation_statement`, `measurement_basis`, `observed_at`, `created_by`,
`created_at`.

### Caráter declaratório

- resultado observado = declaração do usuário;
- status das ações = fato operacional do Core;
- análise OI = snapshot interpretativo;
- comparação de runs = diferença estrutural;
- eficácia **não** é inferida;
- causalidade **não** é confirmada;
- certificação/conformidade fora do escopo.

Preferir: *“A organização registrou melhora após a execução das ações.”*  
Nunca: *“O QMind comprovou que a ação resolveu o problema.”*

### `result_direction`

| Valor | UI |
|-------|-----|
| `improved` | Melhorou |
| `unchanged` | Permaneceu igual |
| `worsened` | Piorou |
| `not_yet_measured` | Ainda não foi medido |

`observed_at` é informado pelo usuário (timezone-aware); não usar `created_at`
silenciosamente.

---

## 3. Persistência

- UUID PK; FK org; FK composta ao ImprovementCase;
- CHECK de `result_direction`;
- textos obrigatórios (trim/non-empty na aplicação);
- índice `(improvement_case_id, observed_at DESC)`;
- RLS ENABLE + FORCE; policy `tenant_isolation`; grants padrão;
- append-only pela aplicação (sem UPDATE/DELETE nesta Sprint).

Não cria indicadores, metas, estatísticas, evidência vinculada ou score.

---

## 4. API de observações

```text
POST /api/v1/organizations/current/improvement-cases/{case_id}/outcome-observations
GET  /api/v1/organizations/current/improvement-cases/{case_id}/outcome-observations
```

POST não aceita org/autor no payload; não altera status do caso, ActionItem,
fingerprint, stale ou analysis run.

GET: mais recente primeiro; lista vazia ok; scoped por org/caso.

---

## 5. Endpoint de evolução (projeção)

```text
GET /api/v1/organizations/current/improvement-cases/{case_id}/evolution
```

Leitura composta **sem** nova fonte de verdade:

```text
ImprovementCaseEvolution
├── case
├── analysis_summary (total_runs, latest, previous, comparison)
├── action_summary (total, by_status, overdue, completed, items, plan)
├── latest_outcome_observation
├── outcome_observations[]
└── closure_readiness
```

---

## 6. Comparação estrutural de runs

Somente snapshots reais do mesmo caso. Identifica findings por `code`.
Missing information e limitations por igualdade exata.

Copy: *“Este ponto não aparece na análise mais recente.”*  
Não: *“Este problema foi resolvido.”*

Com menos de dois runs: `comparison = null`. Sem NLP/LLM.

---

## 7. Resumo de ações

Derivado dos ActionItems do ActionPlan do caso. Contagens por status existente;
vencidas/`completed` conforme lifecycle atual. Ação concluída ≠ ação eficaz.

---

## 8. Closure readiness

Orientação operacional (não score / não conformidade):

- `insufficient_information` — sem análise; análise stale; sem ação; ações
  não terminais; sem observação; ou última observação `not_yet_measured`.
- `ready_for_review` — análise atual não stale; ≥1 ação; todas terminais
  (`done` | `cancelled` | `ineffective_closed`); observação medida
  (≠ `not_yet_measured`).

Significa apenas: há elementos suficientes para o usuário **revisar**.

---

## 9. Lifecycle e decisão humana

Transições existentes preservadas. Nenhuma mudança automática de status.
UI:

- `ready_for_review` + status `acting` → “Colocar em revisão”;
- status `reviewing` → “Encerrar” com disclaimer;
- observação nova **não** reabre caso encerrado.

---

## 10. Fingerprint / stale

Registrar OutcomeObservation **não** altera fingerprint nem torna análise stale.
Alterar ActionItem idem. Fatos do problema/Profile seguem ISOI-003.

---

## 11. Autorização / tenancy

Mesmas roles de gerenciamento do ImprovementCase para criar observação.
Reader: visualiza evolução/observações; não registra; não altera status.
OrgContext + RLS + `X-Organization-Id` + query keys com organizationId +
`requestGeneration`.

---

## 12. UI

Seção Evolução no detalhe do caso: Situação; Resultado observado; Comparação;
Ações e revisão.

---

## 13. Limitações desta Sprint

Sem indicadores estruturados, metas, dashboards, inferência de eficácia,
causalidade, reanálise automática, fechamento automático, evidência vinculada,
event sourcing, score, conformidade, NC, LLM, Fit/Pain/Journey.

---

## 14. Testes

Backend: migration/RLS, direções, validação, append-only, reader, cross-tenant,
evolução/comparação/closure matrix, fingerprint/stale intactos, OpenAPI.
Frontend: vazio, reader, formulário, histórico, comparação, stale, closure CTAs,
disclaimer, tenant guard. Typecheck/build.

---

## 15. Recomendação de fechamento da ISO Intelligence V1

Com ISOI-002…005, o ciclo vertical Context → Intelligence → Action → Evolution
está utilizável no Core.

**Fechamento formal:** [`027_ISO_Intelligence_V1_Improvement_Case_Loop_Baseline.md`](027_ISO_Intelligence_V1_Improvement_Case_Loop_Baseline.md) (ISOI-006).
