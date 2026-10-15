# Projeto de tesouraria — AF-BL-023 revisão 1.2

Data: 15/10/2026. Requisitos: revisão **1.2**. Produto publicado: **0.1.2**. Schema publicado: Flyway **V20**. Aceite do proprietário: **não atribuído**.

Este arquivo prepara a tesouraria. Não importa extrato, não altera saldo, não muda a Spider e não publica dado sintético. As revisões [1.0](ACTIONFINANCE_PROJETO_TESOURARIA_MP_023.md) e [1.1](ACTIONFINANCE_PROJETO_TESOURARIA_MP_023_R1_1.md) permanecem. A proposta [026](ACTIONFINANCE_PROPOSTA_CONTRATOS_FINANCEIROS_026.md) é reutilizada só onde ainda vale; as diferenças estão na seção 2.

## 1. O que já está separado

| Eixo | Estado em 15/10/2026 |
|---|---|
| Implementado e publicado | Observação de cobrança enriquecida (produto 0.1.1, imagem `actionfinance-web:15`) e a apresentação 0.1.2 (`actionfinance-web:16`, SPA `index-B0699gCh.js`). Pedidos 1.3 e 1.4 preservados. Adapter da lista publicado na Spider `spider-runtime-prod:4` |
| Provado em agregado | 12 recebimentos PRODUCTION, 10 pendências pela regra da tela, última tentativa SUCCESS com 1 incluído e 11 atualizados. Esses números são a leitura daquele instante |
| Provado como identidade técnica | Sufixo `@amount.hub.local` é chave interna do checkout avulso, não cliente. A tela 0.1.2 mostra «Pagador não identificado» e guarda a referência no rastreio |
| Não provado | Detalhe autenticado do pagamento de R$ 90 e repetição idempotente do 027. Zoom real de 200% numa janela larga, no acabamento 028 |
| Aceito | Nada desta tesouraria, nem o visual 028 |
| Não existe | Extrato persistido, vínculo movimento–recebimento, iniciativa, rateio, posição de três bases, gráfico de gestão |

A lista de cobranças continua observação. O Monitor continua projeção da Spider. Nenhum dos dois é o extrato da conta.

## 2. Diferença concreta em relação a 026, 1.0 e 1.1

| Ponto da 026 ou da 1.1 | Situação agora |
|---|---|
| Adapter da lista ainda local; pago, aplicação e pagador vazios | Publicado no 027. A matriz «bloqueado pelo contrato» da seção 8 da 026 não descreve mais o ar |
| Produto 0.1.0 e imagem `:14` | Produto 0.1.2, imagem `:16`. Schema continua V20 |
| Pergunta do rateio na seção 11 da 026 | Fechada pelo proprietário: padrão «Não atribuída»; percentual só com regra registrada, autor, vigência e histórico. Não perguntar de novo |
| Iniciativas como empresas separadas | Fechado: Loja de Pães, Inove4us e SegSense são iniciativas da mesma empresa titular |
| Primeiro incremento = só observação de cobrança | Essa fatia foi o 027/028. O próximo incremento executável é extrato e vínculo com os recebimentos já gravados |
| Contrato de movimento como exemplo JSON, sem fonte real | A documentação oficial do MP descreve relatórios de dinheiro em conta (`settlement_report`) e de liberações (`release_report`), CSV/XLSX, com `SOURCE_ID` e `EXTERNAL_REFERENCE` entre as colunas configuráveis. A existência da API não prova acesso da conta desta empresa |
| Spider congelada pela 1.1 para qualquer campo novo | O 027 autorizou só o enriquecimento da observação. Essa entrega fica. Extrato novo não reutiliza essa autorização. Sem capacidade de extrato na Spider, a fatia seguinte cabe no Finance por arquivo, até haver autorização delimitada para uma capacidade nova |

Capacidades publicadas da Spider que o Finance usa para dinheiro: `LOOKUP_ACTIONHUB_PAYMENT` (pedido 1.3) e `LIST_PAYMENT_TRANSACTIONS` (pedido 1.4). O catálogo de contrato satélite vai até **1.5**, ocupado pela biblioteca da Loja. Não há `settlement_report`, `release_report` nem leitura de saldo. Não há cliente Mercado Pago no Finance.

## 3. Empresa, conta e iniciativas

A empresa exibida no seletor continua `Loja de Pães`, id `624023a4-57e3-415c-b7d0-925ca1acd3b7`, código `loja-de-paes`. Esse nome é o da empresa no Finance. Não é a iniciativa Loja. Não renomear e não mover vínculo de acesso.

`pay_company_mapping` liga essa empresa à aplicação `lojadepaes`. Não guarda `collector_id`, `user_id` nem `account_id` do Mercado Pago. `financial_account` é conta gerencial local, sem identidade do provedor. Portanto a correspondência técnica conta MP ↔ empresa Finance **não está demonstrada**. O saldo não pode ser atribuído à iniciativa Loja, nem apresentado como caixa da empresa, enquanto essa conta não for confirmada.

Decisão já tomada e que não se reabre: o dinheiro desta etapa está no Mercado Pago, e as três iniciativas pertencem à mesma empresa. Uma conta atende várias iniciativas. A atribuição gerencial não cria saldo bancário por iniciativa.

O que ainda depende de uma confirmação na prévia de um arquivo real, quando a importação produtiva for autorizada à parte:

| Alternativa | Efeito |
|---|---|
| O arquivo traz `user_id` ou `account_id` e o operador confirma, na empresa já selecionada, que aquele relatório é o da conta titular | Grava o vínculo opaco conta Finance ↔ referência externa. Não grava segredo |
| O painel tiver mais de uma conta e o arquivo não identificar qual é | A prévia não confirma. Nenhuma linha entra |

Até uma dessas confirmações, o desenho trata a conta como «conta do titular ainda não vinculada».

Papéis que não se fundem: pagador da cobrança, cliente comercial, fornecedor ou favorecido, titular da conta. O endereço `@amount.hub.local` permanece identificador técnico de checkout.

## 4. Mapa de fatos

```text
Pedido Hub ──► LIST 1.4 / LOOKUP 1.3 ──► pay_receipt_transaction
                                         observação de cobrança (publicado)

Conta MP ──► settlement_report ou release_report ou arquivo baixado pelo titular
         ──► [sem capacidade na Spider]
         ──► statement_batch + statement_line   (próxima fatia, ainda não existe)

Título Finance ──► pagamento executado no MP, fora daqui
               ──► settlement manual já existente (baixa gerencial, 1 título)
               ──► não nasce da lista nem do extrato nesta fatia
```

| Fato | Identidade estável | Dono | Não é |
|---|---|---|---|
| Observação de cobrança | empresa + `ACTIONHUB_PAY` + ambiente + `transactionId` | Finance, via Spider | Extrato, saldo, título |
| Linha de extrato | conta + origem do arquivo ou relatório + id estável do evento (`SOURCE_ID` quando a fonte o tiver) | Finance | Nova receita só porque houve liberação |
| Posição informada | conta + moeda + instante da fonte + cobertura | Finance calcula a partir da fonte | Saldo gerencial |
| Obrigação | empresa + id do título | Finance | Baixa |
| Iniciativa | empresa + código (`loja`, `inove4us`, `segsense`) | Finance | Empresa, aplicação Hub |
| Alocação confirmada | par de fatos + valor em unidades mínimas + autor | Operador | Sugestão |

Igualdade de data e valor não identifica evento. Página ou arquivo repetido não duplica a linha já gravada com a mesma identidade. Dado omitido numa leitura nova não apaga dado confirmado.

## 5. Dicionário

Moeda e precisão: valores em unidade mínima inteira, transportados como texto de dígitos. `BRL` usa escala 2. Outra moeda exige escala explícita e não entra na mesma soma sem regra cambial, que esta etapa não tem. Ausência não vira zero.

Diagnóstico de lacuna, usado em todo fato:

| Código | Significado | Efeito no indicador |
|---|---|---|
| `NA` | O campo não se aplica a este tipo de evento | Fora da fórmula |
| `NOT_COLLECTED` | A fonte pode ter e esta coleta não pediu | Indicador marca cobertura incompleta |
| `UNAVAILABLE` | A fonte deste evento não tem o campo | Não bloqueia os outros campos presentes |
| `NOT_TRANSPORTED` | A origem tem e o contrato publicado não trouxe | Pendência de contrato; não preencher por derivação |
| `UNCLASSIFIED` | Dado presente, classificação humana ainda não feita | Entra no caixa da conta; fica fora do corte por iniciativa ou categoria |

### 5.1 Observação de cobrança — já persistida

| Campo | Significado | Fonte | Obrigatório | Ausência |
|---|---|---|---|---|
| `transactionId` | Pedido ou pagamento observado | Hub via Spider | Sim | Sem identidade, a linha não grava |
| `amountMinor` | Valor cobrado | Pedido | Quando a origem envia | `amountAbsent`; não é o pago |
| `paidAmountMinor` | Valor pago confirmado pela origem | Payload com confirmação explícita | Não | `paidAmountAbsent`; não copiar o cobrado nem usar `CONFIRMED` como pago |
| `currency` | Moeda do pedido | Origem | Sim quando há valor | Sem moeda, o valor não entra em soma |
| `normalizedStatus` | Situação da cobrança na origem | Lista | Sim | Não é conciliação nem disponibilidade |
| `classification` | `REAL`, `TEST` ou `INDETERMINATE` | `live_mode` ou marca de teste no item | Sim, com motivo | Envelope `PRODUCTION` não classifica. `INDETERMINATE` é pendência de ambiente |
| `commercialApplication` | Código da aplicação, ex. `lojadepaes` | Hub | Não | «Não informada». Não é a iniciativa |
| `commercialDescription` | Descrição comercial | Hub | Não | Texto vazio não vira produto inventado |
| `payerKind` / `payerLabel` | Papel e texto recebidos | Hub | Não | E-mail `@amount.hub.local` é chave técnica, não cliente. Outro e-mail permanece e-mail informado |
| `paymentMethod` / `processorName` | Meio e processador quando a origem evidencia | Hub | Não | «Não informado» |
| `originUpdatedAt` | Atualização na origem | Hub | Quando a origem envia | Não renomear como data de pagamento nem de extrato |
| Pendência da tela | Ambiente, pago ausente em cobrança confirmada, ou revisão | Calculada no Finance | — | Não é quantidade de registros. `UNPAID_EXPECTED` aparece e não entra na contagem |

Resolução da pendência de ambiente ou de pago: nova sincronização já autorizada, quando o item passar a trazer evidência. Efeito: a pendência sai; o caixa da conta não muda, porque cobrança não é movimento. A lacuna do e-mail real, quando a lista preferiu a chave técnica, só se resolve com contrato do Hub que separe as duas identidades. Está fora desta fatia.

### 5.2 Linha de extrato — ainda não existe

| Campo | Significado | Fonte | Obrigatório | Ausência |
|---|---|---|---|---|
| Conta Finance | Conta gerencial vinculada ao relatório | Confirmação do operador na prévia | Sim | Sem vínculo, o lote não confirma |
| Origem do lote | `FILE` nesta fatia. Relatório oficial só se uma capacidade futura for autorizada | Arquivo | Sim | Arquivo não é sincronização automática |
| Id do evento | `SOURCE_ID` do relatório de dinheiro em conta, ou o id que o arquivo declarar estável | Arquivo | Sim para confirmar a linha | Sem id estável, a linha fica na prévia como não importável |
| Referência externa | `EXTERNAL_REFERENCE` quando a coluna existir | Arquivo | Não | Não inventar a partir da descrição |
| Direção e natureza do evento | Entrada, saída, tarifa, liberação, estorno, transferência, informação | Tipo do relatório, não o favorecido | Sim | Tipo desconhecido fica `UNCLASSIFIED` na natureza, não vira receita |
| Bruto, tarifa, líquido | Cada um só se a coluna existir | Arquivo | Não | Coluna ausente é `UNAVAILABLE` naquela linha, não zero |
| Efetivação no extrato | Data em que o relatório diz que o dinheiro afetou a conta | Coluna de data do relatório escolhido | Sim para a linha entrar no realizado | Não usar criação do pedido nem vencimento do título |
| Disponibilidade | Disponível, retido ou a liberar, se o relatório distinguir | `release_report` versus settlement | Não | Não somar componentes sem a fonte dizer que não se sobrepõem |
| Moeda | `currency_id` do relatório | Arquivo | Sim | Sem moeda, fora das somas |

`release` ligado a um pagamento já observado não é outra venda. Transferência entre contas próprias não é receita nem despesa consolidada. Estorno é fato relacionado e preserva a linha original.

### 5.3 Obrigação, posição e classificação — fatias seguintes, campos já reservados

| Campo | Fato | Nesta etapa |
|---|---|---|
| Competência e vencimento | Título já existente (`financial_title`) | Reaproveitar. Conta prevista de pagamento não é baixa |
| Categoria e subcategoria | Classificação gerencial | `UNCLASSIFIED` até o operador confirmar. Sugestão não grava sozinha |
| Iniciativa | Atribuição | `UNCLASSIFIED` («Não atribuída»). Código de aplicação `lojadepaes` pode sugerir a iniciativa Loja; a sugestão não confirma |
| Rateio | Regra com autor, início, fim e percentuais em base 10000 (0,01 ponto percentual) | Ausente significa o valor inteiro não atribuído, não um rateio igual invisível |
| Posição informada | Snapshot da fonte | Sem relatório de saldo, não há número |
| Saldo gerencial | `OPENING` comprovado + `cash_movement` válidos | Não há `OPENING` produtivo. Não fabricar |
| Saldo projetado | Base declarada + compromissos futuros elegíveis | Não altera o realizado |

Datas que não se substituem: criação na origem, atualização na origem, competência, vencimento, pagamento ou liquidação da obrigação, efetivação no extrato, disponibilidade. Cada indicador declara qual usa.

## 6. Categorias iniciais

Natureza do fluxo e classificação gerencial são eixos diferentes. A natureza vem do tipo do evento. A categoria vem do operador.

| Natureza | Entra como | Não entra como |
|---|---|---|
| Receita operacional | Entrada de venda ou recebimento de atividade | Liberação de valor já contado |
| Despesa operacional | Saída de resultado | Compra de ativo, tarifa, tributo |
| Tarifa | Custo do meio, quando a coluna de tarifa existir | Reduzir de novo o líquido se o líquido já está líquido |
| Tributo | Imposto retido ou pago, quando a fonte distinguir | Tarifa do MP |
| Compra de ativo | Saída que não é despesa de resultado | Consumo |
| Financiamento | Principal de empréstimo | Juros, se a fonte separar |
| Aporte ou retirada | Movimento com o titular | Receita ou despesa |
| Transferência própria | Sai de uma conta e entra na outra | Resultado consolidado |

Compra de insumo, entrada em estoque, consumo e pagamento são fatos diferentes. Caixa não é lucro. Margem não se calcula só com pagamentos.

Classificação manual e em lote, na fatia 2: prévia, validação, histórico. Exceção permanece não classificada e visível. Regra futura é explícita e não reclassifica o passado sozinha.

Rateio: as parcelas em unidade mínima somam exatamente o valor alocado. O resto de arredondamento vai para a parcela de maior percentual; empate, para a de menor código de iniciativa. Alterar a regra vale dos fatos ainda não classificados em diante. Valores não atribuídos e compartilhados aparecem uma vez no total da conta.

## 7. Conciliação

Sugestão de vínculo não confirma. O operador confirma. Desfazer a conciliação remove o vínculo e o histórico guarda quem desfez. O fato externo permanece.

| Correspondência | Teto |
|---|---|
| 1:1 | O menor entre o valor ainda aberto da linha e o do recebimento ou da obrigação |
| Parcial | Soma das alocações ≤ valor da linha e ≤ valor do fato interno |
| Agrupada | Várias linhas ou vários fatos, com o mesmo teto por ponta |
| Sem correspondência | A linha fica no extrato, sem caixa duplicado e sem título inventado |

O recebimento já importado entra como candidato quando `processorReference`, `transactionId` ou `EXTERNAL_REFERENCE` coincidem. Data e valor iguais, sozinhos, geram no máximo uma sugestão marcada como fraca, que não confirma.

Bruto, tarifa e líquido: o realizado da conta usa o líquido que afetou o saldo, quando a fonte o traz. O bruto e a tarifa aparecem na composição e não se somam de novo ao líquido. Se a fonte só trouxer um valor, esse valor é o que a fonte diz ter movimentado, e os outros ficam `UNAVAILABLE`.

## 8. Fórmulas

Todas em uma moeda. Arredondamento de exibição: metade para cima na última casa de real, a partir da unidade mínima, só na apresentação. A conta interna permanece inteira.

| Base | Fórmula | Quando não há número |
|---|---|---|
| Posição informada | O valor que a fonte declarou, com instante e cobertura | «Posição não informada pela conta» |
| Saldo gerencial | Saldo inicial comprovado + créditos de movimentos válidos − débitos | «Saldo gerencial indisponível: falta saldo inicial comprovado» |
| Conferência do extrato | Saldo inicial do relatório + créditos − débitos = saldo final, na semântica daquele arquivo | Divergência explícita; sem ajuste automático |
| Projeção no dia D | Base declarada + entradas futuras elegíveis com data ≤ D − saídas futuras elegíveis com data ≤ D | Sem base declarada: só a agenda, sem saldo |
| Menor saldo projetado | Mínimo da série até 13 semanas, com a data | Só se a base e as datas dos compromissos existirem |

Elegível no projetado: título em aberto, na moeda, com vencimento conhecido, ainda não liquidado e ainda não coberto por linha de extrato já realizada. Fato já realizado não entra de novo. Hipótese de prazo ou valor fica nomeada e não altera o realizado.

Cobrança, pagamento e liberação do mesmo dinheiro contam uma vez, na linha que afetou a conta. A observação de cobrança não entra nessa soma.

## 9. Filtros

Combináveis: período e tipo de data, conta, iniciativa, categoria e subcategoria, contraparte no papel do fato, origem, natureza e direção, método quando o fato tiver, situação, conciliação, pendência de classificação.

Padrão ao abrir a tesouraria, quando a tela existir: empresa já selecionada, conta vinculada se houver uma só, período do mês civil em `America/Sao_Paulo` pela data de efetivação do extrato, iniciativa e categoria em «todas», inclusive não atribuídas. Os filtros ativos aparecem em texto. Abrir detalhe e voltar preserva o recorte.

Lista, totais e gráfico usam o conjunto inteiro autorizado, não a página. Filtro que não se aplica a um indicador aparece como «não entra nesta conta» com o motivo. Três resultados distintos: não há registros na empresa; o filtro não encontrou; faltam dados para calcular. Só o segundo é lista vazia com total zero do recorte. Limpar volta ao padrão.

Exportação, na fatia em que existir, usa o mesmo recorte, a mesma permissão e os campos já disponíveis. Não antecipa coluna de fatia futura.

## 10. Indicadores

| Instrumento | Pergunta | Fórmula no recorte | Composição | Fora desta etapa |
|---|---|---|---|---|
| Evolução do caixa realizado | Quanto entrou, saiu e permaneceu? | Série diária ou semanal: saldo inicial declarado do intervalo + líquidos de extrato na data de efetivação | Abre as linhas do intervalo | Sem extrato confirmado, o gráfico não recebe zero |
| Fluxo projetado até 13 semanas | Quando pode faltar dinheiro? | Seção 8. Realizado e projetado com rótulos diferentes | Abre compromissos e hipóteses da data | Sem base declarada, mostra a agenda e diz que não há saldo projetado |
| Agenda de vencimentos | O que vence agora? | Títulos em aberto por vencimento: vencidos, 7 dias, 8–30, 31–90 | Abre a obrigação. Não usa data de pagamento | Já existe em parte nas listas a pagar e a receber; a agenda unificada é a fatia 3 |
| Entradas e saídas por categoria | Onde se concentra? | Soma do líquido realizado por categoria, mais a faixa «sem categoria» | Abre as linhas. Participação = valor ÷ soma do recorte | Denominador zero: «sem movimentação classificada neste recorte», sem percentual |
| Fluxo por iniciativa | Quais iniciativas geram ou consomem caixa? | Entradas e saídas atribuídas, mais compartilhadas e não atribuídas, uma vez | Regra de atribuição visível | Sem regra de saldo inicial por iniciativa, não há saldo da iniciativa |
| Conciliação e qualidade | Quanto está explicado? | Quantidade e valor: conciliado, divergente, sem correspondência, não classificado. Denominador = linhas confirmadas do recorte | Abre cada grupo | Sem extrato, o indicador diz «extrato ainda não coletado» |

Cores repetem o significado e vêm com rótulo. Valor exato disponível por foco e toque. Sem pizza como visão principal. Sem misturar cobrado e líquido no mesmo eixo.

## 11. O que esta revisão não autoriza

Nova capacidade ou infraestrutura da Spider. Cliente direto Finance → Mercado Pago. Scraping. Execução de pagamento, estorno ou transferência. Importação produtiva de arquivo real. Saldo inicial produtivo. Infraestrutura paga nova. Publicar os exemplos sintéticos como se fossem a Loja.

O trabalho já concedido no 027 e no 028 não se pede de novo. A decisão que ainda falta, antes de qualquer linha real entrar em produção, é a autorização de importar um arquivo da conta já confirmada. O desenho da fatia, os testes com arquivo sintético e o schema candidato não dependem dessa autorização e estão no plano de entrega.
