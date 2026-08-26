# Dicionário de métricas

Registro em `reporting_analytics/metrics.py`, versão `1`. Markup, margem bruta e contribuição reutilizam `costing_pricing.formulas`.

| Código | Unidade | Numerador | Denominador | Ausência |
|---|---|---|---|---|
| `orders_by_status` | count | ordens no estado | n/a | estado sem ordem não vira volume zero |
| `planned_quantity` | mista | `target_quantity` | n/a | unidade mista: indisponível |
| `actual_quantity` | mista | unidades vendáveis ou massa pós | n/a | sem rendimento: indisponível |
| `normal_completion_rate` | % | `completed` | `completed + short_closed` | denominador vazio |
| `short_close_rate` | % | `short_closed` | `completed + short_closed` | denominador vazio |
| `quantity_adherence` | % | realizado elegível | planejado da mesma unidade | sem par |
| `net_consumption` | massa | consume − return | n/a | sem fato |
| `consumption_variance` | % | líquido − planejado | planejado | sem planejado |
| `yield_actual` | % | massa pós-forno | massa pré-forno | par incompleto |
| `loss_actual` | % | pré − pós | massa pré-forno | par incompleto |
| `cost_variance` | BRL | realizado − previsto | n/a | sem par completo |
| `cost_per_sellable_unit` | BRL/un | total do cálculo | quantidade vendável | sem sellable |
| `markup_percent` | % | fórmula 021 | custo-base | sem preço ou custo |
| `gross_margin` | % | fórmula 021 | preço | sem preço |
| `contribution_margin` | % | fórmula 021 | preço | variáveis ausentes |
| `price_coverage` | % | ingredientes com preço vigente | ingredientes ativos | universo vazio |
| `yield_coverage` | % | encerradas com rendimento | encerradas | sem encerradas |
| `nutrition_coverage` | % | versões com nutriente valorado | versões publicadas | sem publicadas |
| `compliance_coverage` | % | dossiês com avaliação | dossiês | sem dossiê; não é certificado |
| `data_coverage` | % | soma dos numeradores | soma dos denominadores | nenhuma cobertura |
| `blocking_occurrences` | count | ocorrências abertas bloqueantes | n/a | sem fato |

Agregação de coberturas soma numeradores e denominadores. Percentuais nunca são somados.
