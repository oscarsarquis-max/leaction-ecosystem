# Conversão de unidades de massa

Pesagem e consumo aceitam unidades de massa compatíveis. Massa↔volume é proibida.

Unidade canônica: **grama (`g`)**.

Campos persistidos:

- quantidade e unidade informadas (`quantity`, `unit_code`)
- quantidade e unidade canônicas
- fator, origem (`measurement_unit.si_factor` ou `legacy_identity`) e versão (`1`)

Regras:

- `Decimal` apenas; sem `float`
- `fator = si_origem / si_canônico` (kg→g = 1000)
- tolerância calculada em gramas canônicas
- valores anteriores backfillados com fator 1 e origem `legacy_identity`, sem reinterpretar
- projeções somam `canonical_quantity`

g→kg e kg→g são o mesmo algoritmo (massa→grama).
