# 027 — ISO Intelligence V1 — Improvement Case Loop Baseline

- Status: **Baseline**
- Date: 2026-08-19
- Activity: **ISOI-006**
- Name: **ISO Intelligence V1 — Improvement Case Loop**
- Predecessor docs: [`021`](021_Context_OI_V1_Baseline.md) … [`026`](026_ISO_Intelligence_V1_Improvement_Case_Evolution.md)
- OI counterpart: `qmind-oi/docs/architecture/010-problem-analysis-4-1-4-4-v1.md`

Documento operacional de **fechamento** da primeira baseline vertical problema → contexto → análise → ação → observação → evolução → revisão/encerramento humano. **Não** altera comportamento de produto.

---

## 1. Propósito

Declarar formalmente o que constitui a baseline, pins exatos, capacidades, limites semânticos, configuração operacional e evidência de validação — para impedir expansão por inércia.

---

## 2. Tese: problema primeiro

O QMind organiza a inteligência ISO a partir de um **problema empresarial declarado**, não a partir de um checklist de conformidade.

```text
Context torna o problema compreensível.
Intelligence torna o problema tratável.
Evolution verifica se a situação observada mudou.
```

```text
Evolução da gestão ≠ evolução do resultado empresarial.
```

---

## 3. Nome e definição

**Nome:** ISO Intelligence V1 — Improvement Case Loop

**Definição:** primeira capacidade vertical do QMind que parte de um problema empresarial declarado, organiza seu contexto, produz interpretação determinística com fundamentação limitada em ISO 9001 4.1/4.4, permite converter recomendação em ação por decisão humana, registra resultado observado e preserva histórico para revisão e encerramento humano.

---

## 4. Pins (commits)

| Lado | Commit | Mensagem |
|------|--------|----------|
| **QMind Core** (código funcional da baseline) | `f189a11` | `feat(improvement-cases): track observed outcomes and evolution` |
| **QMind Core** (fechamento documental ISOI-006) | `338f44e` | `docs(iso-intelligence): establish improvement case loop v1 baseline` |
| **qmind-oi** (código funcional da baseline) | `2d78eff` | `feat(intelligence): analyze improvement case context` |
| **qmind-oi** (pointer documental ISOI-006) | `1bba6b3` | `docs(arch): link ISO Intelligence V1 baseline` |

HEADs após ISOI-006 incluem commits **somente documentais** além dos pins funcionais acima. O pin de comportamento permanece `f189a11` (Core) e `2d78eff` (OI).

### Commits funcionais incluídos (Core)

| Commit | Papel |
|--------|--------|
| `2013aa1` | ImprovementCase lifecycle + hub/detalhe |
| `cf57a1d` | Integração Problem Analysis + runs/fingerprint/stale |
| `15a6ae3` | Finding → Action + ActionPlan XOR |
| `f189a11` | OutcomeObservation + Evolution |

### Context-OI V1 (baseline anterior, independente)

Pins históricos em [`021`](021_Context_OI_V1_Baseline.md). Preservada integralmente; contratos `/analyze` intactos.

---

## 5. Arquitetura Core ↔ OI

```text
ImprovementCase + Organization Profile (Core)
        ↓ ProblemContextInput v1.0
HTTP POST /api/v1/organizational-intelligence/problem-analysis (OI)
        ↓ ProblemAnalysis v1.0
guards org/case → improvement_case_analysis_runs (append-only)
        ↓ decisão humana
ActionPlan(improvement_case_id) + ActionItem(provenance)
        ↓ declaração humana
OutcomeObservation (append-only)
        ↓ projeção
GET …/evolution → comparação estrutural + closure_readiness
        ↓ decisão humana
reviewing → closed
```

Integração: **somente HTTP JSON**. Sem import Python cruzado. OI sem auth/RLS/UI/DB.

---

## 6. Contratos e versões

| Contrato | Versão | Schema OI | Wire Core |
|----------|--------|-----------|-----------|
| OrganizationContextInput | 1.0 | `organization-context-input.schema.json` | Context-OI |
| OrganizationalInsights | 1.0 | `organizational-insights.schema.json` | Context-OI |
| ProblemContextInput | 1.0 | `problem-context-input.schema.json` | ISOI-003+ |
| ProblemAnalysis | 1.0 | `problem-analysis.schema.json` | ISOI-003+ |

Compatibility check (ISOI-006): **compatible**.

---

## 7. Modelo de domínio (núcleo)

- `ImprovementCase` — fatos do problema + lifecycle
- `improvement_case_analysis_runs` — snapshots OI imutáveis
- `ActionPlan` — XOR Assessment / ImprovementCase
- `ActionItem` — provenance `source_analysis_run_id` + `source_finding_code`
- `ImprovementCaseOutcomeObservation` — resultado declarado

---

## 8. Ciclo completo

```text
Problema → Contexto → Problem Analysis 4.1/4.4
→ Hipótese/Achado/Recomendação → Decisão humana → Action Item
→ Resultado observado → Reanálise → Comparação/Evolução
→ Revisão / Encerramento humano
```

---

## 9. Capacidades incluídas

### Core

ImprovementCase org-scoped; fatos problema/impacto/processo; lifecycle
`open → analyzing → acting → reviewing → closed` (+ retornos permitidos);
hub; detalhe; `ProblemContextInput`; HTTP OI; guards; runs append-only;
fingerprint/stale; UI Contexto/Análise/Histórico; ActionPlan XOR;
finding→action; OutcomeObservation; comparação estrutural; resumo de ações;
closure readiness; revisão/encerramento humanos; RLS/auth/tenant switch;
OpenAPI/client.

### OI

`ProblemContextInput`/`ProblemAnalysis` v1.0; JSON Schemas; endpoint separado;
context gate; interpretação determinística 4.1/4.4; hipóteses; achados;
recomendações; supporting facts; humanização; limitações; sem persistência/auth/RLS/UI;
Context-OI `/analyze` preservado.

---

## 10. Matriz de capacidades

| Capability | Core | OI | Validated | Semantic limit |
|------------|:----:|:--:|-----------|----------------|
| ImprovementCase | ● | | ISOI-002/006 | Fato operacional, não NC |
| Problem facts | ● | | ISOI-002/006 | Input, não veredito |
| ProblemContextInput | ● | ● | ISOI-003/006 | Envelope, não conformidade |
| ProblemAnalysis | | ● | ISOI-003/006 | Interpretação ≠ auditoria |
| Context gate | | ● | ISOI-003/006 | Readiness ≠ conformity |
| 4.1/4.4 interpretation | | ● | ISOI-003/006 | Lentes limitadas |
| Hypotheses | | ● | ISOI-003/006 | Requer validação humana |
| Findings | | ● | ISOI-003/006 | Achado ≠ NC |
| Recommendations | | ● | ISOI-003/006 | ≠ ação automática |
| Analysis persistence | ● | | ISOI-003/006 | Snapshot imutável |
| Fingerprint/stale | ● | | ISOI-003/006 | Fatos problema/profile |
| Finding→action | ● | | ISOI-004/006 | Decisão humana |
| ActionPlan XOR | ● | | ISOI-004/006 | Assessment XOR case |
| Provenance | ● | | ISOI-004/006 | Run/finding estáveis |
| OutcomeObservation | ● | | ISOI-005/006 | Declaração da org |
| Run comparison | ● | | ISOI-005/006 | Diff estrutural |
| Closure readiness | ● | | ISOI-005/006 | Orientação ≠ certificação |
| Review/closure | ● | | ISOI-002/006 | Decisão humana |
| Tenant isolation | ● | | suites + smoke | RLS + OrgContext |
| Contract compatibility | ● | ● | ISOI-006 | v1 compatible |
| Context-OI V1 preservation | ● | ● | ISOI-006 | `/analyze` intacto |

---

## 11. Ownership

| Responsabilidade | Dono |
|------------------|------|
| Fatos, tenancy, auth, persistência, lifecycle, UI | **Core** |
| Interpretação 4.1/4.4, hipóteses, achados, limitações | **OI** |
| Integração | HTTP JSON apenas |

---

## 12. Limites semânticos

```text
Context Readiness != ISO Conformity
Problem Analysis != Auditoria
Achado interpretativo != Não conformidade
Recomendação != Ação automática
Action Item concluído != Eficácia comprovada
Finding removido do run seguinte != Problema resolvido
OutcomeObservation = declaração da organização
Closure readiness != Conformidade ou certificabilidade
Encerramento do caso != Certificação ou eficácia comprovada
```

---

## 13. Escopo normativo real

- Context-OI V1: readiness limitada das **cláusulas 4 e 7** (“4/7” = 4 e 7, **não** intervalo 4–7).
- Problem Analysis V1: lentes **4.1 e 4.4** apenas.
- Sem implementação integral da Cláusula 4.
- Sem cobertura integral das cláusulas 5–10.
- `iso_basis` = fundamentação estrutural, não veredito.

---

## 14. Histórico e imutabilidade

Runs e OutcomeObservations são append-only. Reanálise cria novo snapshot; anteriores não são reescritos. Ações preservam provenance ao run original.

---

## 15. Tenancy / RLS / autorização

OrgContext + `X-Organization-Id` + RLS FORCE; reader somente leitura; escrita de caso/observação/finding→action pelas roles de gerenciamento; FE com query keys org-scoped e `requestGeneration`.

---

## 16. Configuração operacional

| Item | Valor típico local |
|------|--------------------|
| QMind Core | `uvicorn app.main:app --host 127.0.0.1 --port 8009` |
| qmind-oi | `uvicorn qmind_oi.api.app:app --host 127.0.0.1 --port 8011` |
| PostgreSQL | `localhost:5433` DB `qmind_dev` |
| Migrations | Alembic até `20260819_0022` |
| `QMIND_OI_BASE_URL` | `http://127.0.0.1:8011` |
| `QMIND_OI_TIMEOUT_SECONDS` | `30` |
| Auth | `AUTH_MODE=dev` (local) |
| Tenant | header `X-Organization-Id` |

Smoke reutilizável:

```text
python scripts/smoke_improvement_case_loop_e2e.py
```

Compatibility:

```text
python scripts/check_oi_contract_compatibility.py
```

Não documentar secrets.

---

## 17. Smoke E2E (ISOI-006)

Script: `qmind/backend/scripts/smoke_improvement_case_loop_e2e.py`

Resultado: **73 passed / 0 failed** (Core ↔ OI HTTP real).

Cobriu: criar caso → analyzing → análise OI → finding→action → acting → lifecycle ActionItem até `done` → OutcomeObservation → stale por edição de fato → reanálise → comparação → `ready_for_review` → reviewing → closed; reader/tenant isolation amostrados.

---

## 18. Resultados das suítes (ISOI-006)

| Suite | Resultado |
|-------|-----------|
| qmind-oi ruff | passed |
| qmind-oi mypy | passed (40 files) |
| qmind-oi pytest | 87 passed |
| Core compatibility | compatible |
| Core backend (ISOI + OI + actions + OpenAPI) | 81 passed |
| Frontend IC Analysis/Finding/Evolution | 13 passed |
| Frontend build (`tsc -b && vite build`) | passed |

---

## 19. Homologação

```text
Homologação externa ISO Intelligence V1 não executada —
ambiente Core/OI conjunto não disponível.
```

Validação local Core+OI+Postgres executada via smoke.

---

## 20. Riscos e dívidas conhecidas

- Interpretação 4.1/4.4 limitada e determinística
- Sem evidências vinculadas ao caso/análise
- OutcomeObservation declaratória
- Sem indicadores/metas estruturados
- Comparação somente estrutural
- Sem avaliação de eficácia
- Sem análise integral da Cláusula 4
- OI dependente de disponibilidade HTTP
- Snapshots de schemas no Core
- Labels potencialmente duplicados Core/OI
- Homologação externa conjunto ausente
- Working tree monorepo pode conter sujeira não relacionada

---

## 21. Fora do escopo (deliberado)

Conformidade ISO; NC automática; auditoria automática; certificabilidade; probabilidade de certificação; score de maturidade; eficácia automática; causa raiz automática; indicadores/metas; análise automática de documentos; LLM; Fit; Pain; Journey; catálogo completo de processos; interpretação integral ISO; DB/auth/RLS/UI no OI; reanálise automática; criação automática de ações; fechamento automático.

---

## 22. Critério para evolução futura

Qualquer próxima fase exige decisão explícita de produto. **Não** iniciar automaticamente 4.2/4.3, cláusulas 5–10, Evidence Intelligence, indicadores, eficácia, certification readiness ou LLM.

Antes de nova fase:

1. baseline operada em uso real ou piloto;
2. feedback de usuário;
3. problema seguinte priorizado;
4. valor esperado;
5. limite semântico;
6. inspeção do impacto arquitetural.

---

## Migrations da baseline

```text
20260819_0019 → improvement_cases
20260819_0020 → improvement_case_analysis_runs
20260819_0021 → action_plan XOR + finding provenance
20260819_0022 → improvement_case_outcome_observations
```

Cadeia: `0018 → 0019 → 0020 → 0021 → 0022`.
