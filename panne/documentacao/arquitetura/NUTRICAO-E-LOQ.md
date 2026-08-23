# Nutrição por 100 g e LQ

Cada linha aponta a um nutriente do catálogo global.

Estados: `measured`, `known_zero`, `below_loq`, `not_detected`, `unknown`.

- valor decimal viaja como string
- ausência não é zero
- `below_loq` mantém `value = null` e exige limite de quantificação
- `known_zero` grava zero explícito
- fonte/método e observação técnica são opcionais

Não há arredondamento regulatório nem declaração de conformidade.
