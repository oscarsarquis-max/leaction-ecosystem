# Quadro e filtros

`GET /production/board` projetado em tabela densa (não Kanban): o quadro é agenda operacional, não funil.

Filtros em faixa horizontal, persistidos na URL: data, estabelecimento, turno, área/estação, produto, estado, prioridade, código/texto.

Estados: carregamento, vazio, erro, sucesso. Botão atualizar e horário da última carga. Sem polling.

Cartão/linha: produto, ordem, batelada, alvo, horário, estado (texto+badge), etapa, bloqueio, ocorrência, atraso, próxima ação. Clique abre o detalhe. Sem custos.
