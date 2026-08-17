# 021 — Context ↔ OI V1 Baseline

- Status: **Baseline**
- Date: 2026-08-17
- Sprint: **OI-019**
- Name: **Context-OI V1**

Documento operacional de fechamento da primeira baseline funcional do fluxo Context ↔ Organizational Intelligence. Não altera comportamento.

Validação E2E prévia: [`019_OI016_…`](019_OI016_Core_OI_E2E_Validation_V1.md), [`020_OI018_…`](020_OI018_Unknown_Readiness_E2E_Validation.md).

---

## 1. Baseline pins

| Lado | Commit | Conteúdo |
|------|--------|----------|
| **QMind OI** | `5d3bd81` | Contratos v1, context builder, readiness (`unknown` = lacuna), insights + humanização, adapter, orchestrator, HTTP API |
| **QMind Core** | `64d71ed` (HEAD documental) · código funcional do loop desde `034a87c` | Profile, HTTP client, persistência de runs, guards, UI `/assessments`, Completar, stale, reanálise, histórico |

Tag Git: **não criada** nesta sprint (sem convenção formal Context-OI). Recomendação: marco documental **Context-OI V1**.

---

## 2. Capacidade do produto (V1)

| # | Pergunta | Resposta V1 |
|---|----------|-------------|
| 1 | Quais fatos organizacionais existem? | Organization Profile no Core (trade/legal name, summary, industry, business_model, employee_range, unit_count, certification_status, quality_structure). |
| 2 | Há informação suficiente para o contexto modelado (cláusulas 4 e 7)? | OI monta Context Readiness por cláusula: `READY` ou `MISSING_INFORMATION`. |
| 3 | Quais informações ainda estão ausentes? | `supporting_facts` técnicos + summary humanizado listando lacunas. |
| 4 | Como o usuário completa? | UI Completar → edição do Profile com foco no campo → PATCH. |
| 5 | Como gerar nova análise? | `POST …/intelligence/analyze` (UI “Atualizar análise”). |
| 6 | Como o histórico é preservado? | Cada sucesso cria um `organization_intelligence_runs`; runs antigos não são reescritos. |

### Fluxo

```text
Organization Profile
        ↓
Core → HTTP → OI (schema 1.0)
        ↓
Context Readiness → Organizational Insights
        ↓
Core Persistence → UI /assessments
        ↓
Completar contexto → PATCH → stale cue → Reanalisar
```

---

## 3. Limite semântico

**Context Readiness ≠ ISO Conformity.**

A V1 **não** determina: conformidade ISO, não conformidade, certificabilidade, maturidade ISO, eficácia do SGQ.

Determina apenas **prontidão do contexto disponível** para as capacidades implementadas (lentes de presença das cláusulas 4 e 7 no profile atual).

`"unknown"` em vocabulários controlados (`quality_structure`, `certification_status`) é **fato preservado** e **lacuna de readiness** (OI-017 / OI-018).

---

## 4. Ownership

| Responsabilidade | Dono |
|------------------|------|
| Fatos / Profile / tenancy / auth / persistência de runs / UI | **Core** |
| Interpretação de readiness / insights / humanização de textos públicos | **OI** |
| Integração | HTTP JSON apenas — sem import Python cruzado |

---

## 5. Matriz de capacidades

| Capability | Core | OI | Validated |
|------------|:----:|:--:|:---------:|
| Organization Profile | ● | | OI-016 |
| Context Assembly | | ● | OI-003+ |
| Clause 4 Readiness | | ● | OI-016/018 |
| Clause 7 Readiness | | ● | OI-016/018 |
| Insight Generation | | ● | OI-005+ |
| Insight Humanization | | ● | OI-015/018 |
| HTTP Integration | ● | ● | OI-008/009/016 |
| Persistence (runs) | ● | | OI-010/016 |
| Context Completion (Completar) | ● | | OI-014/018 |
| Stale + Reanalysis | ● | | OI-013/016 |
| Tenant Isolation | ● | ●* | OI-016 |
| Contract Compatibility | ● | ● | OI-011/019 |

\* OI ecoa `core_organization_id`; isolamento de dados é do Core.

---

## 6. Contratos

- `schema_version = "1.0"` (OrganizationContextInput / OrganizationalInsights).
- Compatibility check Core ↔ snapshots OI: **compatible** (OI-019 closure).
- Schemas no Core são **snapshots**; fonte canônica no repo `qmind-oi`.

---

## 7. Operação local

```text
PostgreSQL   leaction_db → qmind_dev :5433
Core API     uvicorn app.main:app --port 8009
OI API       uvicorn qmind_oi.api.app:app --port 8011
Auth         AUTH_MODE=dev (local)
```

```text
QMIND_OI_BASE_URL=http://127.0.0.1:8011
QMIND_OI_TIMEOUT_SECONDS=30
```

Referências: `backend/.env.example`, `architecture/04_Docs/016_…`, OI `docs/architecture/009-http-api-v1.md`.  
Infra homolog Core (sem OI nesta baseline): `infra/terraform-lightsail/` + `DEPLOY.md`.

Smoke curto (reuso): `backend/scripts/smoke_oi018_unknown_readiness.py`.

---

## 8. Homologação externa

**Homologação externa Context↔OI não executada — ambiente OI não disponível em homolog.**

Existe homolog Lightsail do Core (`api`/`app.homolog.qmind.com.br`); não há OI provisionado nesse ambiente nesta baseline.

---

## 9. Dívidas / limitações conhecidas

- Snapshots de schema no Core vs fonte em `qmind-oi` (mitigado por check de compatibilidade).
- Labels de Profile duplicados (Core FE + OI `field_labels`) — sem i18n compartilhado.
- OI depende de `QMIND_OI_BASE_URL` no Core.
- Escopo ISO: somente readiness de presença para cláusulas 4 e 7 no profile atual.
- Sem Fit / Pain / Journey / recomendações / LLM nesta linha.

---

## 10. Fechamento OI-019

| Check | Resultado |
|-------|-----------|
| Smoke curto (reuse OI-018) | PASS |
| Contract compatibility | PASS |
| Suítes OI / Core OI+profile / FE loop | registradas no relatório da sprint |

**Baseline Context-OI V1 estabelecida.**
