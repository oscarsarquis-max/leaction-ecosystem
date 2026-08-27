# Evidência R026-004 — segunda passagem (bloqueios Cortex)

Data: 2026-08-27
Produto: Panne Demo
Sem commit / push / CURSOR-027.
Estado: **validada integralmente pelo Cortex** (conjunto R026-004; esta evidência registra a segunda passagem).

## Aprovado (não regredir)

Detalhe da ordem — Integridade da ficha, auditoria recolhida, eventos traduzidos, quantidades operacionais.

## Bloqueios corrigidos nesta passagem

### 1. Cancelamento concorrente

- `isCancelledError` / `reportLoadError` em `api/errors.ts`
- `useAsyncResource` com geração + montagem
- `ErrorState` trata `cancelado` como carregamento (cinto)
- Páginas: Traceability, PlanDetail, Sheet, Inventory `useItems`, Labeling create/list/detail, OrderDetail

### 2. Estoque R026-004-b

- `aggregateBalancesByUnit` — sem misturar unidades
- `formatOperationalQuantity` em posição, reservas, movimentos, inventários, necessidades
- Visão geral: cartões por unidade

### 3. Dossiê R026-004-c

- Lista: nome da receita + estado humano (sem UUID truncado)
- API: enrich `formulation` / `formulation_version` org-scoped
- Catálogos em `language/labeling.ts`
- Detalhe: nutrientes, FOP, achados, obrigatórios, completude

### 4. Plano R026-004-a

- `plan_item_out(..., product=)` + outerjoin em `get_plan`
- UI: `display_name` / código; UUID só na auditoria
- Teste backend: `test_production_api.py` (9 passed)

### 5. Scanner R026-004-d

- `language-scanner.test.ts` → `R026-004-scanner.md`

### 6. Eventos R026-004-e

- Catálogo central; fallback humano; duplicatas removidas

## Testes

```text
frontend: human-language*, language-scanner, labeling, orders-list, board-*, ops
backend: test_production_api.py → 9 passed
```

## Reinício limpo

Executado `stop-demo.ps1` + verificação de portas + `start-demo.ps1` + `/health` `/ready` antes da entrega ao Cortex.
