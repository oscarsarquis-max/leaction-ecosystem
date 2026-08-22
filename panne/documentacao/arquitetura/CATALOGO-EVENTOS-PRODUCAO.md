# Catálogo de eventos de produção (0010)

Envelope: tipo, comando, ator, instante do servidor, correlação, causação, idempotency key, payload validado, digest, `sequence_no` estável. Append-only. Sem custos no payload.

| Evento | Comando | Payload |
|---|---|---|
| `plan.created` | `create_plan` | public_code, operational_date, shift |
| `plan.item_upserted` | `upsert_plan_item` | plan_item_id, technical_product_id, sort_order |
| `plan.scheduled` | `schedule_plan` | public_code |
| `order.created` | `create_order` | public_code, technical_product_id, target_mode |
| `order.scheduled` | `schedule_order` | public_code |
| `dependency.added` | `add_dependency` | dependency_id, predecessor_order_id, dependency_type |
| `batch.split` | `split_batches` | batch_count, method |
| `order.released` | `release_order` | public_code, hashes |
| `order.held` | `hold_order` | reason |
| `order.cancelled` | `cancel_order` | reason |
| `order.substituted` | `create_substitute_order` | substitute_order_id, public_code |

Tipo desconhecido ou campo extra: recusado. Mesma chave + comando diferente ou payload diferente: `idempotencia_conflito`.
