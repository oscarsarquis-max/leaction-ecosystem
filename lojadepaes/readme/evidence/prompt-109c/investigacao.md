# Investigação — 109C

Feita antes de alterar pedido, fila ou solicitação. A fila publicada é a do Prompt 109 (`lojadepaes:prod-20261030a`, Alembic `d5e9f2a18b33`). Não há prompt, script nem evidência com o nome 109A neste repositório. Onde o 109C cita `p109a-check.mjs`, a imagem do 109A ou a asserção de privacidade do 109A, vale o que o 109 já publicou: `scripts/p109-check.mjs`, a imagem `prod-20261030a` e os testes de privacidade do 109. Isso não muda o comportamento pedido nas seções A–G.

## 1. Ocupação

`committed_for_date` (`schedule.py`) soma os pães dos pedidos com `holds_capacity` cuja `production_local_date` é o dia. Não existe tabela de vaga separada. `occupy_capacity` só liga `holds_capacity` se ainda for falso; não cria outro registro.

Mudar `production_local_date` de um pedido que já segura vaga tira a vaga do dia antigo e coloca no novo, na próxima leitura. A conferência de capacidade da data nova tem de acontecer antes de gravar a data, senão o próprio pedido entraria na conta do dia novo. Pedido concluído em produção continua com `holds_capacity` verdadeiro, então a correção de registro também move a vaga. Anular por duplicidade desliga `holds_capacity` e a vaga sai.

## 2. Histórico que não é mudança de status

`OrderStatusHistory` só exige que `from_status` e `to_status` sejam status conhecidos. Os dois podem ser iguais. Quem lê o histórico é o detalhe do pedido. A fila, o board e o CRM não tratam a linha como transição: o status persistido continua em `orders.status`, e o CRM só emite fato quando o domínio chama `emit_order_fact`.

Decisão: a exceção de data e a anulação gravam uma linha com `from_status == to_status` e o motivo no campo `reason` (até 280 caracteres). Não cria tabela nova e não altera leitura de status. A fila não pode varrer o histórico de cada pedido. Por isso a migração também acrescenta, além de `requested_date`, as colunas `date_change_origin`, `date_change_reason` e `date_change_actor`: são o último registro da exceção, para a marca na fila e a linha do detalhe, sem consulta extra. O evento completo continua no histórico.

## 3. Aceite da solicitação

`accept_preview` devolve um dicionário livre (`accept_preview: dict` no schema). Dá para incluir `existing_orders` sem endpoint novo.

`accept_date_request` cria um pedido `submitted` com `source_date_request_id`, marca a solicitação `converted` e chama `confirm_order`, que ocupa a vaga e enfileira `order_accepted` (“Pedido aceito — pague e acompanhe”). Não procura outro pedido do mesmo cliente.

Decisão: o preview passa a listar os pedidos não cancelados do mesmo cliente. A ação nova `move_existing_order` chama a mesma mudança de data da seção A no pedido existente (origem `customer`), aponta `converted_order_id` para ele e encerra a solicitação como `converted`. Não cria pedido e não enfileira `order_accepted`. O aceite atual, quando não há pedido existente, permanece o mesmo. Se houver e o operador insistir em criar outro, o aceite exige `confirm_different_order`.

A exceção de dia fechado do aceite já é `operator_exception` em `occupy_capacity`, porque o pedido nasce com `source_date_request_id`. Mover um pedido que não nasceu de solicitação não tem essa marca. A mudança de data recebe `allow_closed_day` e, no mover, liga essa exceção quando o dia não é de produção.

## 4. Exclusão gerencial

`managerial_exclusions` já tem `reason`, `author_ref` e reversão. O índice único ativo é por assunto. `active_exclusion_sets` tira o assunto da fila, da agenda, das contagens e do envio de e-mail administrativo. O board coloca todo excluído em `audit:tests`. Os registros atuais são teste, reconhecidos pelo nome.

Decisão: coluna `kind` (`test` ou `duplicate`, default `test` nos registros atuais) e `original_order_id`. `reason` já existe; não se cria outra. Teste continua em `audit:tests`. Duplicidade vai só para `audit:duplicates` e sai das lentes operacionais pelo mesmo conjunto de exclusão ativa. O status persistido não muda. A etapa visível `voided` (“Anulado”, tom de cancelado) é calculada na leitura quando `kind` é `duplicate`.

Fidelidade: a reversão atual (`should_reverse`) só corre com pedido cancelado ou com estorno. Anular não muda o status e recusa pagamento `paid` ou com referência no provedor. Um carimbo aplicado, portanto, não tem como ser revertido por esse mecanismo. Se existir carimbo `qualify` aplicado, a anulação recusa e o relatório registra o motivo. O par de 30/10 não tem carimbo no pedido que será anulado.

## 5. E-mail

Os kinds vivem no mapa de `email_outbox.py` e no check `ck_email_outbox_kind`. O dedupe padrão é `{pedido}:{kind}`. O aviso corretivo já usa uma chave mais longa (`{pedido}:order_accepted:{chave}`), com o mesmo outbox, status `pending` ou `skipped`, e o retry do que ficou `pending`.

Decisão: kind novo `order_date_changed`, assunto “Sua encomenda {REF} mudou de data”, corpo com data anterior, data nova, pagamento já feito ou o caminho de pagamento do aceite, e o link do pedido. Com origem `customer`, a frase é “Conforme combinado com você, sua encomenda será entregue em {data} (pedido original: {data solicitada})”. Dedupe `{pedido}:order_date_changed:{data nova}`. Pedido concluído e correção pela entrega não enfileiram. Nenhum kind antigo muda de momento.

## 6. CRM

`emit_order_fact` só envia `pedido_aceitar` e `pagamento_registrar`, com `pedido_id` e `situacao`. Não há fato de atualização de pedido. Não se inventa tipo no Hub. Mudança de data e anulação não emitem fato.

## O que não muda

`ALLOWED_TRANSITIONS`, os status persistidos, pagamento, aceite automático e os avisos que já existem. A migração só acrescenta colunas e o kind de e-mail. O downgrade remove o que ela criou e apaga só as linhas `order_date_changed`, no mesmo padrão da revisão anterior de kinds, para o check voltar a fechar.
