# Evidência R026-004 — acabamento perfil / achados

Data: 2026-08-27
Produto: Panne Demo
Sem commit / push / CURSOR-027.
Estado: **validada integralmente pelo Cortex no navegador**.

## Validação Cortex (navegador)

Confirmados na validação final:

- isolamento Panne → Horizonte → Panne e limpeza imediata;
- perfil: `Sim` / `Não` / `Não informado`, `Varejo`, `Sólido`;
- achado: `Lactose — evidência insuficiente`;
- `50 g`; plural e totais do estoque;
- superfície principal sem `true`, `false`, `retail`, `solid` nem `Código técnico não catalogado`.

## Histórico — passagens anteriores nesta R026-004

- Isolamento visual Panne → Horizonte → Panne
- Limpeza imediata na troca (`Carregando dossiê da organização ativa…`)
- Proteção contra resposta atrasada
- Conteúdo líquido `50 g`
- Plural do estoque (`6 posições`)
- Totais de estoque coerentes

## Resíduos corrigidos antes da validação final

No dossiê `74fb3138-58e0-4ea1-a1fa-fd4edeeb19f8` (antes da correção):

- Perfil: `true` / `retail` / `solid` em campos editáveis
- Achados: título `Código técnico não catalogado`

## Origem / contrato

### Booleanos anuláveis (`bool | null`)

`packed_food`, `packed_away_from_consumer`, `packed_at_point_of_sale`, `packed_on_request`, `same_establishment`, `food_service`, `ready_to_eat`

API (`ProfileBody`): `bool | None`. Ausência ≠ falso.

### Enums (string livre no API; valores do domínio)

| Campo | Valores do contrato / uso |
|---|---|
| `sales_channel` | `retail`, `own_store`, `food_service`, `wholesale`, `e_commerce`, `online`, `other` |
| `physical_state` | `solid`, `semisolid` (lupa); também `liquid`, `powder`, `gas`, `other` |
| `regulatory_category_code` | `pao`, `bolo`, `biscoito`, `massa` (catálogo de porção) |

### Código do achado não catalogado

API retornou `rule_code: "lactose"` (após `gluten_contains` e `may_contain`), gerado em `labeling_compliance/warnings.py`.

## Correção

- Catálogos + `triStateLabel` / selects humanos no perfil
- `lactose` → `Lactose — evidência insuficiente`
- Fallback de superfície: `Regra ainda não catalogada` / `Opção ainda não catalogada` (código só na auditoria)
- Persistência inalterada (`true`/`false`/`null`/`retail`/`solid`)

## Testes

`labeling-profile-human.test.tsx` + suite frontend completa.
