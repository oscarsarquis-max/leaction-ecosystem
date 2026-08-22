# Estados e comandos implementados (0011)

Complementa [ESTADOS-E-COMANDOS-0010](ESTADOS-E-COMANDOS-0010.md).

## Política

`set_execution_policy` em `draft`/`scheduled`. Congelada em `release_order`.

## Pesagem

`open_weighing_session`, `record_weighing`, `reverse_weighing`, `correct_weighing`, `verify_weighing`, `complete_weighing_session`, `cancel_weighing_session`.

## Consumo, etapa, rendimento, ocorrência

`record_consumption`; `mark_step_ready`, `start_step`, `hold_step`, `resume_step`, `complete_step`, `skip_step`, `cancel_step`; `record_yield`, `reverse_yield`; `record_occurrence`, `resolve_occurrence`.

## Ciclo da ordem

`mark_order_ready`, `resume_order`, `complete_batch`, `complete_order`, `short_close_order`, `override_dependency`, `issue_sheet`.

`hold_order` e `cancel_order` da 0010 foram adaptados (mais origens de pausa; cancelamento incompatível com fatos).
