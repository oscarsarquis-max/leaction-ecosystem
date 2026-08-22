# Política de pesagem e execução

Definida **antes** da liberação (`set_execution_policy`). Na `release_order` é validada, hasheada e congelada. Depois disso o gatilho `politica_imutavel` impede alteração.

Campos: pesagem `required` | `optional` | `not_applicable`; conferência `none` | `second_person`; tolerância absoluta e/ou percentual (`Decimal`); tolerância de conclusão (percentual do alvo); permissão de `short_closed`; lote manual; algoritmo `execution_policy` / `1`; criador e instante.

Se ambas as tolerâncias de pesagem forem nulas, só a igualdade quantizada está dentro. Fora da tolerância exige justificativa. Unidades aceitas: dimensão `mass`.

Não há backfill: ordem liberada na 0010 sem política **não** é tratada como já pesada. Nova liberação sem política falha com `politica_execucao_obrigatoria`.
