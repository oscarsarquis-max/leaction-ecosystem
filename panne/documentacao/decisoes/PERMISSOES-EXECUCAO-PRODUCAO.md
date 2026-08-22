# Permissões de execução

Novas (semente só na `0011`, `ON CONFLICT` implícito via `NOT EXISTS`):

`production.weighing.record`, `weighing.verify`, `consumption.record`, `step.execute`, `occurrence.record`, `occurrence.resolve`, `batch.complete`, `order.complete`, `order.short_close`, `sheet.issue`, `traceability.read`.

Atribuição: padeiro opera pesagem/consumo/etapa/ocorrência e lê rastreio; gestor resolve, conclui, encerra e emite; técnico lê plano/ordem/quadro e rastreio. Sem `costing.read`.

**Limitação de um papel por associação:** não alterada. Não há papel `conferente`. Quem confere usa `baker_operator` (ou gestor) e o domínio recusa autoconferência. Padeiro que também libera continua precisando de outra associação/papel.
