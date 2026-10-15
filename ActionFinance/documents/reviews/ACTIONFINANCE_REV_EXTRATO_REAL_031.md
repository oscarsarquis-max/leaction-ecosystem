# REV 031 — Extrato T1 no relatório real de liquidação

Data: 15/10/2026. Candidata **0.2.0**, parser **1**. Não publicada. O produto no ar permanece **0.1.2**. O RDS público permanece Flyway **V20**. A ISA permanece pausada. O arquivo real não foi importado, não foi chamado o Mercado Pago e a imagem de produção não foi construída.

## Arquivo conferido

O original permanece em `documents/data/reports/`, fora do Git. Hash SHA-256 conferido: `5CDFDEAC66D9CB79D10D4DAAC92E8BFF283BD2B600FB6794AB3E306A0B8622AF`. Tamanho: 5708 bytes. O arquivo não foi editado.

É um relatório de liquidação, 22 linhas e 46 colunas, UTF-8, separador ponto e vírgula, decimal com ponto e sinal, instante com deslocamento. `TRANSACTION_CURRENCY` e `SETTLEMENT_CURRENCY` estão preenchidas e são BRL em todas as linhas. Há uma única referência `USER_ID`. `TRANSACTION_TYPE` é `SETTLEMENT` nas 22 linhas. Esse tipo, no glossário do Mercado Pago, é pagamento aprovado. Não é direção de caixa e não é data de liberação.

O perfil de laboratório `mp-account-money-csv-1` continua existindo para os testes antigos. Ele não é este formato: usa vírgula e as colunas `DATE`, `RECORD_TYPE`, `NET_CREDIT_AMOUNT` e `NET_DEBIT_AMOUNT`.

## Perfil implementado

`mp-settlement-v2-csv-1`, reconhecido pelo cabeçalho e pelo ponto e vírgula. A versão do parser fica no lote e não entra na chave.

| Campo do arquivo | Uso |
|---|---|
| `SETTLEMENT_DATE` | Data da linha. É a data de aprovação, convertida para o dia civil em America/Sao_Paulo |
| `TRANSACTION_DATE` | Data de criação. É lida e não substitui a aprovação |
| `MONEY_RELEASE_DATE` | Previsão de liberação. Não é copiada para a data da linha |
| `TRANSACTION_AMOUNT` | Bruto da compra |
| `FEE_AMOUNT` | Tarifa já incluída na relação com o líquido. Componentes `MKP_FEE_AMOUNT`, `FINANCING_FEE_AMOUNT`, `SHIPPING_FEE_AMOUNT` e `TAXES_AMOUNT` não são somados de novo |
| `SETTLEMENT_NET_AMOUNT` | Líquido que o glossário descreve como impacto na conta. O sinal deste campo define entrada ou saída |
| `REAL_AMOUNT` | Líquido da operação, conceito diferente. Se divergir do líquido de liquidação, os dois permanecem e a linha fica fora |
| `TRANSACTION_CURRENCY` e `SETTLEMENT_CURRENCY` | Moeda comprovada só quando as duas colunas existem, estão preenchidas e são iguais a BRL. Não há fallback |
| `USER_ID` | Referência de conta para o vínculo explícito. Não é validação automática do Mercado Pago |
| `IS_RELEASED` | `true` permite a linha elegível entrar na soma de fluxo. Outro valor deixa a linha na prévia, fora da soma, sem classificá-la como mudança de disponível |
| `BUSINESS_UNIT`, `SUB_UNIT`, `APPLICATION_ID`, loja | Pistas. Não atribuem iniciativa. A linha gravada fica “Não classificada” e “Não atribuída” |

A direção não sai do nome `SETTLEMENT` nem só do valor positivo. Sai do sinal de `SETTLEMENT_NET_AMOUNT`.

`FEE_AMOUNT` negativo no arquivo é custo já descontado: `TRANSACTION_AMOUNT + FEE_AMOUNT = SETTLEMENT_NET_AMOUNT`. A coluna gravada guarda a magnitude, porque o esquema exige tarifa não negativa. O sinal original permanece na linha original do arquivo. `FEE_AMOUNT` positivo não é convertido em custo; a linha fica fora.

## As 22 linhas e as 13 combinações

Há 13 pares `SOURCE_ID` + `TRANSACTION_TYPE`. Quatro aparecem uma vez. Nove aparecem duas vezes, 18 linhas.

Nas quatro únicas, `IS_RELEASED` é verdadeiro. São as únicas elegíveis. A chave `MERCADOPAGO|mp-settlement-v2-csv-1|{SOURCE_ID}|SETTLEMENT` as distingue. A versão do parser não faz parte dela.

Nos nove pares, as duas linhas compartilham identificadores, datas e `IS_RELEASED` falso. Não são parcelas: `INSTALLMENTS` é 1, `INSTALLMENT_NUMBER` está vazio e `DESCRIPTION` está vazio. Não são cópias integrais: nenhuma linha se repete byte a byte. O que muda em cada par é só `TRANSACTION_AMOUNT`, `REAL_AMOUNT` e `SETTLEMENT_NET_AMOUNT`. Os sinais são opostos e os módulos não são iguais; a soma do par não é zero. Não é, portanto, uma tarifa destacada nem um estorno do mesmo valor.

A chave não separa essas duas ocorrências. As 18 linhas permanecem na prévia, com diagnóstico, e a confirmação delas fica bloqueada. Nada é fundido e o número da linha, a data ou o valor não entram na chave para forçar a gravação.

Questão que a fonte e o glossário não fecham: não está determinado se a linha de sinal oposto é estorno, revisão ou artefato da exportação. Enquanto isso, ela não entra.

No arquivo inteiro, bruto mais tarifa fecha com o líquido de liquidação, e `REAL_AMOUNT` coincide com esse líquido. Isso foi contado, sem publicar os valores do extrato. Duas das quatro linhas elegíveis têm tarifa, e essa tarifa é a tarifa do Mercado Livre; ela já está no líquido.

Período lido pela data de aprovação: 01/10/2026 a 14/10/2026. A data de liberação só aparece nas quatro linhas elegíveis, entre 06/10/2026 e 08/10/2026, no mesmo dia civil da aprovação de cada uma.

## Controles da fixture sanitizada

A jornada de tela usou a fixture derivada, não o arquivo real. Identificadores e valores foram substituídos. A relação preservada é: duas linhas liberadas, uma com tarifa que fecha, e um par não liberado com sinais opostos e módulos diferentes.

| Controle | Resultado |
|---|---|
| Prévia | 4 linhas; 2 elegíveis; 2 fora, por identidade insuficiente e liberação não confirmada |
| Confirmação | Criadas 2. Não importadas 2. Soma de fluxo: entradas R$ 176,00. Saídas R$ 0,00 |
| Composição da linha de R$ 76,00 | Bruto R$ 80,00, tarifa R$ 4,00. 80 − 4 = 76. A tarifa não foi somada de novo |
| Recarga e reenvio do mesmo lote | Criadas 0. Inalteradas 2. A soma permanece R$ 176,00 |
| Lote sobreposto | Repete uma linha e acrescenta R$ 10,00. Criadas 1. Inalteradas 1. Soma R$ 186,00 em 3 linhas |
| Par de R$ 30,00 e R$ 12,00 | Fora da confirmação e fora da soma |

Esses reais são da fixture. Não são o total do arquivo real. A soma é o líquido das linhas confirmadas. Não é saldo, disponível nem conciliação.

Empresa da jornada: Padaria Exemplo, conta demonstrativa, vínculo `usr-sanitizado-031`. Não é a Loja de Pães e não houve atribuição de iniciativa.

Capturas em `documents/reviews/screenshots/extrato-031/`: `previa.png`, `lista.png`, `detalhe.png`, `reenvio.png`, `sobreposicao.png`.

O parser também leu o arquivo real, só em memória, e conferiu 22 linhas, 4 elegíveis, 18 fora, 13 chaves distintas, moeda não presumida e o período acima. Esse teste não grava o extrato e não o exibe.

`StatementObservationIT` continua provando, com dados sintéticos do perfil de laboratório, que a importação não cria título, baixa nem `cash_movement`, que o valor pago de um recebimento sintético não muda e que a outra empresa recebe 403. Isso não é prova do arquivo real.

## Versão, esquema e recuperação

| Peça | Estado |
|---|---|
| Produto | 0.2.0 candidata. Servido: 0.1.2 |
| Perfis | `mp-settlement-v2-csv-1` para este relatório. `mp-account-money-csv-1` só como laboratório |
| Schema | V21 cria a observação. V22 aceita os dois perfis no lote. Origin: V20. V21 e V22 rodaram no teste e num Postgres descartável, não no RDS |
| Rollback | `actionfinance-web:16`, `sha256:bcf11a54e4017cd5d4e64efce860ee1e47cfc716f77698980f8c3c33fbb34dec`, SPA `index-B0699gCh.js`, produto 0.1.2. Voltar a imagem não desfaz V21, V22 nem apaga observação |

## Decisão

Não publicar a 0.2.0 e não importar o arquivo real.

| Campo | Decisão |
|---|---|
| Fonte | Relatório de liquidação conferido pelo hash acima. Perfil `mp-settlement-v2-csv-1`, parser 1 |
| Conta | O arquivo tem uma referência `USER_ID`. Ela ainda não está vinculada a uma conta de produção. Este ciclo não criou conta e não associou a linha à Loja |
| Período lido | Aprovação de 01/10/2026 a 14/10/2026 |
| Elegíveis | 4 de 22. Pagamento aprovado, liberação marcada e chave única |
| Exclusões | 18 linhas, em 9 pares. A chave não as separa e a liberação não está confirmada |
| Efeito previsto | Se a carga for autorizada depois: só as 4 observações, sem título, baixa, movimento, saldo ou conciliação. Os valores do extrato real não entram neste relato. A carga não foi feita |

A primeira carga produtiva ainda depende de autorização explícita, do vínculo da referência `USER_ID` à conta da empresa titular e de aplicar V21 e V22 no banco isolado de publicação antes da imagem. A questão dos 9 pares continua aberta e não entra nessa carga.
