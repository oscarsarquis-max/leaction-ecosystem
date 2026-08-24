# 028 — ISO Intelligence V1 — Action Execution Workspace Ágil

- Status: **Implementado (Core-only) — Revisado 001**
- Date: 2026-08-24
- Activity: **ISOI-007** (+ Revisão 001 de integridade)
- Name: **Action Execution Workspace Ágil V1**
- Predecessor: [`027`](027_ISO_Intelligence_V1_Improvement_Case_Loop_Baseline.md) (ISOI-006)
- OI: **sem alteração funcional** — pin `2d78eff` preservado

Documento operacional do workspace ágil de execução de ações no QMind Core. Prepara fatos de execução para **Execution Intelligence** futura (ISOI-009); não interpreta esses fatos no OI neste incremento.

---

## 1. Propósito

Tornar visível e controlável o trabalho entre a decisão humana de criar uma ação e a verificação humana de implementação/eficácia — com board, sprints, squads, cerimônias e histórico — **sem** duplicar o `ActionItem` e **sem** criar um Jira genérico.

---

## 2. Mapa visual

```text
OI Finding
   ↓ decisão humana
ActionItem = Card
   ↓
Squad → Sprint → Board → Check-ins/Impedimentos
   ↓
Implementação → Validação → Eficácia
   ↓
Evolution / próxima interpretação OI (fase futura — ISOI-009)
```

Origens unificadas no board: **ImprovementCase / finding OI** e **Assessment / Finding** clássico — ambos projetam o mesmo `ActionItem`.

---

## 3. Princípios e invariantes (Revisão 001)

1. **Card = projeção do ActionItem** — alocação em sprint (`agile_sprint_cards`), não entidade `Task`.
2. **Squad ativa exige `value_owner`** — criação transacional: squad + membership `value_owner` na mesma transação (`value_owner_membership_id` obrigatório). Não remover/desativar/rebaixar o último value owner de squad ativa.
3. **Fatos de execução ↔ sprint** — check-in e impedimento com `sprint_id` exigem alocação ativa (`removed_at IS NULL`); mismatch → `action_sprint_mismatch`.
4. **Cerimônia ↔ sprint** — eventos `sprint_planning|daily_check_in|sprint_review|retrospective` exigem `sprint_id`; registro exige `event.sprint_id == path sprint_id`.
5. **Dependências preservam histórico** — remoção lógica (`status=removed`); unique parcial só para ativos; ciclo/`blocks` consideram apenas ativos.
6. **Board = read model único** — uma consulta backend; sem N+1 de check-ins no frontend; filtros distintos “sem check-in recente” vs “inteligência desatualizada”.
7. **UI sem UUID operacional** — seletores por nome/descrição/título; IDs só em rotas/payloads.
8. **Agilidade sem burocracia** — daily assíncrono; WIP só sinaliza; sem ranking/gamificação.
9. **Decisão humana / SoD** — mover card ≠ eficácia; validação/eficácia respeitam segregação existente.
10. **Segurança** — RLS ENABLE+FORCE; papéis ágeis não elevam RBAC.

---

## 4. Domínio (persistência)

Migration aditiva: **`20260824_0023`** (após `20260819_0022`).

| Entidade | Papel |
|----------|--------|
| `agile_squads` / `agile_squad_memberships` | Squads + papéis metodológicos |
| `agile_sprints` | Uma ativa por squad |
| `agile_sprint_cards` | Alocação ActionItem ↔ sprint |
| `action_execution_check_ins` | Append-only + `idempotency_key` |
| `action_impediments` | Bloqueio derivado |
| `action_dependencies` | Soft-delete (`active\|removed`); sem DELETE físico para `qmind_app` |
| `agile_ceremony_records` | Append-only / nova revisão |

Agenda: `sprint_id` obrigatório nos tipos de cerimônia.

---

## 5. Board (read model)

| Coluna | Fonte |
|--------|--------|
| Backlog | `ActionItem.open` sem sprint ativa |
| Selecionado | `ActionItem.open` na sprint ativa |
| Em execução | `in_progress` |
| Aguardando validação | `implemented` |
| Aguardando eficácia | `validated` |
| Requer revisão | `ineffective` |
| Concluído | `done` |

Projeção por card (backend): `latest_check_in_at/health`, `open_impediment_count`, `blocking_dependency_count`, `source_analysis_run_id`, `source_finding_code`, `source_analysis_is_stale` (fingerprint do run OI vs contexto atual do caso, mesma regra de `is_stale` dos ImprovementCases).

Movimento: `POST .../agile/board/move` → transições canônicas. Impedimento aberto exige justificativa explícita.

---

## 6. APIs (Core)

Prefixo: `/api/v1/organizations/current/`

- `agile/squads`, `agile/sprints` (+ activate/complete/cards/metrics/ceremony-records)
- `agile/board`, `agile/board/move`
- `actions/{id}/check-ins`, `impediments`, `dependencies` (`include_removed` para histórico)

UI: **Execução** (`/execution` …) consome `@qmind/api-client` gerado.

---

## 7. Métricas V1 (fórmulas)

| Campo | Semântica |
|-------|-----------|
| `planned_cards` / `completed_cards` / `throughput` | Contagens na sprint (throughput = concluídos no período da sprint) |
| `carry_over_cards` | Cards com `carried_from_sprint_id` |
| `in_progress_count` / `overdue_actions` / `open_impediments` | Contagens |
| `average_cycle_time_hours` / `median_cycle_time_hours` | Início → terminalização via eventos de auditoria de transição do ActionItem; `null` se amostra vazia |
| `oldest_in_progress_age_hours` | Idade do item em execução mais antigo; `null` se nenhum |
| `blocked_time_hours` | Soma de durações de impedimentos (abertos: até `now()`; resolvidos: até `resolved_at`) nos cards da sprint; `null` se nenhum |
| `cards_without_recent_check_in` | Cards alocados sem check-in na janela `check_in_stale_window_hours` (**72h**) |
| `review_outcome` | `summary` do último `agile_ceremony_records` tipo `sprint_review` — **não** infere eficácia |

Sem ranking individual nem produtividade por pessoa.

---

## 8. Integrações preservadas

- Contratos OI inalterados; pin funcional `2d78eff`
- Context-OI V1 e ISOI-006 intactos
- ActionPlan XOR Assessment/ImprovementCase preservado
- OpenAPI + `@qmind/api-client` regenerados e consumidos pela UI

---

## 9. Limitações remanescentes legítimas

- Listagem de eventos de Agenda por sprint na UI ainda varre a janela de dias da sprint (API Agenda filtra por `day`); endpoint `sprint_id` seria melhoria futura sem mudar contrato OI.
- Playwright E2E de UI não faz parte deste marco (cobertura E2E via API: trilha OI + Assessment).
- ISOI-008/009/010 fora de escopo.

---

## 10. Matriz Core ↔ OI

| Capacidade | Lado | Nota |
|------------|------|------|
| ISOI-007 Action Execution Workspace | **Core-only** | Fatos operacionais de execução |
| Execution Intelligence (futuro) | OI | Consumirá check-ins/impedimentos/métricas via contrato ainda não definido |
