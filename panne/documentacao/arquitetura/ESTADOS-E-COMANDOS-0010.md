# Estados e comandos implementados (0010)

## Plano

`draft` → `scheduled`. Catálogo também tem `archived` (sem comando).

Comandos: `create_plan`, `upsert_plan_item`, `schedule_plan`.

## Ordem

Implementados: `draft` → `scheduled` → `released` → `on_hold` | `cancelled`.  
`cancelled` → nova ordem substituta (`draft`).

No catálogo 0010, sem comando: `in_weighing`, `ready`, `in_progress`, `completed`, `short_closed`.  
Comandos desses estados: ciclo [0011](ESTADOS-E-COMANDOS-0011.md).

Comandos: `create_order`, `schedule_order`, `add_dependency`, `split_batches`, `release_order`, `hold_order`, `cancel_order`, `create_substitute_order`.

Transição inválida falha com `transicao_invalida`. Pesagem, início, consumo e conclusão **não** existem neste ciclo.

## Batelada

Criada em `pending`. Demais estados só no catálogo.
