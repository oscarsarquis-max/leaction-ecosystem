# ACTIONFINANCE_REV_INVESTIGACAO_RECEBIMENTO_061

10/11/2026. Leitura apenas. Código, banco, Spider, Loja e Hub não foram alterados. Nenhum endpoint de gravação foi chamado.

O exemplo são as duas linhas da Loja de Pães com valor cobrado de 7000 centavos, método `card`, descrição "Checkout avulso por valor", criação em 27/10/2026 e atualização em 10/11/2026. As duas têm a mesma forma. Não há coluna JSON nem payload bruto em `pay_receipt_transaction`.

## Onde o pagador se perde

A Loja envia nome e e-mail no checkout avulso. O Hub grava os dois no payload da ordem e cria o usuário com um e-mail sintético no domínio `@amount.hub.local`. A lista do Pay escolhe primeiro o e-mail desse usuário. O e-mail e o nome do payload ficam para trás. O `subject_id`, que também carrega o e-mail, só seria usado se não houvesse e-mail.

A Spider repassa `payerKind` e `payerLabel` como recebeu. O Finance grava `EMAIL` e esse rótulo técnico, com procedência `ACTIONHUB_PAY`. A tela aplica a regra do relato 028: sufixo `@amount.hub.local` vira **Pagador não identificado**. O campo não chegou vazio. Chegou a identidade técnica no lugar do contato.

## Contrato 1.4

O pedido `financialList` aceita só empresa, sistema de origem, ambiente, cursor e limite. O corpo de cada item não está nesse schema. Os campos que a resposta pode trazer, pelo normalizador da Spider e pela ficha de integração, são: transação, referência (hoje o id da ordem no Hub), referência do processador, situação original e normalizada, valor cobrado, valor pago, moeda, datas, classificação, método, tipo e rótulo do pagador, aplicação, descrição, processador, situação no processador e canal.

Não há, nesse item, nome do pagador, documento, número do pedido da loja, itens, parcelas, taxa, valor líquido nem data de liberação. O id do Mercado Pago só aparece se vier como referência do processador.

## Mapeamento no Finance

`toView` lê os campos da lista acima, menos canal, vínculo da empresa, valor cobrado repetido e origem do valor. Esses quatro chegam na resposta e não são gravados. Não existe coluna para nome, documento, itens, parcelas, taxa, líquido ou data de liberação, então nada disso é descartado de uma resposta que não os traz.

## Tabela

| Dado | Na Loja/Pay | Na resposta da Spider | Gravado no Finance | Exibido na tela |
|---|---|---|---|---|
| Pagador | Loja tem nome e e-mail. O Hub também, no payload. A lista publica o e-mail sintético do usuário | `payerKind=EMAIL`, rótulo técnico, procedência do Pay | Preenchido, forma `email_tecnico`. Não é o contato | "Pagador não identificado". O rastreio guarda a referência técnica e diz que não é contato |
| Pedido | A loja tem o número público. O payload do Hub tem `order_reference`. A lista troca os dois pelo id da ordem | `orderReference` igual ao id da transação | Igual ao id da transação. O número da loja não está na coluna | Mostra essa referência, não o pedido da loja |
| Itens | A loja tem os itens. No Hub o produto é só "Checkout avulso por valor" | Não há campo de itens. A descrição comercial é o nome desse produto | Descrição preenchida com o checkout avulso. Sem coluna de itens | Descrição. Sem itens |
| Método e parcelas | Método `card` no payload. Parcelas só na chamada ao Mercado Pago, sem volta para o payload da lista | `paymentMethod=card`. Sem parcelas | `card`. Sem coluna de parcelas | O código `card`. Sem parcelas |
| Taxa | O retorno do Mercado Pago não é copiado para o payload lido pela lista | Ausente | Sem coluna neste recebimento | Ausente |
| Líquido | O pago gravado é o valor da transação, não o líquido depois da taxa | `paidAmountMinor` igual ao cobrado. A ficha diz que isso não é líquido | Pago preenchido e igual ao cobrado | "Valor pago", não líquido |
| Data de liberação | A observação do Mercado Pago não copia essa data | Ausente | Sem coluna | Ausente. Há criação e atualização na origem |
| ID Mercado Pago | Gravado no payload e na referência de gateway | `processorReference` preenchido | Preenchido nas duas linhas. O valor não é reproduzido aqui | No rastreio, como id do processador. Fora do bloco principal |
| Situação | Ordem paga e situação `approved` no processador | Confirmada, com a situação do processador | `CONFIRMED`, `approved`, ambiente de produção, classificação real | Situação na origem e situação no processador |

## Conclusão

O Finance pode deixar o rótulo do método em português e explicar que o pagador exibido é uma referência técnica, porque esses dois fatos já estão gravados.

Não dá para o Finance sozinho mostrar o nome, o e-mail de contato ou o número do pedido da loja: o que chegou foi o e-mail sintético e o id da ordem no Hub, e não há payload bruto para reler.

Recuperar o contato depende do Pay publicar o nome e o e-mail do payload, em vez do usuário sintético. A Spider já repassa o rótulo que receber.

O número do pedido da loja também depende do Pay: ele está no payload e a lista o substitui pelo id da ordem.

Taxa, líquido, data de liberação, parcelas, itens e documento não entram na lista. Itens e documento teriam de sair da Loja ou do payload; taxa, líquido e liberação teriam de ser lidos do Mercado Pago pelo Pay e, se forem campos novos, aceitos pela Spider e pelo Finance.
