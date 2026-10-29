# Financeiro, conciliação e repasses

29/10/2026. Quatro conceitos separados. A experiência desejada continua sendo uma cobrança ao cliente por compra.

## O que está comprovado

Caminho atual: Loja cria a tentativa → Hub Pay → Mercado Pago → outbox ou consulta → Loja aplica no `PaymentRecord` → indicador e, se for falha persistente de verificação, alerta operacional.

O registro guarda valor esperado, pago e estornado em centavos, moeda BRL, método Pix ou cartão, referência da cobrança Hub, ID do provedor, horário de confirmação e erro saneado (`models/payments.py:12`). O evento de integração deduplica pelo identificador externo. Preencher ID vazio numa confirmação já aplicada não repete aviso, fidelidade nem estado operacional: coberto por teste isolado em 29/10/2026, não por nova operação real.

Alerta de falha de verificação aos 90 segundos, um e-mail e um push por ocorrência, encerrado na recuperação: teste isolado. Pagamento só aguardando o cliente não dispara.

Não há, no código da Loja nem no fluxo de amount checkout examinado, participação de terceiro, saldo retido, obrigação de parceiro ou repasse. Não há rota administrativa de estorno. Contestação não tem fila própria.

O relatório de 28/10 descreve a publicação dessas correções. A imagem da Loja não foi reinspecionada nesta auditoria. Os arquivos do Hub conferidos em 29/10 são os hashes informados, no processo iniciado em 28/10 17:46:41.

## Quatro conceitos

| Conceito | Hoje | Kit |
|---|---|---|
| Compra no carrinho | Um envio, várias linhas, um pedido | Pode reunir kit e pão avulso |
| Cobrança do cliente | Uma tentativa ativa por esse pedido | Continua uma, se a política ratificar. Várias cobranças seriam desvio do objetivo, não equivalente |
| Participação econômica | Não existe. O valor é da Loja | Regra versionada daquela compra: Loja, parceiro, transporte, taxas, quem financia desconto, frete e perda |
| Repasse efetivo | Não existe | Dinheiro liberado no provedor, retido, obrigação, pagamento da obrigação, extrato |

Pago no provedor não é saldo liberado e não é valor pago ao parceiro.

## Três hipóteses comerciais

Nenhuma está escolhida. A recomendação de piloto está em [decisoes-para-ratificacao.md](decisoes-para-ratificacao.md).

| Hipótese | Contrato e risco | O que o software precisaria | O que não decide sozinho |
|---|---|---|---|
| Loja vende o kit e compra os componentes | Cliente contrata a Loja. Parceiro é fornecedor. Reembolso ao cliente é obrigação da Loja; o ajuste com o fornecedor segue o contrato de fornecimento | Pedido, recebimento, conta a pagar versionada, aceite do componente, conciliação | Nota, tributo e documento fiscal |
| Vários recebedores no provedor | Cada um autoriza recebimento. Estorno e contestação têm regra de quem devolve | Onboarding, OAuth, divisão, liberação, extrato por participante | Disponibilidade na conta da Loja |
| Remuneração por receita ou marca | Licença, exclusividade, base e vigência, além da produção | Direito versionado separado do repasse do componente | Existência do contrato. Não foi inferida |

Validação com contador e jurídico é dependência. Um campo de comissão não escolhe o responsável fiscal.

## Provedor

Documentação consultada em 29/10/2026, sem contato comercial e sem leitura da conta:

- Split 1:N depende de vendedores de carteira assessorada e contato com a equipe do Mercado Pago. [Pré-requisitos](https://www.mercadopago.com.br/developers/pt/docs/split-payments/split-1-1/prerequisites). Não está comprovado para esta conta (F08).
- O modelo 1:1 documentado divide vendedor e marketplace com OAuth do vendedor. [Integração](https://www.mercadopago.com.br/developers/pt/docs/split-payments/split-1-1/integration-configuration/integrate-marketplace). Isso não cobre um kit com quantidade arbitrária de participantes no checkout atual.
- Relatórios de movimentação, liberação e vendas têm cadência própria. [Relatórios](https://www.mercadopago.com.br/developers/pt/docs/reports/introduction). Webhook não é disponibilidade de dinheiro.

Itens ainda sem prova na conta: onboarding de recebedor, revogação de OAuth, limite de recebedores, taxa e arredondamento, divisão de frete e desconto, retenção, reembolso parcial depois do repasse, saldo insuficiente do parceiro, contestação e reprocessamento.

A área de acompanhamentos, com ofertas externas, não é essa modalidade. F13.

## Livro proposto

Movimentos append-only, em centavos. Partidas dobradas são uma alternativa se o volume de compensações justificar; não é abertura de instituição financeira. A escolha fica para a etapa de viabilidade.

Invariantes, para qualquer alternativa:

- Centavos exatos, arredondamento explícito e residuo atribuído a uma parte nomeada.
- Uma transação do provedor não gera duas apropriações.
- A soma das participações da versão vendida reconcilia com o total da compra, na regra daquela versão.
- Estorno e repasse são movimentos novos ligados à origem. Não são edição do saldo anterior.
- Ajuste manual tem autor, motivo e vínculo.

Relatório por participante, quando existir: período, fonte, bruto, desconto, tarifa, frete, líquido previsto, líquido realizado, retido, pago e a pagar. Datas separadas: venda, aprovação, liberação, repasse.

## Métricas para ratificar depois da linha de base

Não há amostra de produção nesta auditoria. Não aprovar meta numérica agora.

| Trecho | Origem → destino | O que medir quando houver amostra |
|---|---|---|
| Confirmação | Aprovação no provedor → evento durável no Hub | p50/p95/p99 e idade do evento mais antigo |
| Aplicação | Evento do Hub → `PaymentRecord` na Loja | mesma forma, mais taxa de reprocessamento |
| Alerta | Falha de verificação sustentada → e-mail e push, contados à parte | prazo já desenhado em 90 s para falha de sync; não é prazo de liberação de dinheiro |
| Kit | Componente embalado → kit conferido | compromissos vencidos |
| Entrega | Kit despachado → prova de entrega | compromissos vencidos |
| Dinheiro | Participação prevista → extrato realizado | divergência em centavos |

“Tempo real” significa prazo medido para o evento elegível e recuperação quando o provedor falha. Não significa saldo disponível porque o webhook chegou.

## Conciliação desejada

Pedido e composição vendida → cobrança → transação do provedor → participações da versão → eventos de estorno ou contestação → valor liberado → obrigação → pagamento da obrigação. Divergência aparece como fila, com link para o registro, sem sumir atrás do total.
