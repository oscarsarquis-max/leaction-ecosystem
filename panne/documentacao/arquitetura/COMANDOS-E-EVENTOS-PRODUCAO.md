# Comandos e eventos de produção

Comando = intenção autenticada. Evento = fato append-only. Relatórios e quadro **só leem eventos** (e o estado projetado da ordem).

| Comando | Evento | Agregado | Quem (papéis atuais) |
|---|---|---|---|
| `register_demand` | `demand.registered` | plano/item | commercial, production_manager |
| `compose_plan` | `plan.composed` | plano | production_manager |
| `lock_plan` | `plan.locked` | plano | production_manager |
| `create_order` | `order.created` | ordem | production_manager |
| `schedule_order` | `order.scheduled` | ordem | production_manager |
| `release_order` | `order.released` | ordem | production_manager (+ technical_responsible se política exigir) |
| `split_batches` | `batch.created` | batelada | production_manager |
| `issue_ticket` | `ticket.issued` | emissão | production_manager, baker_operator |
| `start_weighing` | `weighing.started` | ordem/batelada | baker_operator |
| `record_check` | `weighing.checked` | conferência | baker_operator |
| `record_shortage` | `material.short` | ocorrência | baker_operator |
| `substitute_material` | `material.substituted` | ocorrência | production_manager |
| `start_step` | `step.started` | etapa | baker_operator |
| `finish_step` | `step.finished` | etapa | baker_operator |
| `hold_order` | `order.held` | ordem | baker_operator, production_manager |
| `resume_order` | `order.resumed` | ordem | production_manager |
| `record_consumption` | `consumption.recorded` | consumo | baker_operator |
| `record_yield` | `yield.recorded` | rendimento | baker_operator, production_manager |
| `record_occurrence` | `occurrence.recorded` | ocorrência | baker_operator |
| `scrap_batch` | `batch.scrapped` | batelada | production_manager |
| `complete_order` | `order.completed` | ordem | production_manager |
| `short_close_order` | `order.short_closed` | ordem | production_manager |
| `cancel_order` | `order.cancelled` | ordem | production_manager, organization_admin |

IA: nenhum comando desta lista. Cálculo de escala: motor existente, sem modelo.

Idempotência: o mesmo comando com a mesma correlação não gera segundo efeito (evita toque duplo no tablet).
