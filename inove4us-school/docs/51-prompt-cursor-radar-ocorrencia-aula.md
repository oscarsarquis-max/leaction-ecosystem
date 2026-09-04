# Prompt companheiro — Radar (ocorrência de aula)

Estende o espelho existente (`school_planos_aula_espelhados.mesa_payload_json`). Sem pipeline novo.

## Payload B2C (`mesa.ocorrencia`) — nomes reais do `inove4us-26`

- `tipo`: `concluida` | `interrompida` | `substituicao` | `trabalho_monitorado`
- `nota`: texto livre do professor
- `resolucao` / `status`: `aguardando_continuacao` | `concluida_via_juncao` | `agendada_continuacao` | `normal`
- `aguardando_continuacao` (bool)
- `juncao_destino_id` + `juncao_destino_data` (aula que absorveu)
- `juncao_origem_id` + `juncao_origem_data` (aula absorvida — no destino)
- `continuacao_origem_id` + `continuacao_origem_data`
- `continuacao_destino_id` + `continuacao_destino_data`
- `unida` (bool)

Atualização: mesmo `LESSON_RECORD_SYNC` de sempre. Sem coluna nova, sem tabela nova.

## Radar

Selo na Lista, Agenda e Linha do Tempo. Ao abrir o espelho: nota + “Unida com a aula de [data]” / “Continuação de [data]”. Aula sem ocorrência não muda.
