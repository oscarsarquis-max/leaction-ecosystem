# Perdas, rendimento e retrabalho

| Conceito | Fonte | Tratamento |
|---|---|---|
| Consumo | `consume` / correção | entra no líquido |
| Retorno | `return` | reduz o líquido se a política incluir |
| Desperdício | `waste` | categoria própria; não é retorno |
| Sobra | `project_yield.leftover` | distinguida; sem valoração automática |
| Descarte | `project_yield.scrap` | distinguido; sem valoração automática |
| Retrabalho | premissa `rework` | não há entidade operacional neste ciclo |
| Vendável | `sellable_units` | único denominador do custo vendável |

Sem rendimento final confiável: total pode existir; custo vendável ausente.
