# Conclusão e short_closed

## `completed`

Exige: pesagem concluída ou dispensa (`optional`/`not_applicable`); conferências obrigatórias aceitas; etapas obrigatórias `completed` ou `skipped`; ao menos um consumo; rendimento calculável; sem ocorrência bloqueante aberta; dependências satisfeitas; permissão `production.order.complete`; desvio percentual do alvo ≤ tolerância de conclusão.

## `short_closed`

Não é conclusão normal. Exige política `allow_short_close`, permissão `production.order.short_close`, motivo, resultado incompleto ou fora do alvo. Preserva fatos. Evento `order.short_closed`. Bateladas abertas passam a `short_closed`.

Predecessor `short_closed` bloqueia a dependente `preferment`/`intermediate` até override humano auditável. Predecessor `cancelled` bloqueia sem override.
