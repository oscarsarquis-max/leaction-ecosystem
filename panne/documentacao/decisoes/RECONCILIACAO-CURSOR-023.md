# Reconciliação CURSOR-023

| Fato existente | Fato novo | Vínculo | Granularidade | Autoridade | Impacto histórico | Estratégia pré-0020 |
|---|---|---|---|---|---|---|
| `ingredient` + versões + unidade | `inventory_item` | `ingredient_id` | 1 item estocável por ingrediente organizacional | catálogo de ingredientes | nenhum | criar item sob comando humano |
| `supplier`, `supplier_item`, `supplier_item_price` | cotação, pedido, preço observado | FKs opcionais | preço canônico permanece no cadastro | cadastro de preços | nenhum | preço observado só com comando |
| conversões `measurement_unit` | quantidade canônica do movimento | `convert_to_canonical_mass` | Decimal | motor de unidades | nenhum | recusar massa↔volume |
| formulação / escala | demanda planejada da reposição | `ProductionOrderMaterial` | ordem liberada | produção | nenhum | ausência explícita se não houver |
| plano, ordem, batelada, snapshot | reserva e separação | `production_order_id` | ordem / batelada | produção para o fato; estoque para a reserva | sem reserva retroativa | adoção humana |
| pesagem | — | não vira movimento | pesagem ≠ estoque | execução | nenhum | não postar |
| `production_material_consumption` | `inventory_consumption_posting` | consumo id | 1 postagem por consumo | execução soberana | nenhum | não reinterpretar |
| eventos / rastreabilidade | projeção estendida | origem + hash | evento | produção + estoque | só novos nós | sem segunda fonte |
| política de custo 021 | fronteira explícita | nenhum cálculo | — | custos soberanos | nenhum | movimento sem valoração |
| relatórios 022 | relatório `inventory` | mesmo motor | período | reporting.inventory.read | catálogo v2 | ausência ≠ zero |
| permissões / RLS | permissões 023 | `permission` | org | runtime | seed 0020 | default deny |

Não se copiam ingredientes, fornecedores, ordens, consumos ou preços.
