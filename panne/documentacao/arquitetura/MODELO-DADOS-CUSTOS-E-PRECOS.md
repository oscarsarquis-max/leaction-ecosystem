# Modelo de dados — 0018 custos e preços

Migração reversível `0018_costing_pricing`. UUID, `timestamptz`, `numeric`. FKs compostas por organização. Unique indexes. RLS ENABLE+FORCE. Exclusão física bloqueada.

| Tabela | Papel |
|---|---|
| `costing_policy` | política da organização, `row_version` |
| `costing_policy_version` | versão imutável após `published` |
| `costing_assumption` | premissa/tarifa append-only |
| `costing_calculation` | memória de cálculo append-only |
| `costing_component` | linha de categoria/origem |
| `costing_evidence` | snapshot de preço, conversão e fato |
| `costing_gap` | ausência explícita |
| `costing_invalidation` | evento; não reescreve o cálculo |
| `pricing_simulation` | markup/margens/reversa |
| `pricing_simulation_component` | bases e taxas da simulação |
| `practiced_price` | preço com vigência e canal |
| `pricing_decision` | histórico de decisão humana |
| `costing_command` | idempotência |

Cálculos, componentes, evidências, lacunas, simulações, decisões e comandos são append-only. Invalidar não altera totais antigos.
