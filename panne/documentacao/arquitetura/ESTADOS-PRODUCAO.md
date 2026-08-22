# Máquinas de estados de produção

Quatro máquinas separadas. Nomes dos candidatos da ordem foram **revisados**: `planned` cede a `scheduled` (não confundir com o plano); `partially_completed` cede a `short_closed`; `weighing` permanece como `in_weighing`.

Atores usam papéis atuais sem alterar o esquema: planejador ≈ `production` / `production_manager`; padeiro ≈ `baker_operator`; líder pode ser o mesmo `production_manager`; cancelamento sensível também `organization_admin` / `owner`.

## Plano

| Estado | Finalidade |
|---|---|
| `open` | Montagem do recorte |
| `locked` | Recorte fechado; ordens podem ser liberadas |
| `archived` | Recorte encerrado |

`open` → `locked` (planejador; há pelo menos um item). `locked` → `open` só com motivo (reabertura). Sem exclusão.

Impacto: quadro do dia só lista planos `locked` ou `open` do recorte; arquivo some do quadro operacional.

## Ordem

| Estado | Finalidade | Impressão | Quadro |
|---|---|---|---|
| `draft` | Montagem | não | oculto ou “rascunho” só para planejador |
| `scheduled` | No plano, ainda sem snapshot | não oficial | fila do planejador |
| `released` | Snapshot congelado | emitível | visível |
| `in_weighing` | Separação em curso | válida | “pesar” |
| `ready` | Materiais conferidos | válida | “pronto para fazer” |
| `in_progress` | Etapas em curso | válida | em execução |
| `on_hold` | Pausa | válida, marcada | bloqueio |
| `completed` | Encerrada com alvo cumprido | histórica | some do operacional |
| `short_closed` | Encerrada abaixo do alvo | histórica | some; motivo visível na rastreio |
| `cancelled` | Não executar | **inválida** | some; emissão recusada |

### Transições

| De → para | Ator | Pré-condição | Evento | Reversível | Motivo |
|---|---|---|---|---|---|
| draft → scheduled | planejador | produto, versão candidata, estabelecimento | `order.scheduled` | sim (voltar a draft) | não |
| scheduled → released | planejador | versão **aprovada**; escala ok | `order.released` | não edita snapshot; só cancelar | não |
| released → in_weighing | padeiro | emissão ou início digital | `weighing.started` | não | não |
| in_weighing → ready | padeiro | conferência ok ou aceita com ocorrência | `weighing.completed` | não | se houve falta |
| ready → in_progress | padeiro | primeira etapa | `order.started` | não | não |
| * → on_hold | padeiro/líder | ordem ativa | `order.held` | sim (resume) | **sim** |
| on_hold → estado anterior ativo | líder | motivo da pausa tratado | `order.resumed` | — | sim |
| in_progress → completed | líder | bateladas finais ok | `order.completed` | não | não |
| in_progress → short_closed | líder | alvo não cumprido | `order.short_closed` | não | **sim** |
| draft/scheduled/released/on_hold → cancelled | planejador/admin | — | `order.cancelled` | reabrir só cria **nova** ordem ou estado `scheduled` com histórico | **sim** |
| cancelled → (não volta) | — | — | — | reabertura gera nova ordem ligada à antiga | — |

`released` → `in_progress` direto é permitido se a pesagem for implícita (padaria pequena); o evento deve registrar o atalho.

## Batelada

`pending` → `in_weighing` → `in_progress` → `completed` | `scrapped` | `cancelled`.

Pausa da ordem coloca bateladas ativas em `on_hold`. Uma batelada `scrapped` não conclui a ordem sozinha.

## Execução de etapa

`pending` → `running` → `done` | `skipped`. `running` → `paused` → `running`.

`skipped` exige motivo. Tempo real é evento, não overwrite do previsto.
