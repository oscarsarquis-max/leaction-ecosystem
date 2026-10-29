# ACTIONFINANCE_REV_INTEGRIDADE_BASELINE_023_R1_1

Data da leitura: 15/10/2026, após o schema V20. Baseline de execução: AF-BL-023 revisão 1.1. Produto permanece **0.1.0**. A Spider não foi modificada. Aceite do proprietário: **não atribuído**. A primeira entrega **não** está integralmente concluída.

## O que foi verificado

Empresa `624023a4-57e3-415c-b7d0-925ca1acd3b7`, ambiente `PRODUCTION`. Instante da leitura do banco: a tarefa de consulta terminou em 15/10/2026 de manhã, depois da sincronização `1f159934-4b30-446c-8c2c-3f84176e3025`.

| Fato | Valor |
|---|---|
| Recebimentos armazenados | 11 |
| Com aplicação, pagador, método, processador ou valor pago | 0 em cada um desses campos |
| `paid_amount_absent` | 11 |
| Classificação `INDETERMINATE` | 11 |
| Classificação `REAL` ou `TEST` | 0 |
| Títulos, baixas, movimentos | 0, 0, 0 |
| Flyway | V20 `success=true`. O run `b39468f1-3ab2-4396-b070-15514fb34ee4` continua `FAILED`, 0 criados, 0 atualizados |
| Última tentativa | `1f159934-4b30-446c-8c2c-3f84176e3025`, 15/10/2026 10:48:48Z–10:48:49Z, status `EMPTY`, 0 criados, 0 atualizados, 1 página |
| Rótulo da tela para `EMPTY` | «Sincronização concluída» |

O total 11 é o armazenado nesse instante, não um teto. A tentativa das 10:48 não criou nem atualizou linha. A captura do proprietário (concluída, 11 registros, 11 pendências de ambiente) corresponde a esse estado, não aos contadores do Monitor.

## Caso R$ 90

Identidade completa: `b6cf9b7a-d8d3-42a7-873e-818f17133322`.

| Campo no Finance | Persistido |
|---|---|
| Cobrado | 9000 centavos |
| Pago | ausente (`paid_amount_absent=true`). O cobrado não foi copiado |
| Situação | `CONFIRMED` |
| Atualização na origem | 2026-10-06 15:01:49Z |
| Classificação | `INDETERMINATE`, motivo vazio |
| Aplicação, pagador, método, processador, status do provedor | ausentes |
| Pendência | `ENVIRONMENT_UNPROVEN` — «Falta evidência de ambiente» |

As outras dez linhas seguem o mesmo padrão de ausência. Não há uma única etiqueta escondendo motivos diferentes: as onze pendências são a mesma causa, falta de classificação REAL ou TEST.

## Matriz da fronteira

| Campo | Hub persistido | API de lista usada pela capacidade | Spider publicada | Finance | Tela | Fronteira |
|---|---|---|---|---|---|---|
| Identidade | não relida neste ciclo no banco do Hub | — | o id chega, porque o Finance o gravou | `transaction_id` | prefixo na lista; id no detalhe | — |
| Cobrado R$ 90 | evidência anterior do proprietário no admin | o valor chegou | o valor chegou | 9000 | cobrado | — |
| Pago | admin do Hub, segundo o proprietário, mostrava R$ 90 | **não determinado** se a API de lista de produção enviou `paidAmountMinor` | o código **commitado** de `ActionHubPayListIdentity` não copia `paidAmountMinor` | nulo | ausente, sem copiar o cobrado | Spider commitada não transporta. O banco `actionhub_prod` desta conta tem 0 tabelas; a linha do Hub não foi relida aqui |
| Aplicação, cliente, método, processador | o código local do Hub sabe montar esses campos | não comprovado no processo publicado | o mesmo arquivo commitado não copia `commercialApplication`, `payerLabel` nem `paymentMethod` | nulos | ausentes | Spider commitada. Há um diff local de +43 linhas que reencaminharia esses campos; **não foi publicado** |
| Ambiente do pagamento | `live_mode` no payload, no código local | não comprovado na resposta que chegou | classificação não é copiada pelo arquivo commitado | `INDETERMINATE` porque o item veio sem `REAL`/`TEST` | «Falta evidência de ambiente» | Spider commitada, ou a API não enviou. As duas possibilidades permanecem; o Finance não inventou `REAL` |
| Tarifa, líquido, retenção, disponibilidade | não fazem parte da lista de cobranças | — | — | não derivados | — | não coletado; não inferir |

`PRODUCTION` no envelope da sincronização não classifica o pagamento. Por isso as onze linhas ficam pendentes mesmo com a sincronização no ambiente produtivo.

## O que não foi feito

Não alterei a Spider, o Hub publicado nem a Loja. Não reli a janela para enriquecer, porque a página das 10:48 não trouxe campo novo e o adapter publicado não transporta os campos faltantes. Publicar o diff local da Spider seria exatamente a alteração proibida.

Não há correção de apresentação que recupere pagador, método ou pago: eles não estão na linha. A tela já distingue a pendência de ambiente e não trata o cobrado como pago.

## Critérios

| Critério | Resultado |
|---|---|
| ID completo do caso de R$ 90 | PASS |
| Matriz com causa quando a evidência alcança | PASS para Finance e para o código commitado da Spider |
| Hub persistido e API de produção relidos | NÃO VERIFICADO — `actionhub_prod` não contém as tabelas de pedido |
| Campos recuperados na tela pública | FAIL — continuam ausentes; dependem da Spider |
| Repetição sem duplicação depois de um enriquecimento | NÃO VERIFICADO — a última página não alterou as 11 identidades |
| Sem título, baixa ou movimento | PASS |
| Spider íntegra neste trabalho | PASS |
| Primeira entrega integral | FAIL — delimitada ao que está utilizável |

Utilizável hoje: lista dos 11 recebimentos, cobrado, situação, data de atualização e a pendência de ambiente. Não utilizável como pago, cliente, método ou base de caixa.
