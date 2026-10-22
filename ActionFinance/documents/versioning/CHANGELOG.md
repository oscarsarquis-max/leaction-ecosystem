# Changelog do ActionFinance

Mudanças perceptíveis ao usuário e notas técnicas necessárias. Estados honestos: planejada ≠ publicada.

## 0.1.0 — publicada (identificação existente)

Convenção da fundação, ainda servida em 09/10/2026 (`system/info`).

Perceptível (histórico acumulado até cadastros-017 / Pay listagem): autenticação OIDC; títulos a receber/pagar; baixas manuais; contas gerenciais; cadastros; sincronização de cobranças Hub via Spider (observação, sem baixa automática).

Notas técnicas: Flyway até V19 no origin na inspect 05/10/2026; SPA `index-BYEiixeg.js` reconfirmada 09/10/2026. Sem tag Git imutável desta publicação (limite histórico — não fabricada).

Não inclui: tesouraria MP, conciliação de extrato, posição de três bases, correção 019.

## Retificação 15/10/2026 — schema, sem versão nova de produto

O origin passou de Flyway V19 para V20 (`commercial_application` e colunas associadas). A imagem e o `version=0.1.0` não mudaram. Não é candidata 0.1.1 e não implementa a Tesouraria 023. Detalhe em REV_025.

## 0.1.1 — publicada em 15/10/2026

A lista de recebimentos passa a poder mostrar aplicação, descrição, pagador, método, processador, classificação e pago quando a origem confirma esses dados. Uma tentativa sem gravação nova deixa de aparecer como “nenhum item novo”. Schema permanece V20. Manifesto: [AF-0.1.1](manifests/AF-0.1.1-enriquecimento-recebimentos-027.md). Relato: [REV_027](../reviews/ACTIONFINANCE_REV_ENRIQUECIMENTO_RECEBIMENTOS_027.md). Aceite não atribuído.

Retificação no relato 028: antes da imagem 0.1.2 o banco já tinha uma tentativa SUCCESS com 1 incluído e 11 atualizados, 12 recebimentos de produção e 10 pendências pela regra da tela. O detalhe do pagamento de R$ 90 e a repetição idempotente continuam sem prova.

## 0.1.2 — publicada em 15/10/2026

A lista, os filtros, o resumo e o detalhe dos recebimentos passam a separar recebimento, pagador, pagamento, atualização na origem, valores, situação e ação. O sufixo comprovado `@amount.hub.local` deixa de aparecer como cliente e passa a «Pagador não identificado», com a referência técnica no detalhe. Schema e sincronização permanecem os de 0.1.1. Manifesto: [AF-0.1.2](manifests/AF-0.1.2-apresentacao-recebimentos-028.md). Relato: [REV_028](../reviews/ACTIONFINANCE_REV_APRESENTACAO_RECEBIMENTOS_028.md). Aceite visual não atribuído.

## 0.2.0 — publicada em 15/10/2026

Contas → Extrato recebe um CSV identificado, mostra a prévia, preserva todas as ocorrências do lote e consulta a observação. Sugestão de vínculo não quita recebimento. Não há saldo inicial, categoria nem iniciativa. O Prompt 030 impede confirmar ou somar quando a moeda não está comprovada. O Prompt 031 lê o relatório real de liquidação, no perfil `mp-settlement-v2-csv-1`. O Prompt 032 consolida evento só quando a identidade distingue e chama a soma de total parcial. O Prompt 034 publica a imagem e aplica V21–V23 depois de realinhar o checksum de V20. O arquivo real não foi importado. Manifesto: [AF-0.2.0](manifests/AF-0.2.0-extrato-t1-029.md). Relatos: [REV_029](../reviews/ACTIONFINANCE_REV_EXTRATO_T1_029.md), [REV_030](../reviews/ACTIONFINANCE_REV_ADEQUACAO_EXTRATO_030.md), [REV_031](../reviews/ACTIONFINANCE_REV_EXTRATO_REAL_031.md), [REV_032](../reviews/ACTIONFINANCE_REV_CONSOLIDACAO_EXTRATO_032.md), [REV_033](../reviews/ACTIONFINANCE_REV_BASE_REPRODUZIVEL_033.md), [REV_034](../reviews/ACTIONFINANCE_REV_PUBLICACAO_EXTRATO_034.md).

## 0.2.1 — publicada em 15/10/2026

A jornada Contas → Extrato fica legível: o próximo passo e o efeito da confirmação aparecem antes das linhas, o aviso repetido vira um resumo, e o detalhe abre pelo líquido e pela data do perfil. Valores, revisão e schema permanecem os de 0.2.0. O arquivo real não foi importado. Manifesto: [AF-0.2.1](manifests/AF-0.2.1-ux-extrato-035.md). Relato: [REV_035](../reviews/ACTIONFINANCE_REV_UX_EXTRATO_035.md). Aceite visual não atribuído.

## 0.2.2 — publicada em 15/10/2026

O extrato explica a conta ausente, importa com prévia e separa linhas elegíveis de ocorrências em revisão. Entradas, saídas, diferença e barras usam o mesmo conjunto elegível. Saldo, agenda e investimentos permanecem indisponíveis quando a base não os sustenta. Schema permanece V23. O arquivo real não foi importado. Manifesto: [AF-0.2.2](manifests/AF-0.2.2-extrato-fluxo-041.md). Relato: [REV_041](../reviews/ACTIONFINANCE_REV_EXTRATO_FLUXO_041.md). Aceite visual e financeiro não atribuído.

## 0.2.11 — publicada em 22/10/2026

Abrir uma conta em Tesouraria mostra Dados da conta: banco, modalidade, moeda, contatos e o caminho de acesso. Movimentações e o extrato continuam separados. Conta antiga permanece sem identificação até preenchimento explícito. Conexão automática continua indisponível. Schema V25. Servida em `actionfinance-web:28`, SPA `index-Dd2g04DF.js`. A imagem de retorno é a 0.2.10 em `actionfinance-web:27`. Aceite não atribuído. Relato: [REV_054R1](../reviews/ACTIONFINANCE_REV_PUBLICACAO_CONTAS_054R1.md).

## 0.2.10 — publicada em 16/10/2026

A conciliação passa a aplicar uma regra de rateio, relacionar um título pelo valor em reais, conciliar parte ou um grupo com o livro e desfazer com motivo. O histórico da classificação aparece no movimento. A agenda e o extrato permanecem os da 0.2.9. Schema permanece V24. Servida em `actionfinance-web:27`, SPA `index-Dgo58fLv.js`. A imagem de retorno é a 0.2.9. O arquivo real não foi importado. Aceite não atribuído. Relato: [REV_053](../reviews/ACTIONFINANCE_REV_PROVA_JORNADA_053.md).

## 0.2.9 — publicada em 16/10/2026

A agenda abre num calendário mensal. Cada data com compromisso mostra, em separado, o que há a receber e o que há a pagar, com ícone, quantidade e valor restante. A legenda fica junto da grade. A diferença prevista do mês não é saldo bancário. A vista em lista e os links antigos com faixa continuam válidos. Schema permanece V24. Servida em `actionfinance-web:26`, SPA `index-Ywb7z5Cf.js`. A imagem de retorno é a 0.2.8. O arquivo real não foi importado. Aceite não atribuído. Relato: [REV_052](../reviews/ACTIONFINANCE_REV_AGENDA_CALENDARIO_052.md).

## 0.2.8 — publicada em 16/10/2026

Classificação confirmada do extrato, rateio, conciliação do livro separada da referência comercial, resumo operacional da tesouraria e agenda dos títulos em aberto. Recebimentos e pagamentos passam a usar a composição de dois terços e um terço, inclusive formulário, detalhe e baixa. A posição é a soma das contas ativas em real com saldo inicial já aplicável na data; conta sem cobertura não aparece como R$ 0,00. Ainda não há posição informada pela fonte, conta prevista no compromisso, fluxo projetado nem análise. O arquivo real não foi importado. Aceite não atribuído.

## 0.2.7 — publicada em 16/10/2026

A barra principal passa a Tesouraria, Recebimentos, Pagamentos e Cadastros. Tesouraria reúne Contas e Extratos. Em Recebimentos, o item visível quando a integração está ligada chama-se Recebimentos integrados e explica que a lista vem da origem, sem ser extrato nem valor conciliado. As rotas públicas permanecem. Visão geral, conciliação, fluxo, análise, iniciativas e rateios ficam para as entregas descritas na baseline 1.3. Schema permanece V23. O arquivo real não foi importado. Manifesto: [AF-0.2.7](manifests/AF-0.2.7-navegacao-tesouraria-048.md). Relato: [REV_048](../reviews/ACTIONFINANCE_REV_NAVEGACAO_TESOURARIA_048.md). Aceite não atribuído.

## 0.2.6 — publicada em 16/10/2026

A lista, o cadastro e o detalhe das contas financeiras passam a usar a mesma composição da prévia aprovada. O detalhe separa os movimentos do Finance da posição e do relatório importado. Sem saldo inicial, a posição fica «Não apurada» uma vez. O modelo não guarda instituição, e a tela deixa de inventar esse dado. Schema permanece V23. O arquivo real não foi importado. Manifesto: [AF-0.2.6](manifests/AF-0.2.6-contas-padrao-visual-047.md). Relato: [REV_047](../reviews/ACTIONFINANCE_REV_CONTAS_PADRAO_VISUAL_047.md). Aceite não atribuído.

## 0.2.5 — publicada em 16/10/2026

A prévia do extrato segue a composição aprovada: linhas à esquerda, decisão à direita, abas Prontas e Em revisão, e o detalhe no lugar da decisão. A lista depois de importar permanece a da 0.2.4. O arquivo real não foi importado. Manifesto: [AF-0.2.5](manifests/AF-0.2.5-previa-aprovada-046.md). Relato: [REV_046](../reviews/ACTIONFINANCE_REV_PREVIA_APROVADA_046.md). Aceite não atribuído.

## 0.2.4 — publicada em 15/10/2026

O extrato passa a seguir o projeto Fluxo: cartão branco, abas com contagem, tabela e análise lado a lado, gráfico com escala e detalhe no lugar da análise. A leitura do relatório continua antes do vínculo, e saldo desconhecido continua «Não apurado». O arquivo real não foi importado. Manifesto: [AF-0.2.4](manifests/AF-0.2.4-projeto-extrato-044.md). Relato: [REV_044](../reviews/ACTIONFINANCE_REV_PROJETO_EXTRATO_044.md). Aceite não atribuído.

## 0.2.3 — publicada em 15/10/2026

O extrato lê o relatório antes de pedir vínculo. Se a identificação confere, segue a prévia; se falta, pede confirmação da conta; se diverge, não troca o vínculo. Sem saldo inicial, os indicadores dizem «Não apurado» em vez de R$ 0,00. Um zero informado continua zero. O arquivo real não foi importado. Manifesto: [AF-0.2.3](manifests/AF-0.2.3-desbloqueio-importacao-043.md). Relato: [REV_043](../reviews/ACTIONFINANCE_REV_DESBLOQUEIO_IMPORTACAO_043.md). Aceite não atribuído.

## Não lançado

| Versão | Estado | Motivo |
|---|---|---|
| 1.0.0 | Recusada como rótulo atual | Plataforma incompleta; 024 proíbe chamar de 1.0 só por versionar |
| 0.2.10 | Publicada; carga de extrato não feita | Rateio, conciliação do livro e desfazer na própria tela. O relatório do proprietário não foi importado |
| 0.2.9 | Publicada; carga de extrato não feita | Agenda mensal de recebimentos e pagamentos. O relatório do proprietário não foi importado |
| 0.2.8 | Publicada; carga de extrato não feita | Classificação, conciliação e resumo da tesouraria. O relatório do proprietário não foi importado |
| 0.2.7 | Publicada; carga de extrato não feita | Navegação da tesouraria. O relatório do proprietário não foi importado |
| 0.2.6 | Publicada; substituída no ar por 0.2.7; carga de extrato não feita | Contas na composição aprovada. O relatório do proprietário não foi importado |
| 0.2.5 | Publicada; substituída no ar por 0.2.6; carga de extrato não feita | Prévia na composição aprovada. O relatório do proprietário não foi importado |
| 0.2.4 | Publicada; substituída no ar por 0.2.5; carga de extrato não feita | Extrato no sistema visual Fluxo. O relatório do proprietário não foi importado |

AF-BL-023 1.0 entra como **requisito**, sem linha de produto nova.
