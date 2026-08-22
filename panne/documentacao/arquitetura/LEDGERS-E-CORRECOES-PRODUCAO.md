# Ledgers e correções

## Pesagem

Quantidade efetiva = soma de `record` e `correction` cujo id não foi alvo de `reversal` ou `correction`. O registro original permanece.

## Conferência

Append-only. Com `second_person`, o conferente ≠ operador. Rejeição não edita: exige correção nova.

## Consumo

Independente da pesagem. Tipos `consume`, `return`, `waste`, `correction` (voida o alvo e aplica nova quantidade). Pesado ≠ consumido.

## Rendimento

Medições por tipo; reversão anula a original sem apagá-la. Resultado derivado em `deterministic_yield` / `1`.

## Imutabilidade

Gatilho `registro_imutavel` em ledgers e emissão. Sem `DELETE` físico nas tabelas de execução.
