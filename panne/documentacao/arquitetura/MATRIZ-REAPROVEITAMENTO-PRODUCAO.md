# Matriz — estado atual da Panne frente ao chão de fábrica

Ciclo: CURSOR-011. Somente leitura do modelo 0001–0009.

| Conceito atual | Classificação | Nota |
|---|---|---|
| `organization`, `establishment` | aproveitável | Ordem e quadro nascem no estabelecimento, isolados pela org |
| `app_user`, `organization_membership`, papéis, permissões | estender | Permissões de produção são novas; um papel por associação pode ser insuficiente |
| RLS + contexto transacional | aproveitável | Mesmo padrão GUC; tabelas novas de produção serão organizacionais |
| `ingredient` / `ingredient_version` | aproveitável | Referência do snapshot; a ordem não aponta a versão viva depois da liberação |
| `supplier`, `supplier_item_price` | separado | Preço alimenta custo futuro, não o quadro do padeiro |
| `technical_product` | aproveitável | Identidade do produto no plano e na ordem |
| `formulation` / `formulation_version` aprovada | aproveitável | Pré-condição da liberação |
| `formulation_item`, `process_step` | estender | Copiados para snapshot na liberação; a receita viva continua no lab |
| `scale_calculation` | aproveitável | Motor determinístico; a ordem guarda o resultado, não o recalcula na execução |
| `trial` / `trial_measurement` | **separado** | Ensaio de formulação, não ordem de fábrica (ver abaixo) |
| `approval` | aproveitável | Evidência de que a versão pode ser liberada para produção |
| nutrição / conformidade | separado | Podem gerar alertas na ficha; não dirigem o quadro |
| `audit_event` | estender | Eventos de produção têm agregado próprio; a trilha crítica é append-only |
| plano, ordem, batelada, pesagem, ficha emitida, consumo real | **lacuna** | Inexistentes |

## `trial` não é ordem de produção

| | `trial` | Ordem de produção (proposta) |
|---|---|---|
| Finalidade | Validar ou ajustar uma formulação | Cumprir demanda de um turno/estabelecimento |
| Ciclo de vida | `planned` → execução pontual → medições | Máquina própria (rascunho → liberada → pesagem → execução → conclusão/cancelamento) |
| Quantidade | Experimental | Snapshot escalado para a demanda |
| Quadro / ficha de fábrica | Não | Sim |
| Pode usar versão não publicada | Sim, no lab | Não; só versão aprovada |
| Relatórios de fábrica | Não | Projeções derivadas de eventos |

Reutilizar `trial` como ordem misturaria lab e chão de fábrica e quebraria os invariantes 1, 4 e 11.
