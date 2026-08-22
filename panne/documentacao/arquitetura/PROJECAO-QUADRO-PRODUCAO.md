# Projeção do quadro de produção

`GET .../production/board` lê ordens, bateladas, plano, produto, dependências, ocorrências e etapas. **Não há tabela paralela.**

Filtros: data ou intervalo ≤ 7 dias, estabelecimento, turno, produto, estado, prioridade, código/texto limitado. Estação/área não tem coluna — o parâmetro `area` filtra o código público.

A resposta inclui quantidade/alvo, horários, estados, etapa atual, bloqueios, ocorrências abertas, atraso determinístico (`planned_end_at < agora` e não terminal), próxima ação permitida (permissão ∩ estado) e `row_version`. Sem custos.
