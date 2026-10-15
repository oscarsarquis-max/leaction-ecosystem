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

A lista de recebimentos passa a poder mostrar aplicação, descrição, pagador, método, processador, classificação e pago quando a origem confirma esses dados. Uma tentativa sem gravação nova deixa de aparecer como “nenhum item novo”. Schema permanece V20. Manifesto: [AF-0.1.1](manifests/AF-0.1.1-enriquecimento-recebimentos-027.md). Relato: [REV_027](../reviews/ACTIONFINANCE_REV_ENRIQUECIMENTO_RECEBIMENTOS_027.md). Aceite não atribuído. A sincronização autenticada desta versão ainda não foi executada.

## 0.2.0 — candidata em 15/10/2026, não publicada

Contas → Extrato passa a receber um CSV identificado, mostrar a prévia, gravar só as linhas elegíveis e consultar a observação. Sugestão de vínculo não quita recebimento. Não há saldo, categoria nem iniciativa. O Prompt 030 impede confirmar ou somar quando a moeda não está comprovada. O Prompt 031 lê o relatório real de liquidação, no perfil `mp-settlement-v2-csv-1`. O Prompt 032 preserva todas as ocorrências do lote, consolida evento só quando a identidade distingue e chama a soma de total parcial. O produto servido continua o já publicado. O arquivo real não foi importado. Manifesto: [AF-0.2.0](manifests/AF-0.2.0-extrato-t1-029.md). Relatos: [REV_029](../reviews/ACTIONFINANCE_REV_EXTRATO_T1_029.md), [REV_030](../reviews/ACTIONFINANCE_REV_ADEQUACAO_EXTRATO_030.md), [REV_031](../reviews/ACTIONFINANCE_REV_EXTRATO_REAL_031.md), [REV_032](../reviews/ACTIONFINANCE_REV_CONSOLIDACAO_EXTRATO_032.md).

## Não lançado

| Versão | Estado | Motivo |
|---|---|---|
| 1.0.0 | Recusada como rótulo atual | Plataforma incompleta; 024 proíbe chamar de 1.0 só por versionar |
| 0.2.0 | Candidata, não publicada | Extrato T1 com ocorrências preservadas no Prompt 032. Publicação e importação produtiva não autorizadas |

AF-BL-023 1.0 entra como **requisito**, sem linha de produto nova.
