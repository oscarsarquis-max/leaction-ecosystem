# Matriz de atendimento — AF-BL-023 revisão 1.3

09/11/2026. O corpo do plano e do projeto 023 R1_3 não foi editado. Esta matriz diz o que as reviews 049 a 054R1 entregaram e o que segue pendente. O artefato no ar é o **0.2.11**, schema **V25**, conferido em [REV_055](../reviews/ACTIONFINANCE_REV_ESTADO_PUBLICADO_055.md). Aceite do proprietário não atribuído. O extrato real ainda não foi carregado.

| Capacidade | Estado (entregue/publicado/pendente) | Evidência (relato) |
|---|---|---|
| Classificação confirmada do evento de extrato | publicado | [REV_049](../reviews/ACTIONFINANCE_REV_CLASSIFICACAO_CONCILIACAO_049.md), fechada no ar em [REV_051](../reviews/ACTIONFINANCE_REV_FECHAMENTO_049_050_051.md); a tela foi percorrida em [REV_053](../reviews/ACTIONFINANCE_REV_PROVA_JORNADA_053.md) |
| Rateio com regra vigente e resíduo na maior participação | publicado | REV_049; a regra 50/50 e o resíduo de R$ 0,01 foram vistos na tela em REV_053 |
| Conciliação do livro, parcial ou em grupo, e desfazer | publicado | REV_049; REV_053 percorreu conferir, agrupar, desfazer e invalidar depois do estorno da baixa |
| Referência comercial separada do livro, sem baixar o título | publicado | REV_049; REV_053 manteve o título em aberto depois da referência |
| Resumo da tesouraria | publicado | [REV_050](../reviews/ACTIONFINANCE_REV_JORNADA_FINANCEIRA_INTEGRADA_050.md), publicado em REV_051 (0.2.8) |
| Posição gerencial das contas ativas em real, com saldo inicial já aplicável; desconhecido distinto de zero | publicado | REV_050 e REV_051. Não é saldo informado pela fonte |
| Agenda dos títulos em aberto e calendário mensal | publicado | REV_050; calendário em [REV_052](../reviews/ACTIONFINANCE_REV_AGENDA_CALENDARIO_052.md) (0.2.9). A diferença prevista do mês não é saldo bancário |
| Recebimentos e pagamentos na composição de dois terços e um terço | publicado | REV_050, publicado em REV_051 |
| Dados da conta: banco, modalidade, moeda, contatos e caminho de acesso | publicado | [REV_054](../reviews/ACTIONFINANCE_REV_DADOS_CONTAS_054.md) ficou sem publicar; [REV_054R1](../reviews/ACTIONFINANCE_REV_PUBLICACAO_CONTAS_054R1.md) publicou em 0.2.11 / V25. REV_055 reviu o mesmo artefato em 09/11/2026 |
| Posição pela fonte | pendente | REV_051: posição informada pela fonte não foi feita. O projeto 1.3, seção 7, continua sendo o requisito |
| Conta nos compromissos | pendente | REV_050: o compromisso em aberto diz que a conta ainda não está definida. REV_051: conta prevista no compromisso não foi feita |
| Fluxo projetado | pendente | REV_051. O projeto 1.3, seção 8, pede a projeção até 13 semanas; não há página de fluxo |
| Cenários | pendente | REV_051 não anuncia projeção. O projeto 1.3, seção 8, pede cenários nomeados; cenário sem nome não entra como previsão |
| Análise | pendente | REV_051: análise e planejamento não foram feitos. O plano 1.3 não abre página vazia de análise |
| Conector bancário | pendente | REV_054 e REV_054R1: conexão automática continua indisponível. O extrato entra por arquivo. A demanda [001](../integrations/ACTIONFINANCE_DEMANDA_SPIDER_001.md) deixa o extrato automático da conta para uma demanda própria |
