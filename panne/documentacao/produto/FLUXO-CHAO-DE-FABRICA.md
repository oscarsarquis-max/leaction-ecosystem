# Mapa do fluxo operacional

`demanda → plano → ordem → batelada → separação/pesagem → execução → apontamentos → conclusão → projeções`

Digital e impresso leem a **mesma ordem**. Cálculo de escala é determinístico (motor já existente). IA não transita estados.

## Etapas

| Etapa | Ator | Entrada | Decisão | Saída | Comando | Evento | Evidência |
|---|---|---|---|---|---|---|---|
| Demanda | comercial / produção / sistema | pedido, previsão, falta | incluir no plano ou recusar | item de demanda | `register_demand` | `demand.registered` | quantidade, data, produto |
| Plano | `production_manager` | demandas do recorte | caber no turno/estação | `ProductionPlan` | `compose_plan` | `plan.composed` | data, turno, estabelecimento |
| Ordem | planejador | item do plano + versão aprovada | qual versão e quantas peças | ordem `draft`/`scheduled` | `create_order` | `order.created` | produto, versão, alvo |
| Liberação | planejador / responsável técnico | ordem agendada + escala | congelar snapshot | ordem `released` + ficha emitível | `release_order` | `order.released` | snapshot formulação/escala |
| Batelada | planejador ou sistema | ordem liberada | partir em ciclos de equipamento | `ProductionBatch` | `split_batches` | `batch.created` | capacidade masseira/forno |
| Separação | `baker_operator` | materiais planejados | conferir, faltar ou substituir | checklist | `start_weighing` / `record_shortage` | `weighing.started` / `material.short` | peso, lote, operador |
| Execução | padeiro | etapas do snapshot | iniciar, pausar, retomar | etapa em curso | `start_step` / `hold_order` | `step.started` / `order.held` | horário, estação |
| Apontamentos | padeiro / líder | fatos do turno | registrar consumo, perda, ocorrência | realizado | `record_consumption` / `record_occurrence` | `consumption.recorded` | valor, motivo |
| Conclusão | líder / planejador | bateladas | concluir, concluir parcial, retrabalho | estado terminal | `complete_order` / `short_close` | `order.completed` | quantidade vendável |
| Projeções | leitura | eventos | nenhum | quadro, ficha, relatórios | — | — | derivado |

## Situações especiais

- **Pré-fermento no dia anterior:** ordem ou batelada com data de início ≠ data de venda; dependência visível no quadro.
- **Preparação intermediária:** ordem filha ou batelada de componente; não vira `trial`.
- **Entre turnos:** a ordem permanece; o quadro filtra o recorte.
- **Capacidade:** batelada respeita masseira/forno; excesso gera nova batelada, não “esticar” a ordem.
- **Mudança após liberação:** não edita o snapshot; cancela e cria nova ordem, ou ocorrência + reabertura com motivo.
- **Falta / substituição:** ocorrência; substituição só com permissão e novo material apontado; planejado permanece.
- **Retrabalho / descarte:** eventos; não apagam consumo anterior.
- **Conclusão parcial:** estado próprio (`short_closed`), motivo obrigatório.
- **Vários estabelecimentos:** uma ordem, um estabelecimento; o plano não cruza org.
- **Conexão instável / papel:** ver contingência; a fonte continua a ordem.

Cancelamento e reabertura **nunca** apagam eventos. Motivo é obrigatório.
