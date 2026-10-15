# REV 032 — Consolidação do extrato

Data: 15/10/2026. Candidata **0.2.0**. Não publicada. O produto no ar permanece **0.1.2**. O RDS público permanece Flyway **V20**. A ISA permanece pausada. Nenhuma chamada nova ao Mercado Pago, Spider ou Hub. O arquivo real não foi importado.

## Commits

Branch local `feat/actionfinance-extrato-032`, cortada de `feat/prm-009-public-receipt-sync`. Não enviada ao remoto.

| Commit | Conteúdo |
|---|---|
| `6c7028bfee93bb09cd01b6a1b9038bea125c18aa` | Candidata 0.2.0 até o Prompt 031: perfil de liquidação, V21, V22, testes, relatos e jornada sanitizada anterior. O CSV real não entra |
| Commit de preservação deste ciclo | Separa ocorrência, evento, disponibilidade e total parcial. V23. O hash completo fica no `git log` da branch, imediatamente acima deste relato |

O working tree continua com outras frentes não commitadas: cadastros, logout, V13–V20 e o restante do monorepo. Elas não foram varridas para este incremento.

## O que a confirmação faz agora

Confirmar o lote preserva cada linha do arquivo como ocorrência. A posição no arquivo, junto com o hash do arquivo, identifica a ocorrência naquele documento. Isso não é a identidade do evento entre importações.

| Estado | O que acontece |
|---|---|
| Identidade suficiente e liberada | Vira evento. Entra no total parcial das linhas elegíveis |
| Identidade suficiente e não liberada | Vira observação. Fica fora do total parcial e não é saldo disponível |
| Identidade ambígua | Fica em revisão, sem evento consolidado e sem fusão |
| Reenvio do mesmo conteúdo | Não cria outro evento. A nova ocorrência aponta para o evento já gravado |

A soma da lista se chama total parcial. Não é fluxo integral da conta, nem saldo, nem disponível. Linha sem categoria continua visível como “Não classificada” e “Não atribuída”.

## Os nove pares

Comparação de hoje, só com contagens: 22 linhas, 46 colunas, 13 grupos, 9 pares de tamanho 2 e 4 linhas únicas. Em todos os pares, as datas e `IS_RELEASED` são iguais, `INSTALLMENT_NUMBER` está vazio, e as únicas colunas diferentes são `TRANSACTION_AMOUNT`, `REAL_AMOUNT` e `SETTLEMENT_NET_AMOUNT`. Os módulos não são iguais e a soma do par não é zero. Os pares estão com liberação falsa. As quatro únicas estão com liberação verdadeira. Moeda BRL nas duas colunas. Tipo `SETTLEMENT` nas 22.

O glossário do relatório descreve `SETTLEMENT` como pagamento aprovado e reserva `INSTALLMENT_NUMBER` à parcela financiada. Não define uma segunda linha do mesmo `SOURCE_ID` e do mesmo tipo, com sinal oposto e módulo diferente. Não há outro relatório nesta pasta. O Hub não foi usado como fonte destas linhas.

Exemplo sanitizado, com a mesma relação e sem valor do arquivo real: duas linhas `pay-san-par-1`, tipo `SETTLEMENT`, liberação falsa, sem número de parcela, mesma data. Líquidos +30,00 e −12,00, tarifa zero. Nenhuma outra coluna muda.

A evidência que falta é o detalhe dessa operação na conta do Mercado Pago: se a linha negativa é estorno parcial, retenção ou repetição da exportação. Serve um recorte dessa operação ou o relatório de liberação do mesmo período para esses identificadores. Não é necessária outra exportação genérica de todas as colunas. Não foi enviada mensagem ao suporte.

Enquanto isso, as 18 linhas permanecem no lote, em revisão, e não viram evento.

## Jornada sanitizada

Fixture de 22 ocorrências, quatro liberadas isoladas e nove pares. Empresa Padaria Exemplo, conta demonstrativa, vínculo `usr-sanitizado-032`. Postgres descartável em `127.0.0.1:5441`, removido ao fim. Capturas em `documents/reviews/screenshots/extrato-032/`.

| Passo | Resultado |
|---|---|
| Prévia | 22 ocorrências. O par de R$ 12,00 não pode ser consolidado |
| Confirmação | 22 preservadas, 4 eventos criados, 18 em revisão. Total parcial: entradas R$ 251,00 |
| Composição | Bruto R$ 80,00, tarifa R$ 4,00, líquido R$ 76,00. 80 − 4 = 76 |
| Reenvio | 0 criados, 4 inalterados. O total parcial permanece R$ 251,00 |
| Sobreposição | Repete uma linha, acrescenta R$ 10,00 liberados e uma linha única não liberada de R$ 20,00. Total parcial R$ 261,00. Os R$ 20,00 ficam preservados e fora do total |
| Banco ao fim | 6 eventos: 5 liberados no total parcial e 1 não liberado fora dele. 47 ocorrências de documento. Títulos, baixas e movimentos não foram o alvo da gravação |

`StatementObservationIT` passou neste ciclo, com V23 aplicada no Postgres do teste, e manteve título, baixa e `cash_movement` sem alteração no perfil de laboratório. A outra empresa continua sem leitura.

## Esquema e recuperação

V21 cria a observação. V22 admite o perfil de liquidação. V23 guarda a ocorrência do documento e a disponibilidade do evento. Nenhuma foi aplicada no RDS. Rollback: `actionfinance-web:16`, `sha256:bcf11a54e4017cd5d4e64efce860ee1e47cfc716f77698980f8c3c33fbb34dec`, SPA `index-B0699gCh.js`, produto 0.1.2. Voltar a imagem não apaga V21–V23.

## Decisão

Não publicar neste ciclo e não importar o arquivo real.

A jornada está pronta para uma publicação com revisão explícita: o lote inteiro fica visível, o total é parcial e os nove pares ficam em revisão. O impedimento para construir essa imagem em cima do origin atual é outro: V13–V20 já foram aplicadas no RDS e ainda não estão no Git. Uma imagem feita só com estes commits não valida o Flyway desse banco. Versionar V13–V20 é frente separada. Não autoriza movimentar dinheiro, atribuir saldo inicial nem alterar a Spider.
