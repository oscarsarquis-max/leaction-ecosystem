# Divisão de bateladas e arredondamento

Sem float. `Decimal` com a política já existente (`QUANTITY_QUANTUM` 6 casas, fatores 10 casas, `ROUND_HALF_UP`).

Método: `equal_share_plus_remainder`. Cada parte recebe o quociente quantizado; o resíduo em quanta vai às primeiras bateladas da sequência. A soma é exatamente o alvo da ordem.

Unidades exigem quantidade inteira e peso unitário. Massa usa o quantum de quantidade.

Alocações de material por batelada repetem a mesma regra sobre o líquido e o bruto do snapshot. A soma das alocações é exatamente a linha do snapshot.

Memória da divisão fica em `production_batch.split_memory` (método, regra de resíduo, contagem, alvo).
