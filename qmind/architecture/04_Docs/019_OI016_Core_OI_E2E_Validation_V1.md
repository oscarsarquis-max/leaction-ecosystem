# 019 — OI-016 Core ↔ OI End-to-End Validation V1

- Status: Completed
- Date: 2026-08-17
- Sprint: **OI-016**
- Result: **PASS** (no code fixes)

## Ambiente

| Peça | Detalhe |
|------|---------|
| SO | Windows 10 / PowerShell |
| Postgres | Docker `leaction_db` → `localhost:5433` / DB `qmind_dev` |
| QMind Core API | `http://127.0.0.1:8009` (`uvicorn app.main:app`) |
| QMind OI API | `http://127.0.0.1:8011` (`uvicorn qmind_oi.api.app:app`) |
| Auth | `AUTH_MODE=dev`, headers `X-Dev-User-Sub` / `X-Organization-Id` |

## Commits validados

| Repo | Commit | Mensagem |
|------|--------|----------|
| **qmind-oi** | `0a9f605` | `feat(insights): humanize organizational insight messages` |
| **QMind Core** (`qmind/` no monorepo) | `034a87c` | `feat(oi): connect intelligence gaps to organization context` |

## Configuração (não sensível)

```text
ENVIRONMENT=local
AUTH_MODE=dev
QMIND_OI_BASE_URL=http://127.0.0.1:8011
QMIND_OI_TIMEOUT_SECONDS=30
VITE_API_PROXY_TARGET=http://127.0.0.1:8009
VITE_AUTH_MODE=dev
```

## Cenário

1. Criar org A (e B para tenancy).
2. PATCH profile parcial: `employee_range=""`, `quality_structure="unknown"`, demais campos básicos preenchidos, `unit_count` ausente.
3. `POST /api/v1/organizations/current/intelligence/analyze` (Core → OI HTTP real).
4. PATCH preencher lacunas (`employee_range`, `quality_structure`, `unit_count`).
5. Reanalisar; listar runs; switch tenant; parar OI e reanalisar.

Script reproduzível: `backend/scripts/smoke_oi_e2e_local.py` (37 checks).

## Resultados

| Área | Resultado |
|------|----------|
| Profile → Core → OI HTTP | PASS — schema `1.0`, `core_organization_id` = tenant |
| Persistência | PASS — `organization_intelligence_runs` |
| Humanização | PASS — summary com “Número de colaboradores”; sem `employee_range` / `quality_structure` no texto |
| `supporting_facts` | PASS — chaves técnicas (`employee_range`, `unit_count`, …) |
| PATCH + histórico | PASS — run1 intacto após PATCH; sem run extra no PATCH |
| Reanálise | PASS — run2 novo; lacunas preenchidas saem dos facts |
| Tenancy A↔B | PASS — runs/profile/insights isolados |
| OI indisponível | PASS — HTTP **502** `oi_unavailable`; nenhum run novo; profile intacto; recovery OK |
| Completar / stale / foco | PASS — via Vitest (`OrgIntelligenceContextLoop`, `OrgOrganizationalIntelligence`) |
| Suítes | PASS — ver abaixo |
| Contract compat | PASS — `Core <-> OI contracts v1: compatible` |

## Bugs

Nenhum **BUG-OI-016-XX**. Nenhuma correção de código.

## Limitação observada

**LIM-OI-016-01** — No Core, `quality_structure` (e `certification_status`) defaultam para `"unknown"`. No OI (OI-003), token controlado presente (incl. `"unknown"`) **não** entra em `missing_information`. Portanto, pelo caminho Core→OI com profile default, `quality_structure` **não** aparece como lacuna nem no Completar baseado em `supporting_facts`.

Humanização de `quality_structure` foi confirmada com chamada **direta** ao OI enviando `quality_structure: null` (summary amigável + fact técnico).

`employee_range=""` e `unit_count=null` cobrem o cenário de lacuna + Completar no fluxo integrado.

## Evidências técnicas

- Smoke live: **37/37 PASS**
- OI down: `{"code":"oi_unavailable","message":"QMind OI is unavailable"}` status 502
- OI suites: ruff OK, mypy OK, pytest **66 passed**
- Core: pytest OI + profile **31 passed**; contract check OK
- FE: Vitest context/OI/tenant **15 passed**; `npm run build` OK

## Limitações do exercício

- Validação de Completar/foco/stale foi por **testes de componente** (não clique manual no browser nesta sessão).
- UI `/assessments` depende do Vite proxy local; o loop funcional Core↔OI foi exercitado na API real + testes FE do loop.

## Recomendação OI-017

Decidir se `"unknown"` em vocabulários controlados deve continuar como “presente” no readiness ou se o Core deve omitir/`null` esses campos até o consultor escolher um valor explícito — alinhando Completar a `quality_structure` no fluxo padrão. Não misturar com novas capacidades de insight.

## Resolução LIM-OI-016-01 (pós OI-017)

**Resolvido em OI-017** (`qmind-oi`): `"unknown"` continua fato preservado no profile; para readiness passa a contar como informação não determinada (`quality_structure` / `certification_status` → `missing_information`). Sem alteração de contrato nem do Core. Histórico da validação OI-016 acima permanece como executado.
