# R026-009 — Elegibilidade e disponibilidade de estoque

## Estado

**Validada integralmente pelo Cortex** (após a terceira passagem).

## Passagens

| Passagem | Papel |
|---|---|
| 1ª | Corrigiu matemática e semântica de saldos/elegibilidade |
| 2ª | Corrigiu referência temporal visível e navegação contextual (`?lot=`) |
| 3ª | Unificou a data operacional da API e da interface (`as_of`) |

## Validação integral (Cortex)

- API e UI compartilham a referência operacional.
- Demo: referência 24/08/2026; LOT-000002 · 27/08/2026 · vence em 3 dias; relógio real não substitui a âncora.
- Totais (g): Físico 33.100 · Reservado 24.000 · Não reservado 9.100 · Impedido 2.300 · Disponível para produção 6.800.
- LOT-000003 bloqueado e LOT-000004 quarentena com disponibilidade operacional zero.
- Links de posição distintos; `?lot=LOT-000004` filtra; filtro identificado; Limpar filtro.
- Isolamento Panne → Horizonte (remove parâmetro e dados) → retorno à Panne ok.
- Sem regressão nos totais nem na semântica de elegibilidade.

## Contrato temporal

- Fonte: `inventory_operational_date()` (`PANNE_DEMO_ANCHOR_DATE` só em `PANNE_ENV=demo`).
- Payload: `as_of` + `timezone=America/Sao_Paulo`.
- FE: `resolveInventoryAsOf(body.as_of)`.

## Decisão semântica

- `available_quantity` → UI **Não reservado**.
- `eligible_quantity` / `impeded_quantity`.
- FEFO alinhado ao mesmo `as_of`.

## Testes (entrega)

- Backend: 6 passed (`test_inventory_eligibility_r026_009.py`).
- Frontend: 10 passed (`inventory-r026-009.test.tsx`).

## Restrições observadas no registro

CURSOR-027 não iniciado. Sem commit/push/merge/deploy.
