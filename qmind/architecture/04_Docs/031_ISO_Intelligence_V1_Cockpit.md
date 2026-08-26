# ISO Intelligence V1 — Cockpit (ISOI-010)

- Status: **Implementado (aguardando revisão de gate)**
- Data: 2026-08-26
- Escopo: **Core-only**
- Predecessor: ISOI-009 — Core `21df383`, OI `34ead2e` (sem alteração funcional neste incremento)
- Migration: **nenhuma** (`20260826_0025` permanece head; índices existentes bastam)

## 1. Mapa visual

```text
improvement_cases / actions / impediments / evidence / measurements / outcomes
        │
        ▼  batch set-based (ANY + GROUP BY + LATERAL)
Cockpit read model (as_of)
        │  + latest EI runs (persistidos) → freshness current|stale|never
        ▼
GET /iso-intelligence/cockpit/{summary,cases,activity}
        │
        ▼
UI /cockpit  ──drill-down──► Evolution / Card / Measurement
        │
        ▼ ação humana nos módulos existentes
nova leitura factual (sem POST OI)
```

## 2. Dicionário de contadores

| Contador | Unidade | Fonte |
|----------|---------|--------|
| `case_totals.*` | casos | `improvement_cases.status` |
| `priority_distribution` | casos | faixa calculada por regras transparentes |
| `execution.active/completed/overdue_actions` | ações | `action_items` + lifecycle Core |
| `execution.blocked_cases` | casos | ≥1 impedimento aberto |
| `execution.active_impediments` | impedimentos | `action_impediments.status=open` |
| `execution.open/overdue_dependencies` | dependências | `action_dependencies` |
| `evidence.*` | ações | `claims_execution` × Evidence aprovada |
| `measurement.by_*` | casos/indicadores | posturas Core de medição/meta |
| `intelligence_coverage` | casos | fingerprint batch × latest run |
| `execution_posture_distribution_current/stale` | casos | posture do latest run, separado por freshness |
| `signals_current` / `signals_stale` | sinais | `result.signals` do latest run |
| `recent_activity` | eventos | janela 7/30/90 dias explícita |

## 3. Fila e precedência

Faixas: `immediate_attention` > `attention` > `follow_up` > `on_course` > `completed_or_observed`.

Motivos estáveis em `priority_reasons[]` (código + rótulo humano). Pior faixa vence; vários motivos permitidos. Sem score.

Ordenação na faixa: prazo mais antigo → última atividade mais antiga → `case_id` só como desempate interno.

## 4. Fato atual × interpretação OI

- Contadores e fila usam fatos Core no instante `as_of`.
- Latest EI run persistido: `current` se `input_fingerprint` = fingerprint batch; `stale` se diferente; `never_analyzed` se ausente.
- Sinais de runs stale **nunca** entram em `signals_current`.
- Abrir/filtrar/atualizar o cockpit **não** chama OI nem cria runs.

## 5. Batch fingerprint

`cockpit/batch_fingerprint.py` carrega casos, planos, ações agregadas, medições e outcomes em consultas set-based; monta o mesmo `ExecutionIntelligenceInput` do builder ISOI-009; aplica `fingerprint_execution_intelligence_input` (exclui `request_id`/`correlation_id`/`captured_at`). Chunks de 100. Testes comparam batch × single-case; query count constante (5) para 1 e 25 casos no mesmo chunk.

## 6. Segurança

- Roles de leitura iguais ao Improvement Case / Evolution (`reader` e `action_owner` inclusos).
- RLS via `tenant_connection`.
- Cursor opaco com `organization_id`; reuso cross-org recusado.
- Payload sem e-mail, membership id, storage key, conteúdo de Evidence ou texto integral de check-in.
- `Cache-Control: private, no-store`.

## 7. APIs e UI

```text
GET /api/v1/organizations/current/iso-intelligence/cockpit/summary
GET /api/v1/organizations/current/iso-intelligence/cockpit/cases
GET /api/v1/organizations/current/iso-intelligence/cockpit/activity
```

Filtros de fila no backend (além de status/banda/postura/busca): `ready_for_review`, `has_overdue_actions`, `has_active_impediment`. Cursor estável na fila; UI “Carregar mais” consome `next_cursor`.

UI: rota lazy `/cockpit`, item **Cockpit** no AppShell. Síntese, distribuições acessíveis, fila desktop/mobile, filtros na URL, drill-down para o caso. Botão “Atualizar visão” = somente GETs.

## 8. Performance

- Paginação cursor, limit default 25 / max 100; filtros aplicados **antes** do slice.
- Batch fingerprint em chunks de 100; query count constante por chunk (não O(N) por caso).
- Sem N+1; sem materialized view nesta V1.
- Sem migration `0026`: planos de consulta do dataset de teste não exigiram índice novo além dos existentes (`ix_improvement_cases_org_updated`, `ix_ic_ei_runs_case_created`, FKs de caso/ação).

### EXPLAIN (sanitizado, `qmind_dev`)

**Projeção de casos (fila):**

```text
Incremental Sort
  Sort Key: updated_at DESC, id
  -> Index Scan using ix_improvement_cases_org_updated on improvement_cases
       Index Cond: (organization_id = $org)
       Filter: (status <> 'closed')
```

**Latest EI por caso (`DISTINCT ON`):**

```text
Unique
  -> Sort
       Sort Key: improvement_case_id, created_at DESC
       -> Seq Scan on improvement_case_execution_intelligence_runs
            Filter: (organization_id = $org)
```

Em orgs com poucos runs EI o seq scan é aceitável; o índice por caso (`ix_ic_ei_runs_case_created`) cobre o caminho `ANY(case_ids)` usado pelo cockpit. Reavaliar se o volume de runs crescer.

Activity: `UNION ALL` seekável com tie-break `(occurred_at, event_type, case_id, action_item_id, source_id)` — nunca “primeira tranche global + filtro em Python”.

## 9. E2E e evidências

- Playwright (quando disponível): seed demo → síntese → filtro → drill-down → retorno com filtros → refresh sem POST OI.
- Screenshots sanitizados (dados fictícios DEMO; sem PII):

| Arquivo | Conteúdo |
|---------|----------|
| [`assets/isoi-010/cockpit-desktop-full.png`](assets/isoi-010/cockpit-desktop-full.png) | Desktop — síntese + fila |
| [`assets/isoi-010/cockpit-filtered-queue.png`](assets/isoi-010/cockpit-filtered-queue.png) | Fila com filtro (atenção imediata) |
| [`assets/isoi-010/cockpit-mobile-width.png`](assets/isoi-010/cockpit-mobile-width.png) | Largura mobile (~390px) |
| [`assets/isoi-010/cockpit-drilldown-ei.png`](assets/isoi-010/cockpit-drilldown-ei.png) | Drill-down Evolution / EI |

Regenerar: `npx playwright test e2e/iso-intelligence-cockpit-screenshots.spec.ts` com Core + preview ativos.

## 10. Roteiro demonstrativo (5 minutos)

1. Rodar seed local `backend/scripts/seed_cockpit_demo_local.py` (AUTH_MODE=dev; dados fictícios).
2. Abrir `/cockpit` — mostrar síntese e quatro jornadas.
3. Filtrar atenção imediata — caso bloqueado/vencido.
4. Abrir caso — Evolution + EI (se existir).
5. Voltar — filtros preservados; “Atualizar visão”.
6. Lembrar: decisões humanas; meta ≠ eficácia; OI não é chamado pelo cockpit.

## 11. Limitações

- Sem tendência histórica inventada; snapshot `as_of` apenas.
- Closure readiness do cockpit compartilha `evaluate_closure_readiness` com Evolution (análise + stale fingerprint inclusos).
- Activity não cobre todas as transições de auditoria de status.
- ISOI-011 (hotpage pública) **não** iniciado.

## 12. Preparação ISOI-011

Manter cockpit Core-only e contratos OI estáveis. A jornada pública futura consome o mesmo vocabulário humano (faixas/motivos), sem antecipar hotpage, marketing site ou deploy.
