# Plano de entrega — tesouraria AF-BL-023 revisão 1.2

Data: 15/10/2026. Projeto: [PROJETO_TESOURARIA_MP_023_R1_2](ACTIONFINANCE_PROJETO_TESOURARIA_MP_023_R1_2.md). Produto no ar: **0.1.2**. Esta revisão de requisitos não é versão de produto. Aceite: **não atribuído**.

Nada deste plano foi implantado. Não houve importação, migration nova nem mudança da Spider.

## 1. Provas que continuam abertas e não são refeitas aqui

| Pendência | Estado | Por que não se refaz o incremento |
|---|---|---|
| Detalhe autenticado do pagamento `b6cf9b7a-d8d3-42a7-873e-818f17133322` e segunda sincronização sem gravação nova | Aberta desde o 027 | Exige a sessão já autenticada do operador. Não há senha nem cookie neste trabalho. O agregado já lido (12 PRODUCTION, 10 pendências, SUCCESS 1/11) não substitui o detalhe nem a repetição |
| Acabamento 028 | Publicado em 0.1.2 | A tela não será redesenhada. Falta a conferência humana de zoom real de 200% numa janela larga. Viewport estreito não conta |

Essas duas pendências não bloqueiam o desenho do extrato. Bloqueiam apenas declarar o 027 encerrado.

## 2. Fatias

| Fatia | Entra | Fica para a seguinte | Produto, quando existir |
|---|---|---|---|
| **T1** Extrato e vínculo | Lote de arquivo, linha com identidade estável, prévia, sugestão de vínculo com `pay_receipt_transaction`, armazenamento original. Sem confirmação automática | Categoria confirmada, iniciativa confirmada, conciliação confirmada, posição, gráfico | Planejado **0.2.0**. Não é candidata hoje |
| **T2** Classificação e conciliação | Categoria, iniciativa, rateio com regra, confirmação e desfazer vínculo | Posição e gráficos | Planejado 0.2.x ou 0.3.0 conforme o tamanho real na hora |
| **T3** Posição e compromissos | Três bases, agenda, filtros do mesmo recorte em lista e totais | Série e gráficos | Depende de saldo inicial comprovado ou de posição informada pela fonte |
| **T4** Fluxo e gráficos | Os seis instrumentos, com composição | IA preditiva: não entra | Só com a cobertura declarada em cada indicador |

T1 já grava os campos que T2–T4 leem, vazios e diagnosticados (`UNCLASSIFIED`, `NOT_COLLECTED`). Não deixa a coluna para «criar depois» em cima de linha já confirmada sem lugar para o diagnóstico.

## 3. Primeiro incremento executável (T1)

### O que o operador consegue fazer

Enviar um arquivo de relatório de dinheiro em conta ou de liberações, ver a prévia, corrigir o vínculo da conta se o arquivo não identificar a conta, e confirmar o lote. Linhas com id estável gravam. Linhas sem id ficam na prévia e não entram. Uma segunda carga do mesmo id atualiza só lacuna, e não apaga valor já confirmado. Ao lado de cada linha, o Finance mostra sugestão de recebimento já gravado quando a referência coincide, com o rótulo «sugestão». Confirmar o lote não confirma o vínculo e não cria título, baixa nem movimento de caixa.

A tela só entra na segunda barra, sob Recebimentos, com o nome **Extrato**, quando essa prévia funcionar. Até lá não há item de menu.

### O que não entra em T1

Cliente Mercado Pago. Chamada nova à Spider. Arquivo real em produção. Saldo inicial. Execução de pagamento. Classificação automática pelo favorecido. Gráfico. Tratar a lista de cobranças como extrato.

### Dependências reais

| Dependência | Situação |
|---|---|
| Recebimentos 0.1.2 | Publicados. T1 só lê |
| Pedidos 1.3 e 1.4 e adapter do 027 | Permanecem. T1 não os altera |
| Capacidade de extrato na Spider | Não existe. T1 não a cria |
| Acesso efetivo da conta ao `settlement_report` ou `release_report` | A documentação oficial descreve gerar, listar e baixar CSV/XLSX, com colunas configuráveis incluindo `SOURCE_ID` e `EXTERNAL_REFERENCE`. Nenhuma chamada foi feita com a conta desta empresa. A API não comprova o acesso |
| Conta MP ↔ empresa `624023a4-57e3-415c-b7d0-925ca1acd3b7` | Não persistida. A prévia de um arquivo real, no futuro, pede confirmação do operador. T1 de laboratório usa conta sintética |
| `financial_account` e `cash_movement` | Existem para baixa gerencial. T1 não grava neles. A linha de extrato é outra tabela, para não nascer movimento `SETTLEMENT` sem baixa |
| `settlement` | Continua 1 título por baixa manual. Não serve de alocação N:N |

### Schema candidato

Flyway **V21**, ainda não escrito e não aplicado. A aplicação desta fatia não sobe se V21 não estiver aplicado. Checksums V1–V20 intactos.

Tabelas candidatas, todas com `tenant_id` e `company_id`:

| Tabela | Papel |
|---|---|
| `financial_initiative` | Códigos `loja`, `inove4us`, `segsense`. Nome amigável. Sem saldo |
| `external_account_link` | Conta Finance ↔ origem `MERCADOPAGO` + referência opaca. Sem segredo |
| `statement_batch` | Arquivo ou relatório: hash do original, nome, período declarado, moeda, conta, autor, estado `PREVIEW` ou `CONFIRMED` |
| `statement_line` | Id estável, direção, natureza, datas, bruto/tarifa/líquido com ausência própria, referência externa, diagnóstico de categoria e iniciativa |
| `statement_original_row` | Linha crua protegida, sem uso em indicador |
| `statement_link_suggestion` | Recebimento candidato, força da evidência, estado `OPEN`. Sem estado `CONFIRMED` em T1 |

Índice único: conta + origem + id do evento. Repetir o arquivo não cria outra linha.

### Contrato

Não há `contractVersion` novo. O 1.5 continua da biblioteca. O nome de trabalho do movimento, se um dia houver capacidade na Spider, continua o da 026: movimento de conta, número de satélite a recontar na autorização. T1 não envia esse contrato.

O arquivo é fonte `FILE`. Colunas ausentes ficam `UNAVAILABLE`. Colunas desconhecidas ficam no original e não entram na soma. Moeda diferente de `BRL` é rejeitada na prévia desta etapa, com a frase «moeda sem regra de conversão».

### Testes que bloqueiam a candidata

Arquivo sintético, ids sintéticos, sem o UUID real do pagamento de R$ 90.

| Caso | Resultado exigido |
|---|---|
| Mesmo `SOURCE_ID` duas vezes | Uma linha |
| Mesma data e mesmo valor, ids diferentes | Duas linhas |
| Página ou arquivo sobreposto | Atualiza lacuna; não apaga líquido já gravado |
| Linha sem id | Permanece na prévia; lote pode confirmar as outras |
| Liberação com referência de recebimento já gravado | Sugestão aberta; `cash_movement` não aumenta; o recebimento não muda de valor |
| Tarifa e líquido na mesma linha | O realizado usa o líquido; tarifa aparece na composição e não se soma de novo |
| Estorno | Linha nova relacionada; a original permanece |
| Transferência | Não entra como receita nem despesa de resultado |
| Favorecido conhecido | Iniciativa e categoria ficam «Não atribuída» |
| E-mail `@amount.hub.local` citado no arquivo | Não vira cliente |
| Empresa vizinha | Não vê lote, linha, sugestão nem agregado |
| Repetir a carga | Contagem de criados estável; sem título, baixa ou movimento novos |
| Fuso `America/Sao_Paulo` na virada do dia | A data civil de efetivação não muda por causa do dia UTC |
| V21 ausente | A aplicação não aplica o lote |

Regressão do que já está no ar: lista e detalhe de recebimentos 0.1.2, filtros, «Pagador não identificado», sync sem criar título. Suíte `PayReceiptSyncIT` continua exigindo `cash_movement` inalterado.

### Recuperação

| Se | Volta |
|---|---|
| A candidata nem chegou a produção | Nada a recolher |
| A imagem subiu e V21 não | O serviço não confirma lote. Recolher a imagem anterior `actionfinance-web:16` / `sha256:bcf11a54e4017cd5d4e64efce860ee1e47cfc716f77698980f8c3c33fbb34dec` |
| V21 subiu e o lote é de laboratório | Desfazer o vínculo de sugestão. Linha confirmada não se apaga; marca-se retirada de conferência, com autor. Sem `DELETE` do fato externo |
| Rollback da imagem | Não desfaz V21 nem linhas já gravadas |

Não há ensaio isolado neste ciclo. O ensaio é pré-condição da implantação futura, com a mesma empresa sintética, antes de qualquer arquivo real.

### Autorização que T1 ainda não tem

Importar arquivo real da conta de produção. Saldo inicial. Qualquer chamada ao Mercado Pago. Mudança da Spider. T1 de laboratório, com arquivo sintético identificado, cabe no desenho sem essa autorização. A carga produtiva é decisão posterior, com o vínculo da conta confirmado na prévia.

## 4. Prévia visual

Exemplos **sintéticos**. Não são a Loja, não são saldo e não entram em produção.

Desktop, largura ampla. Faixa azul, marca branca, duas barras. Sem sidebar.

```text
Recebimentos    Pagamentos    Cadastros
A receber    Transações importadas    Extrato

Extrato da conta                          [Enviar arquivo]
Conta Mercado Pago — exemplo sintético, não é a empresa do seletor
Período 01/10/2026–15/10/2026 pela efetivação no extrato    Limpar

Cobertura: arquivo de exemplo, 4 linhas, 1 não importável.
Posição informada pela conta: não coletada.
Saldo gerencial: indisponível, falta saldo inicial comprovado.

Efetivação   Descrição                         Líquido      Situação
06/10/2026   Liberação PIX-SINT-90             R$ 85,00     Sugestão de vínculo com recebimento sintético de R$ 90,00. Tarifa R$ 5,00 não somada de novo
07/10/2026   Tarifa de saque exemplo           R$ 3,50      Sem categoria. Não atribuída
08/10/2026   Transferência entre contas        R$ 200,00    Transferência própria. Fora do resultado
—            Linha sem identificador estável   —            Não importável. Permanece na prévia

Divergência de exemplo: saldo inicial do arquivo R$ 1.000,00 + créditos R$ 85,00 − débitos R$ 203,50 = R$ 881,50. O arquivo de exemplo declara final R$ 880,00. Diferença R$ 1,50. Sem ajuste automático.

Caixa projetado de exemplo, com base declarada hipotética de R$ 881,50:
  a pagar sintético vencido     R$ 1.000,00
  menor saldo                   R$ 118,50 negativos em 20/10/2026, se o vencimento se confirmar
```

Celular, 360 px. Os mesmos fatos em cartões. Filtro de período em duas datas. Valores inteiros visíveis. A diferença de R$ 1,50 e o projetado negativo aparecem em texto, não só em cor. «Abrir linha» e «Abrir sugestão» são botões. A descrição longa quebra em duas linhas no cartão e fica inteira no detalhe.

Lista vazia de exemplo, filtro que não encontra: «Nenhuma linha neste período». Empresa sem extrato: «Extrato ainda não coletado». Não são o mesmo texto e não são R$ 0,00.

## 5. Ordem quando a implementação for aberta

1. Testes do dicionário e da deduplicação em arquivo sintético, antes da tela.
2. V21 só no ensaio isolado.
3. Prévia e confirmação de lote sintético.
4. Regressão dos recebimentos 0.1.2.
5. Item **Extrato** na segunda barra.
6. Imagem nova, manifesto 024, rollback para `:16`.
7. Arquivo real somente com autorização própria e com a conta confirmada na prévia.

Até o passo 1 ser pedido, o produto permanece 0.1.2 e o banco permanece V20.
