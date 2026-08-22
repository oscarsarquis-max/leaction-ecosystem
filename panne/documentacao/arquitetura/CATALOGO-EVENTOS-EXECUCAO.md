# Catálogo de eventos — execução

Schemas fechados em `production_execution.constants.EVENT_PAYLOADS`, mesclados ao validador de `production_event`. Extra ou falta de campo rejeita. Idempotência: mesma chave e payload devolvem o anterior; payload diferente falha.

Novos tipos: `execution.policy_set`, `weighing.session_*`, `weighing.recorded`, `weighing.verified`, `consumption.recorded`, `step.transitioned`, `order.in_weighing` (transição via sessão), `order.ready`, `order.resumed`, `order.completed`, `order.short_closed`, `batch.status_changed`, `yield.recorded`, `occurrence.recorded`, `occurrence.resolved`, `dependency.overridden`, `sheet.issued`.

`order.released` (0010) ganhou `policy_hash`. Eventos 0010 restantes intactos.
