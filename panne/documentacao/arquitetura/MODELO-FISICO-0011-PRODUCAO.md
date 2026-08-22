# Modelo físico 0011 — execução

Revision `0011_production_execution`. FKs compostas `(id, organization_id)`. RLS ENABLE+FORCE, default deny.

| Tabela | Mutável | Papel |
|---|---|---|
| `production_execution_policy` | só antes de congelar | Snapshot de política por ordem |
| `production_weighing_session` | estado/versão | Sessão `open`/`completed`/`cancelled`; uma aberta por batelada |
| `production_weighing_entry` | append-only | Ledger `record`/`reversal`/`correction` |
| `production_weighing_verification` | append-only | `accepted`/`rejected` |
| `production_material_consumption` | append-only | `consume`/`return`/`waste`/`correction` |
| `production_step_execution` | estado atual | Etapa × batelada |
| `production_step_execution_event` | append-only | Histórico da etapa |
| `production_yield_measurement` | append-only | Massas, unidades, sobra, descarte |
| `production_occurrence` | status | Abertura factual |
| `production_occurrence_event` | append-only | `opened`/`resolved` |
| `production_dependency_override` | append-only | Override humano de predecessor `short_closed` |
| `production_sheet_issue` | append-only | Emissão numerada + SHA-256 |

Colunas novas em `production_order` / `production_batch`: pausa, conclusão e encerramento. Contador `kind=sheet` para número sequencial da ficha. Índice único `(id, organization_id)` em `production_batch_material` para FK composta.
