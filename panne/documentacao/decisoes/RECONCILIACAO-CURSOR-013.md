# Reconciliação CURSOR-013

Incompatibilidades documentadas **antes** da migração `0011`, confrontando o prompt com o head `0010_production_planning`.

| Tema | Estado em 0010 | Prompt 013 | Decisão |
|---|---|---|---|
| Ordens já liberadas | Podem existir sem política nem pesagem | Não inventar que foram pesadas | Liberação nova exige política. Ordens antigas sem política não ganham fatos retroativos |
| `hold_order` | Só a partir de `released` | Pausa também em execução | `released`, `in_weighing`, `ready`, `in_progress` → `on_hold`; `held_from_status` para retomar |
| Batelada `ready` | Fora do CHECK 0010 | Ordem passa por `ready` | 0011 amplia o catálogo da batelada com `ready` e `short_closed` |
| Cancelamento | `released`/`on_hold` sem fatos | Produção iniciada não vira cancelamento vazio | Cancelamento recusado se houver pesagem, consumo, etapa, rendimento ou ocorrência |
| Padeiro | Só leitura de ordem/quadro | Pesagem, consumo, etapa, ocorrência | Permissões novas na `0011`; autoconferência bloqueada no domínio |
| Um papel por associação | Preservado | Não alterar salvo bloqueio técnico | Preservado. Conferente = mesmo papel `baker_operator` + regra de ator distinto |
| Evento `order.released` | Quatro hashes | Congelar política | Campo fechado `policy_hash` adicionado |
| Estoque / custo / HTTP / PDF | Fora | Fora | Permanece fora |

Estados catalogados na 0010 **sem comandos** e agora implementados: ordem `in_weighing`, `ready`, `in_progress`, `completed`, `short_closed`; batelada `in_weighing`, `ready`, `in_progress`, `on_hold`, `completed`, `cancelled` (via encerramento). `scrapped` continua só catálogo.
