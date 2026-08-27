# Evidência R026-002 — Quadro vs seed + troca de organização

Org Panne Demonstração `45104a8c-d590-5946-b8dd-f5534e89e338`
Estabelecimento Padaria Central `8f941e25-d6a5-5b27-93aa-cbc4c7fa1ce8`

## Matriz de filtros (API) — 1ª passagem

| Query | Cards |
|---|---:|
| (sem filtros) | 10 |
| `operational_date=2026-08-24` | 5 |
| `operational_date=2026-08-27` | 0 |
| `2026-08-24` + Padaria Central | 5 |
| `2026-08-24` + Central + `shift=morning` | **3** (cenário sugerido) |
| idem + `area=fornos` | **0** |
| idem + `area=masseira` | **0** |

## Ordens do cenário sugerido (2026-08-24 · Central · Manhã · sem área)

- ORD-20260824-0001 draft
- ORD-20260824-0003 released
- ORD-20260824-0004 in_weighing

## Isolamento de dados

Padaria Horizonte Demo com `operational_date=2026-08-24` → 0 cards (vazio legítimo; sem ordens da Panne).

## Causa 1ª passagem (Quadro vazio)

1. UI usava `todayIso()` → 2026-08-27 → quadro vazio.
2. Contexto padrão forçava `area=fornos`; a API filtra `public_code ILIKE '%fornos%'` → zero com data/turno corretos.

## Validação Cortex — Quadro inicial

Aprovada no navegador (contadores 2/1, lista 3, fluxo/estações, nomes, sem console error).

## Devolução Cortex — contexto residual na troca de org

Troca seletor: Panne Demonstração → Padaria Horizonte Demo.

| Etapa | URL observada (antes da correção) | Faixa |
|---|---|---|
| Panne com cenário | `...?operational_date=2026-08-24&establishment_id=8f941e25-…&shift=morning` | `24 ago 2026 · Padaria Central · Manhã · Todas as áreas` |
| Após troca p/ Horizonte | **mesmos params** (id da Central) | ainda **Padaria Central** + “Sem acesso a este estabelecimento” |

Sem vazamento de ordens; vazamento de contexto/URL.

## Causa 2ª passagem

`clearOperationalContext()` limpa sessionStorage, mas URL + estado do `BoardPage` + filtros que aceitavam `establishment_id` com `catalog === null` mantinham o estabelecimento da org anterior.

## Correção 2ª passagem (comportamento esperado)

| Etapa | Esperado |
|---|---|
| Panne demo | Contexto válido da Panne (âncora + 1º estabelecimento do catálogo) |
| → Horizonte | URL sem `establishment_id` da Panne; sem “Padaria Central”; sem “Sem acesso…” residual; vazio legítimo ou contexto Horizonte |
| → Panne | Cenário demonstrativo restabelecido |
| Fora do demo | Limpa contexto; formulário de novo contexto; sem âncora forçada |

Teste automatizado: `frontend/src/board-org-switch.test.tsx` (demo round-trip + não-demo).
