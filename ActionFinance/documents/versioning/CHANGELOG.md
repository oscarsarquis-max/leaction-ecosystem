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

## 0.2.4 — publicada em 15/10/2026

O extrato passa a seguir o projeto Fluxo: cartão branco, abas com contagem, tabela e análise lado a lado, gráfico com escala e detalhe no lugar da análise. A leitura do relatório continua antes do vínculo, e saldo desconhecido continua «Não apurado». O arquivo real não foi importado. Manifesto: [AF-0.2.4](manifests/AF-0.2.4-projeto-extrato-044.md). Relato: [REV_044](../reviews/ACTIONFINANCE_REV_PROJETO_EXTRATO_044.md). Aceite não atribuído.

## 0.2.3 — publicada em 15/10/2026

O extrato lê o relatório antes de pedir vínculo. Se a identificação confere, segue a prévia; se falta, pede confirmação da conta; se diverge, não troca o vínculo. Sem saldo inicial, os indicadores dizem «Não apurado» em vez de R$ 0,00. Um zero informado continua zero. O arquivo real não foi importado. Manifesto: [AF-0.2.3](manifests/AF-0.2.3-desbloqueio-importacao-043.md). Relato: [REV_043](../reviews/ACTIONFINANCE_REV_DESBLOQUEIO_IMPORTACAO_043.md). Aceite não atribuído.

## Não lançado

| Versão | Estado | Motivo |
|---|---|---|
| 1.0.0 | Recusada como rótulo atual | Plataforma incompleta; 024 proíbe chamar de 1.0 só por versionar |
| 0.2.4 | Publicada; carga de extrato não feita | Extrato no sistema visual Fluxo. O relatório do proprietário não foi importado |

AF-BL-023 1.0 entra como **requisito**, sem linha de produto nova.
