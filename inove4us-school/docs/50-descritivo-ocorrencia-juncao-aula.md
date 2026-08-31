# Descritivo — Registro de Ocorrência + Junção de Aulas

Paliativo do “Split de Aulas / Efeito Cascata”. Sem motor automático. Decisões fechadas em 2026-08-14.

## Objetivo do card (3.1)

Campo real: `kanban_state.tarefas[].objetivo` (card da metodologia). Não é PEI. Não é `objetivo_aprendizagem` da aula Dia a Dia.

## Fechamento

Estende o relato atual (`RelatoAulaModal` ao concluir / último card em Pronto). Padrão: **Concluída** (comportamento antigo).

## Próxima aula do mesmo fio (0.3)

Mesma `turma` + `disciplina_id`. Mesmo assunto se `plano_session`, `desafio_id` ou `tema` coincidirem quando os dois lados tiverem o campo. “Próxima” = primeira aula desse fio com `data_evento` depois da pendente.

## Resoluções manuais (só na próxima aula)

- Juntar objetivos (união no card que absorve; pendente `concluida_via_juncao`).
- Agendar continuação em horário escolhido (aula nova, `continuacao_origem_id`).

Se o professor não fizer nada, a aula permanece `aguardando_continuacao`.
