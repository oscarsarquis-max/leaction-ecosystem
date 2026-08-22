# Catálogo dos tipos declarativos

Motor `deterministic_compliance` v1. Schema Pydantic `extra="forbid"`. Sem `eval`, sem código no banco e sem expressão livre.

| Tipo | Parâmetros | Resultado possível |
|---|---|---|
| `evidence_presence` | `evidence_key` | `pass` ou `insufficient_data` |
| `numeric_comparison` | `input_key`, `operator` (`eq`,`ne`,`gt`,`gte`,`lt`,`lte`), `threshold` Decimal | `pass`, `fail` ou `insufficient_data` |
| `boolean_condition` | `input_key`, `expected` | `pass`, `fail` ou `insufficient_data` |
| `catalog_membership` | `input_key`, `catalog`, `mode` (`in`/`not_in`) | `pass`, `fail` ou `insufficient_data` |
| `mandatory_manual_review` | `reason` | `manual_review` |
| `compound` | `operator` (`and`/`or`), `clauses` só dos tipos-folha | propaga insuficiência ou revisão |

Ausência de valor **nunca** vira zero nem aprovação. Tipo desconhecido ou campo extra é recusado na validação.
