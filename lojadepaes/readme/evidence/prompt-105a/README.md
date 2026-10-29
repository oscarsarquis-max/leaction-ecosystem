# Prompt 105A — evidência de 27/10/2026

Coleta de produção: 27/10/2026 20:05:39 −03 (23:05:39 UTC).
Imagem em execução: `lojadepaes:prod-20261027f`. Nenhuma correção de código desta sessão foi publicada.

## Incidente dos dois pedidos

Leitura somente. Nenhuma cobrança, estorno ou mudança de produção/entrega foi feita nesta leitura.

| Verificação | LPA8FC361791 | LP91E9C35D1B |
|---|---|---|
| Transação efetiva | Cartão Visa Mercado Pago `185349985529`, aprovado/acreditado 17:10:26 −03, BRL 70, estorno 0. Pix `186394563492` cancelado `by_collector`, sem aprovação | Cartão Visa Mercado Pago `186395637864`, aprovado/acreditado 17:12:09 −03, BRL 70, estorno 0. Pix `186395690348` cancelado `by_collector`, sem aprovação |
| Vínculo | Referência externa do cartão = cobrança Hub `d79861f6-65a6-48b9-be3f-d2aa1729dcd0`, pedido LPA8FC361791 | Referência externa do cartão = cobrança Hub `97de3e93-a7b4-45ef-8716-0c411c23eec4`, pedido LP91E9C35D1B |
| Loja às 20:05 −03 | Cartão `paid`, 7000 centavos; Pix `cancelled`. Pedido `confirmed` | Cartão `paid`, 7000 centavos, sincronizado 17:14:29 −03; Pix `cancelled`. Pedido `confirmed` |
| Aceite | `system:auto-accept` às 17:04 −03, antes do Pix | `admin:admin@lojadepaes.com.br` às 18:45:03 −03, depois do cartão já pago |
| Aviso | `order_accepted` aceito pelo serviço às 17:04; `payment_approved` aceito às 19:24:56 −03. Aceite do serviço não prova a caixa de entrada | `payment_approved` às 17:14; `order_accepted` às 18:45. Mesma ressalva |
| Operação | Continua confirmado, com a reserva anterior. Produção e entrega não foram avançadas | Igual |

A Loja ainda não grava o ID Mercado Pago na tentativa de cartão (`mp_payment_id` vazio). O vínculo usado é a cobrança do Hub, conferida no provedor por ID e por referência externa.

Pix: o cancelamento `by_collector` foi registrado pelo lado recebedor quando a troca de método abriu o cartão (17:08 e 17:11). Não há auditoria de clique de uma pessoa. O código da Loja cancela a tentativa anterior nessa troca.

Busca somente leitura por outros pedidos `confirmed`, `in_production` ou `ready` com tentativa ainda `pending` e referência Hub: **0**. Nenhum outro pedido foi alterado.

## Proteção contra recorrência — local, não publicada

A causa da perda: a aprovação do cartão gravou `PAID` no Hub sem o evento da outbox de encomenda; a Loja só reconciliava enquanto o pedido estava em avaliação. `LPA8FC361791` já estava aceito automaticamente.

O diff local, ainda não publicado, cobre outbox na aprovação, recuperação depois do aceite e worker de 30 segundos com lote de 10. O intervalo de 30 segundos é a frequência do ciclo, não a medição de capacidade.

`server.js` local já diferia do publicado antes desta intervenção. Não publicar o arquivo inteiro sem comparar com o processo em execução.

A suíte `pay-regression.test.js`, executada antes das alterações, já falhava em `sessão/plano continua em valor_negociado e não é confundida com checkout avulso` (linha 158, `undefined` versus `true`). Não foi afrouxada.

## Carrinho — clareza local

Implementado no frontend local, sem publicação:

- “Adicionar ao carrinho” no pão e no Criador; a adição não envia pedido.
- Aviso: a compra ainda não foi finalizada e o pedido ainda não foi enviado.
- “Ir ao carrinho para finalizar” e “Continuar escolhendo”.
- Página `/pedido/novo` intitulada “Seu carrinho”, com “Finalizar compra” como único envio.
- Página do pedido distingue aceite pendente, pagamento pendente, confirmação financeira e verificação indisponível.

Testes de interface desta sessão: QuantityReview, CheckoutPage, ProductShelf, Header, BreadBuilder, OrderStatusPage.pay e OrderDetail.payment — passaram. Não houve navegador autenticado nem captura de celular/desktop. C01–C12 não foram executados como jornada integrada.

## Adendo — alerta, capacidade, publicação, confirmação tardia e ID Mercado Pago

Nada disto foi publicado. A imagem em execução continua `lojadepaes:prod-20261027f`. Os dois pedidos de produção não foram alterados.

### Falha persistente

Limiar: **90 segundos** (`PERSISTENT_SYNC_FAILURE`), três ciclos de 30. Pagamento apenas pendente, sem erro de consulta, não abre ocorrência.

A mensagem leva a referência do pedido, a natureza registrada, o horário da última verificação e o caminho `/admin/pedidos/{id}`. O texto diz que isso não significa que o cliente deixou de pagar. E-mail operacional e Web Push usam a mesma ocorrência. Um ciclo posterior não cria outra mensagem. Na recuperação, o resumo da ocorrência recebe “encerrada”; e-mail e push permanecem um de cada.

Teste isolado em `lojadepaes_test`, 27/10/2026: nenhum aviso aos 0 s e aos 89 s; um e-mail e um push aos 90 s; as duas contagens seguiram em 1 aos 150 s e depois da quitação. Aguardando o cliente: 0 e-mails de alerta.

### Capacidade do worker

Critério de aprovação: lote de 10 diante de fila maior; pendências novas consultadas antes dos pagamentos históricos já quitados; duração do ciclo medida, bem abaixo de tratar os 30 segundos como se fossem o tempo de atendimento; webhook de confirmação aplicado enquanto a consulta externa ainda está em andamento, sem esperar o fim dela.

Medição local, fila de 15 (12 quitados históricos e 3 pendentes), cada consulta com 0,01 s de espera:

| Prova | Medido | Critério |
|---|---|---|
| Atendimento dos novos | 0,273 s para 10 registros; as 3 pendências foram as primeiras consultas | pendências antes dos históricos; tempo medido < 30 s |
| Hub lento e indisponível | 0,225 s no ciclo com 0,20 s de falha injetada; o registro continuou pendente | a duração acompanha a espera real; no ciclo seguinte, com o Hub respondendo, o mesmo registro ficou pago |
| Webhook durante a consulta | a confirmação entrou em 0,026 s; a consulta seguiu por mais 0,30 s | abaixo do `lock_timeout` de 0,25 s, logo o banco não segurou a linha durante a rede; um único aviso `payment_approved` |

O bloqueio de cada registro é solto antes da consulta do registro seguinte. A ordenação atende `pending`/`unknown` antes de `paid`.

### Bloqueio entre registros do mesmo lote

O teste de um único webhook durante a consulta (0,024 s nesta execução) não cobre o registro seguinte. O cenário novo usa duas sessões de banco, com A e B no mesmo lote. O worker conclui A e, com B ainda parado na consulta, outra sessão aplica o webhook de A.

Medição: o webhook de A concluiu em **0,013 s**, abaixo do limite de 0,25 s, com B ainda em consulta. Ao liberar B, os dois ficaram pagos. Cada um teve um único aviso `payment_approved`. Não houve segundo registro de cobrança, nem fidelidade, nem mudança de estado do pedido.

A correção persiste e libera as alterações de A antes de esperar a rede de B. Cada registro continua atômico; a repetição do mesmo evento não gera outro efeito; o que ficou pendente continua elegível no ciclo seguinte.

### Retorno financeiro

Voltar a Loja e, em seguida, o Hub sem outbox **não** é rollback seguro: essa sequência restaura a perda da confirmação de cartão. Ela fica registrada só como defeito, não como plano.

Artefatos, conferidos em 28/10/2026 12:27 −03. O nome do teste não identifica o arquivo.

Loja de retorno: imagem `lojadepaes:prod-20261027f`, id `sha256:8c5b48336a55f3e078c7d8dc8b605bad3484d80df25ff51a96f43ff90ee47141`, criada 2026-10-27T16:08:02Z, contêiner desde 2026-10-27T16:11:58Z. Arquivo `/app/backend/app/domain/payment_webhooks.py`, 7095 bytes, SHA-256 `ad8147299228bc11d7bb06e58b2572c14aa63736b475145bf1c8df7876a6ad74`.

O teste anterior tinha carregado o git HEAD, 6936 bytes, SHA-256 `dd4043f246e96e92bd4da5bb35623b6c34eeda130cd38af09f6ddef36672824e`. A diferença é só CRLF na imagem contra LF no git. O texto coincide. A repetição do teste de aprovação usou os bytes da imagem e passou: uma aplicação, repetição duplicada, um aviso e um registro.

Hub em execução, que não é o retorno: PM2 `gateway-api` id 1, pid 562132, Node 20.20.2, script `/var/www/leaction-platform/services/gateway-api/server.js`, criado 2026-10-15T13:30:24Z. Os arquivos em disco são anteriores a esse início.

| Arquivo no processo | SHA-256 | `fulfillVerifiedCardPayment` |
|---|---|---|
| `domain/mp-webhooks.js` | `34457287f375c6a7c1e5fa4583645acab1861b7f5d116b7c5ad802be4b1a093e` | ausente |
| `domain/amount-checkout.js` | `5faf44a6074f3d105ffa098e1d2ff44a115bb9a3106f33f489a49fe27dc7c1ab` | a outbox existe; o cartão síncrono não passa por ela |
| `payment-fulfillment.js` | `1043b1239275454bb414b071ef1d27228a75860fd9a4aed8a10647289a49b87c` | igual à cópia local |
| `server.js` | `f1533f7dda8523cc9b480f804c9062f2e67af345282e3eacd872870e6db6cc83` | ausente |

Hub de retorno, só local, ainda sem imagem: `domain/mp-webhooks.js` SHA-256 `3983720d936e7bbd46d102587d46c8d455efe6016ef79ebd61221e26fbd6ac1d` e `domain/amount-checkout.js` SHA-256 `28c75227ff0a75d5dc54e86922987d02ba89be5a7ac7923d5ee6adfc0d50819b`. O nome `hub-confirm-durable-20261028` aponta para esse par. `payment-fulfillment.js` é o mesmo hash do processo. O `server.js` local, SHA-256 `03c8f5178a180005097b108b3fdde2ce25c9183be89a5ecf050fa5fdba69c5f7`, é outro arquivo e ainda não foi comparado linha a linha com o do processo.

Sequência, se a Loja precisar voltar:

1. Manter no Hub o par local `mp-webhooks.js` `3983720d…` e `amount-checkout.js` `28c75227…`. Não repor os arquivos do processo de 15/10.
2. Repor a Loja pela imagem `sha256:8c5b48336a55f3e078c7d8dc8b605bad3484d80df25ff51a96f43ff90ee47141` (`lojadepaes:prod-20261027f`).
3. Confirmação que chegar nesse intervalo entra na outbox do Hub de retorno e a Loja `27f` aplica uma vez.

Não há passo seguinte que troque o Hub pela versão sem outbox.

Teste isolado, sem deploy: o handler publicado da `27f` aplicou a aprovação do Hub de retorno e a repetição do mesmo evento ficou duplicada, com um aviso e um registro. A Loja local do 105A fez o mesmo com outro pedido. Um terceiro pedido, sem evento, permaneceu pendente — é a perda que a versão proibida reintroduz. No Hub local, a aprovação síncrona gravou um evento; a repetição não criou outro; falha da outbox não deixou o pedido pago.

Contenção, somente se o Hub durável já tiver sido removido: o defeito reintroduzido é o cartão ficar `PAID` no Hub sem entrega à Loja. Não abrir nova cobrança. A recuperação é repetir a aprovação pelo `fulfillVerifiedCardPayment`, que devolve o evento único. Com a Loja do 105A, a operação recebe o alerta de falha persistente aos 90 segundos. Com a Loja `27f` esse alerta não existe, então a operação precisa ser avisada pelo e-mail operacional antes de qualquer reversão do Hub.

`server.js` local já diferia do publicado. Antes de qualquer publicação, comparar esse arquivo com o processo em execução. Esta etapa não publicou.

### Confirmação anterior ao aceite

Pedido ainda `submitted`, pagamento aprovado às 17:10:26 −03, evento aplicado com a trava nova já no código. O registro financeiro fica pago, com esse horário. O pedido continua `submitted`, sem aceite fabricado e sem início de produção. Nova cobrança continua recusada com “o pagamento abre depois do aceite de A Loja”.

### ID Mercado Pago na Loja

A consulta pública do Hub passa a expor o `gateway_reference` numérico quando o payload não tem `mp_payment_id`. Teste Node `amount-observation` cobrindo `185349985529`: passou.

Na Loja, um registro antigo já pago e sem esse ID recebe o identificador na consulta canônica. Não nasce segundo `payment_approved`, nem evento de fidelidade, nem mudança de estado operacional, e o horário de confirmação permanece o original.

## Fechamento em 28/10/2026

O `server.js` em execução (`f1533f7d…`, 52.004 bytes) e a cópia local (`03c8f517…`) diferiam em dois pontos: as rotas de cartão e o registro local da Biblioteca Spider, que não está no servidor. A publicação não substituiu o arquivo inteiro. O arquivo publicado é o processo de 15/10 com a importação de `fulfillVerifiedCardPayment` e a troca só nas duas respostas de cartão aprovado (`POST /payments/card` e `POST /payments/sandbox-card`). A outra chamada de `fulfillOrderPayment` permanece. A Biblioteca não entrou nesta publicação.

| Arquivo publicado no Hub | SHA-256 | Conferido no disco após o restart |
|---|---|---|
| `server.js` | `2f2ab384625d2d34b2d3fa6dff3ca4f2007758cc2712152c2194a392980a1aaa` | 3 ocorrências de `fulfillVerifiedCardPayment`; 0 de `registerSpiderBibliotecaRoutes` |
| `domain/mp-webhooks.js` | `3983720d936e7bbd46d102587d46c8d455efe6016ef79ebd61221e26fbd6ac1d` | par durável |
| `domain/amount-checkout.js` | `28c75227ff0a75d5dc54e86922987d02ba89be5a7ac7923d5ee6adfc0d50819b` | par durável |
| `payment-fulfillment.js` | `1043b1239275454bb414b071ef1d27228a75860fd9a4aed8a10647289a49b87c` | inalterado |

PM2 `gateway-api` reiniciado em 2026-10-28T16:21:28Z. Pid novo `590620`. `GET http://127.0.0.1:4001/health` respondeu `ok: true`. Cópia anterior em `/tmp/hub-105a-backup-20261028T162128Z`. Não repor essa cópia: ela é o Hub sem outbox do cartão.

Jornadas C01–C12 no banco isolado `lojadepaes_test`, pelo envio real do carrinho (`submit_order` / `quote_lines`), não por pedido já fabricado: 12 passaram em 17,24 s. Compra conjunta de 1 + 2 unidades fecha em um pedido, duas linhas, três unidades, R$ 74,70 e um pagamento. Variantes do mesmo produto não se misturam. A revisão envia só o carrinho final. Adaptação deixa o conjunto aberto até o aceite, que libera um pagamento do total. Conjunto regular reserva a data uma vez. Data passada e quantidade acima do limite nomeiam o pão e não gravam pedido. Repetir o envio devolve o mesmo pedido. Uma segunda compra do mesmo cliente e do mesmo total não herda o pagamento da primeira. Retorno interrompido permanece pendente e a consulta seguinte quita os R$ 74,70 sem segunda cobrança nem produção. Pedido quitado não oferece novo pagamento. Total adulterado é recusado. Cliente, e-mail de aceite, e-mail administrativo e resumo mostram a mesma referência, os itens e o total. A suíte de pagamento e e-mail já existente passou de novo: 36 testes.

Loja publicada depois do Hub. Backup `lojadepaes-20261028T163046Z.sql.gz` (116.121 bytes). Imagem `lojadepaes:prod-20261028a`, id `sha256:1da937081ff47e990ebbd9b1eae6bad54f0d566af4e8ad46e499742bc8581d6b`, container iniciado 2026-10-28T16:31:00Z. Alembic `d5e9f2a18b33` (head). Saúde pública `{"status":"ok","service":"lojadepaes"}`. O pacote servido `https://lojadepaes.com.br/assets/index-CHig2hvs.js` tem o mesmo SHA-256 do container, `efc5c09e9fba1b6e16cb9799c2b6ddf76736f0df1acc517946c5424397a94bcc`, e contém “Finalizar compra” e “Carrinho”.

Dentro da imagem: `payment_webhooks.py` `f1ebe848b9ac4f09a11eee937a7deb53f23ddf43b8bb01ba19b7b18f1ccb125d`, `payment_worker.py` `ba34276cf769fc745cf063fc853b0f09cd23a6425eecb65a870f6c348f195383`, `payment_alerts.py` `fb232fcc2fa2dfda36981d2c5ca92fdc421b4389baf6898d57bc3285ef6233ee`.

Retorno da Loja, se precisar: imagem `sha256:8c5b48336a55f3e078c7d8dc8b605bad3484d80df25ff51a96f43ff90ee47141` (`lojadepaes:prod-20261027f`), mantendo o Hub durável. Não publicar `lojadepaes:prod-20261027g` por cima. A entrega seguinte do Gigio parte de `prod-20261028a`. Esta imagem já carrega o texto do Gigio que estava na árvore; isso não substitui a validação própria do Gigio.

## O que continua pendente

- Conferência visual autenticada da fila, do detalhe e da página do cliente. A checagem publicada foi a saúde, a imagem, os hashes, o banco e a API. Nenhuma sessão administrativa foi usada neste adendo.
- `LP91E9C35D1B` continua o caso real em que o cartão foi registrado às 17:14 e o aceite manual ocorreu às 18:45. A correção nova impede nova cobrança antes do aceite; não reescreve esse histórico.
- `pay-regression.test.js`, linha 158 (`undefined` versus `true`, sessão/plano em `valor_negociado`), segue falha anterior. A asserção não foi afrouxada e não foi reexecutada neste fechamento.

## Adendo em 28/10/2026 — consulta do identificador

A causa era a projeção de `loadOwnedAmountOrder`. As duas consultas carregavam `gateway_ref` e não `gateway_reference`. O identificador numérico do Mercado Pago ficava só nessa coluna, a consulta ao provedor não acontecia, e a Loja mantinha “falta confirmação do valor recebido” mesmo com o cartão já pago.

Publicado no Hub, só `domain/amount-checkout.js`, SHA-256 `caad9b468514341106d7c2c21dee530ddaa02188be8ea23f5628b01406ae2f4f`. O processo `gateway-api` pid `591861` carregou esse arquivo em 2026-10-28T17:46:41Z. `server.js` permanece `2f2ab384625d2d34b2d3fa6dff3ca4f2007758cc2712152c2194a392980a1aaa` e `mp-webhooks.js` permanece `3983720d936e7bbd46d102587d46c8d455efe6016ef79ebd61221e26fbd6ac1d`. Cópia anterior do arquivo: `/tmp/hub-amount-backup-20261028T174641Z`. Repô-la reabre a falha de consulta; não é correção do incidente.

A Loja precisou de dois passos sobre a imagem financeira. `prod-20261028b` (`sha256:352fb8d31e8abb80098d5db11c6b04274348bfda7d8862abc5fa92f0ad7c171a`, backup `20261028T175122Z`, 118.415 bytes) completa metadados num pagamento que já está pago. A primeira aplicação real, porém, ocorreu ainda na `28a`, e a repetição da mesma observação parava antes de preencher o que tinha ficado vazio. `prod-20261028c` (`sha256:2f4d6f0266dba0645710aae1189fa23a1ac02318f6c7b458cc6f004386cb7078`, container desde 2026-10-28T18:13:22Z, backup `20261028T181312Z`, 118.435 bytes) preenche só campos vazios quando a mesma confirmação reaparece. Alembic continua `d5e9f2a18b33`. No processo: `payment_webhooks.py` `dc7b226cef0d90cc2278fd41d473ac6fed0012afa4e5c9c62a3148be61866f42`, `storefront_orders.py` `78c79f186ca331aa04df8c9be2feea5170aab3b142c5e7b5dcbeb0b25a9cd168`. Os comentários de cadência em `payment_worker.py` e `payment_alerts.py` foram junto; os intervalos não mudaram. Registro já pago volta a cada cinco minutos. A conferência das 11:40:22Z e a seguinte, 11:45:23Z de 29/10, mediram esse intervalo.

Testes isolados, sem pagamento real: no Hub, observação, recuperação da referência (R01–R05, R11, R12) e integração, 19 passaram antes da publicação. Na Loja, recuperação, pagamentos, alertas e jornadas C01–C12: 30 e 12 passaram antes da `28c`. O teste novo cobre a confirmação repetida que encontra metadados vazios. Uma falha inicial do alerta persistente vinha do gatilho de `updated_at` desligado no teste e não reativado; a asserção foi mantida e o gatilho volta ao fim de R09 e R10.

A base seguinte, inclusive o Gigio, parte de `lojadepaes:prod-20261028c` com este Hub. Retorno da Loja deste adendo: `prod-20261028b` para o último arquivo, ou `prod-20261028a` para o conjunto. Não restaurar os dumps por cima da operação e não publicar `prod-20261027g`.
