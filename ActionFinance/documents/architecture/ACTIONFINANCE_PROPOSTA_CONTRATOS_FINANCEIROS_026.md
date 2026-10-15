# ACTIONFINANCE_PROPOSTA_CONTRATOS_FINANCEIROS_026

Data: 15/10/2026. Baseline AF-BL-023 revisão 1.1. Versionamento do Prompt 024. Esta proposta **não** está aprovada e **não** autoriza implementação nem publicação.

Produto publicado: **0.1.0**. Schema Finance: Flyway **V20**. Imagem web: `actionfinance-web:14`, digest `sha256:cb0619f2f1b4b38c86da43298cc11cd1979dbe25dc4dc5f25c1f6533072c528a`. A Spider não foi alterada. O diff local de `ActionHubPayListIdentity.java` não foi publicado.

## 1. O que está publicado de fato

| Artefato | Onde está | O que faz |
|---|---|---|
| Pedido de lista | código do Finance, `contractVersion` **1.4**, propósito `FINANCIAL_EXTERNAL_LIST` | `extensions.financialList`: `companyId`, `originSystem=ACTIONHUB_PAY`, `environment` (`HOMOLOG` \| `SANDBOX` \| `PRODUCTION`), `cursor` opcional, `limit` 1–50 |
| Pedido de consulta pontual | mesmo cliente, `contractVersion` **1.3**, propósito `FINANCIAL_EXTERNAL_LOOKUP` | uma referência externa, não a lista |
| Esquema 1.4 e 1.5 no repositório da Spider | `contracts/satellite/1.4` e `1.5` | 1.5 já existe e acrescenta `biblioteca` (`appId=lojadepaes`). O bloco `financialList` de 1.5 repete o de 1.4. Não há esquema JSON do item de recebimento |
| Adapter commitado da lista | `ActionHubPayListIdentity` no Git, 124 linhas, commit `c407591d` (01/10/2026) | não copia pago, pagador, método, aplicação nem classificação |
| Working tree da Spider | +43 linhas no mesmo arquivo | reencaminharia esses campos. Continua local. Fora desta autorização |
| Hub, configuração | `.env.production.example` aponta o gateway para a instância `paneldx-database`, banco `leaction_hub` | origem documentada dos pedidos. Não foi aberta nesta leitura |
| Instância `actionhub-prod`, banco `actionhub_prod` | 0 tabelas | não é a origem dos pedidos. A ausência aqui não apaga o Hub |
| Empresa no Finance | `id=624023a4-57e3-415c-b7d0-925ca1acd3b7`, `code=loja-de-paes`, `name=Loja de Pães`, fuso `America/Sao_Paulo`, `is_demo=false`, ativa | não existe entidade de iniciativa. «Unidade» no cadastro de contraparte é filial de pessoa, não Loja/Inove/SegSense |

Consumidor atual da lista: o ActionFinance. Ele lê um mapa e ignora chave que não conhece. Isso **não** torna um campo novo compatível se o mesmo nome mudar de significado. Outros propósitos (seguro, capital de giro, biblioteca) usam o mesmo envelope de satélite e rejeitam propriedade fora do esquema (`additionalProperties: false` no pedido).

## 2. Caso R$ 90, campo a campo

Identidade: `b6cf9b7a-d8d3-42a7-873e-818f17133322`. Não é prova de pago.

| Campo | Origem que se espera | O que o Finance gravou | Leitura |
|---|---|---|---|
| Identidade | pedido Hub | a própria | atravessou |
| Cobrado | centavos do pedido | `9000` | atravessou. Não é o pago |
| Pago | só com confirmação explícita no payload | nulo, `paid_amount_absent=true` | não chegou. Não preencher com 9000 |
| Situação | status do pedido | `CONFIRMED` | rótulo de situação não confirma valor pago |
| Atualização | instante do pedido | 2026-10-06 15:01:49Z | atravessou |
| Classificação real/teste | `live_mode` ou flag de teste no payload | `INDETERMINATE`, motivo vazio | o item chegou sem `REAL` ou `TEST`. O envelope `PRODUCTION` não classifica |
| Aplicação, pagador, método, processador | cadastro/payload do Hub | nulos | o adapter commitado não os copia. O admin do Hub, segundo o proprietário, mostrou cliente e pago: isso é outra leitura, não a lista |

Tentativa `b39468f1-3ab2-4396-b070-15514fb34ee4`: `FAILED`, 0 criados, 0 atualizados. A seguinte, `1f159934-4b30-446c-8c2c-3f84176e3025`: `EMPTY`, 1 página, 0 criados, 0 atualizados. `EMPTY` não é enriquecimento. `COMPLETED` no Monitor não é commit no Finance.

## 3. Mapa de fatos

Fatos externos, que atravessam a Spider quando houver capacidade:

| Fato | Identidade estável | Não é |
|---|---|---|
| Observação de cobrança | `originSystem` + `transactionId` | extrato, saldo, título |
| Movimento de conta | conta + id do provedor | nova receita só porque houve liberação |
| Posição informada | conta + instante da fonte | saldo gerencial |

Fatos internos do Finance, que **não** precisam ir à Spider:

| Fato | Identidade | Dono |
|---|---|---|
| Iniciativa | empresa + código (`loja-de-paes`, `inove4us`, `segsense`) | Finance |
| Obrigação a receber ou a pagar | empresa + id do título | Finance |
| Rateio | versão de regra, com autor e vigência | operador |
| Alocação / conciliação | par de fatos + valor alocado | operador confirma |
| Saldo gerencial e projeção | base declarada + movimentos válidos | Finance calcula |

Cardinalidade: uma empresa, várias iniciativas, várias contas. Uma conta recebe várias iniciativas. Pagador, cliente comercial, favorecido e titular da conta são papéis diferentes. E-mail não vira documento fiscal.

Atribuição à iniciativa é pendente até haver evidência (`app_id` ou escolha do operador). Rateio não é inferido pelo integrador.

## 4. Contrato proposto — observação de cobrança

Não alterar o pedido 1.4. Não enfiar estes campos no 1.5, que já tem outro significado (`biblioteca`). O número do próximo contrato de satélite fica **em aberto** até nova listagem do catálogo no dia da implementação. O nome de trabalho é `receipt-observation`, candidato somente depois de 1.5.

Pedido: o mesmo `financialList` 1.4. Resposta: o mapa atual mais campos aditivos. Chave nova não muda chave antiga.

Item (exemplo **sintético**, não enviar ao produto):

```json
{
  "transactionId": "b6cf9b7a-d8d3-42a7-873e-818f17133322",
  "orderReference": "b6cf9b7a-d8d3-42a7-873e-818f17133322",
  "commercialApplication": "lojadepaes",
  "commercialDescription": "Plano exemplo",
  "amountMinor": "9000",
  "amountAbsent": false,
  "paidAmountMinor": "9000",
  "paidAmountAbsent": false,
  "currency": "BRL",
  "currencyScale": 2,
  "originalStatus": "approved",
  "normalizedStatus": "CONFIRMED",
  "paymentMethod": "pix",
  "processorName": "Mercado Pago",
  "payerKind": "EMAIL",
  "payerLabel": "cliente.exemplo@dominio.invalid",
  "payerProvenance": "ACTIONHUB_PAY",
  "classification": "REAL",
  "classificationReason": "live_mode=true",
  "originRevision": "2026-10-06T15:01:49.498Z",
  "fieldPresence": {
    "paidAmountMinor": "PRESENT",
    "payerLabel": "PRESENT"
  }
}
```

Regras do item:

| Regra | Significado |
|---|---|
| `amountMinor` / `paidAmountMinor` | inteiro não negativo em unidades mínimas, transportado como string de dígitos para não usar ponto flutuante. `currencyScale` é 2 para `BRL`. Outra moeda exige escala explícita |
| Pago | só se a origem confirmar o valor. Situação `CONFIRMED` não preenche pago |
| `fieldPresence` | `PRESENT`, `ABSENT` (a origem não tem), `UNKNOWN` (esta resposta não trouxe). `UNKNOWN` não apaga valor já gravado. `ABSENT` grava ausência. Correção explícita usa revisão nova, não omissão |
| Vários pagamentos no mesmo pedido | a unicidade é o pagamento, não o pedido |
| Classificação | `REAL`, `TEST` ou `INDETERMINATE`. Evidência aceita: `live_mode` ou flag de teste no payload. Envelope `PRODUCTION` não basta |
| Paginação | cursor opaco, página estável, limite máximo 50. Página vazia é `EMPTY` no Finance, não sucesso de enriquecimento |
| Idempotência | `messageId` + `idempotencyKey` do pedido; o item, por `transactionId` + `originRevision` |

Estados do run no Finance, produtores diferentes:

| Contagem | Quem produz | Não é |
|---|---|---|
| Retornados na página | Spider/Hub | criados no Finance |
| Criados / atualizados / inalterados | commit no Finance | contador do Monitor |
| Rejeitados | validação local | falha do provedor |
| Pendentes | classificação do Finance (`ENVIRONMENT_UNPROVEN`, `PAID_AMOUNT_MISSING`, outras) | erro de transporte |
| `COMPLETED` no Monitor | projeção da Spider | `SUCCESS` do run |

`RUNNING`, `SUCCESS`, `EMPTY`, `PARTIAL`, `FAILED` continuam sendo os únicos status do run.

## 5. Contrato proposto — movimento de conta

Fonte: extrato ou relatório da conta, ou arquivo importado com prévia. Não é `LIST_PAYMENT_TRANSACTIONS`. Não passa a ser sincronização automática da cobrança.

Exemplo sintético:

```json
{
  "accountRef": "mp-conta-exemplo",
  "movementId": "mp-mov-exemplo-1",
  "direction": "IN",
  "kind": "RELEASE",
  "amountMinor": "8500",
  "currency": "BRL",
  "currencyScale": 2,
  "effectiveAt": "2026-10-07T12:00:00Z",
  "relatedPaymentId": "b6cf9b7a-d8d3-42a7-873e-818f17133322",
  "availability": "AVAILABLE"
}
```

`kind`: `PAYMENT_IN`, `PAYMENT_OUT`, `FEE`, `TRANSFER`, `CONTRIBUTION`, `WITHDRAWAL`, `HOLD`, `RELEASE`, `REFUND`, `CHARGEBACK`, `REVERSAL`, `INFO`. `RELEASE` ligado a um pagamento já observado não é outra receita. `REFUND` aponta o movimento ou pagamento original; não apaga a linha antiga. Sem comando de executar pagamento, estorno ou transferência.

## 6. Contrato proposto — posição

Snapshot, não saldo único.

```json
{
  "accountRef": "mp-conta-exemplo",
  "observedAt": "2026-10-15T12:00:00Z",
  "currency": "BRL",
  "availableMinor": "100000",
  "heldMinor": "5000",
  "toReleaseMinor": null,
  "coverage": "PARTIAL"
}
```

`toReleaseMinor: null` significa que a fonte não informou. Não gravar zero. `available` e `held` se somam só se a fonte disser que não se sobrepõem; o esquema guarda `componentsOverlap: true|false`. Três saldos permanecem separados: informado pelo MP, gerencial (inicial comprovado + movimentos), projetado.

## 7. O que fica só no Finance

Obrigação: competência, vencimento, parcelas, valor em unidades mínimas, moeda, iniciativa ou «não atribuída». Liquidação registrada pelo operador e movimento importado depois casam pela alocação, com teto do valor ainda não alocado. Sugestão não confirma. Transferência própria, financiamento, ativo e despesa operacional são classes do operador, com autor, não do integrador.

Datas: instante em UTC (`date-time`). Data civil de competência e vencimento no fuso `America/Sao_Paulo`, sem hora. Não comparar dinheiro em binário de ponto flutuante.

## 8. Matriz campo–fonte

| Campo | Fonte | Transporte hoje | Persistência Finance | Uso | Situação |
|---|---|---|---|---|---|
| Id e cobrado | pedido Hub | lista 1.4, adapter commitado | gravados | lista | disponível |
| Situação original | pedido Hub | lista | gravada | não prova pago | disponível |
| Pago confirmado, método, aplicação, pagador, live_mode | payload/cadastro Hub | não saem do adapter commitado | vazios nos 11 | pendência | bloqueado pelo contrato publicado |
| Tarifa, líquido, liberação, saldo | conta MP | não há capacidade | não existe | conciliação | ainda não coletado |
| Iniciativa | decisão já tomada: mesma empresa | não há tabela | não existe | análise | a criar no Finance, sem nova empresa |
| Rateio | operador | não trafega | não existe | despesa compartilhada | ainda não coletado |
| Título, baixa, movimento gerencial | Finance | não devem nascer da lista | 0 / 0 / 0 hoje | obrigações | interno; a lista não os cria |

## 9. Diferença e consumidores

| Mudança | Consumidor antigo | Consumidor novo diante do produtor antigo |
|---|---|---|
| Campos aditivos no item da lista | o Finance atual ignora chave desconhecida e continua gravando id e cobrado | trata ausência como `UNKNOWN` e não apaga |
| Novo propósito de movimento | não é chamado pelo cliente 1.4 | não dispara sozinho |
| Iniciativa no Finance | seletor continua `Loja de Pães`; não renomear nem mover vínculo | — |

Não reutilizar `amountMinor` para pago. Não reutilizar `environment` do envelope como classificação do pagamento.

Recomendação: primeiro incremento só de observação de cobrança, aditivo, sem novo número até a autorização de implementação recontar o catálogo (1.5 já ocupado). Movimento e posição ficam em contratos separados, depois. A mudança necessária é de contrato e adapter da lista, não do núcleo de governança da Spider. Isso continua dependência futura, não trabalho deste ciclo.

## 10. Primeiro incremento, quando houver autorização

Recuperar, na observação já existente, pago confirmado, método, aplicação, pagador e classificação, sem criar título, baixa ou movimento. A tentativa `b39468f1` permanece `FAILED`. Uma página vazia não conta como recuperação.

Incremento seguinte: movimentos de conta, com arquivo pré-validado ou capacidade nova. Depois: posição e conciliação. Cada um com autorização própria. Importar extrato não herda a autorização da sincronização de cobranças.

## 11. Questão ainda aberta

O agrupamento das iniciativas na mesma empresa já está decidido.

Despesa compartilhada entre Loja, Inove4us e SegSense: o rateio será (a) informado em cada lançamento, (b) uma regra vigente com percentuais e data, ou (c) permanecer inteiro em «não atribuída» até alguém o classificar? A proposta recomenda (c) como padrão e (b) só quando o operador gravar a regra. Não recomenda inferir pelo favorecido.
