# Matriz de notificações

Canal e kind como estão no código. `payment_available` **não** é kind: é booleano da visão pública (`storefront_orders.py` 883 e 964).

Dedupe de pedido: `enqueue_order_email` usa `{order.id}:{kind}` (`email_outbox.py` 277+). Pedido excluído como teste: dedupe `excluded:{order.id}` e status `skipped` no caminho admin (`enqueue_admin_order_email`). Sem transporte ou sem destinatário de operação: status `skipped`, não há segundo envio porque a linha já existe. Suíte deixa `LOJADEPAES_MAIL_IDENTITY_READY=false`, então as linhas nascem `skipped`.

Web Push (`web_push.py` 30–55 e 186): kinds `order_submitted_admin`, `order_auto_accepted_admin`, `date_request_received_admin`, `acceptance_update`, `payment_sync_alert`, `test`. Sem VAPID ou sem inscrição ativa, `enqueue_event_pushes` devolve 0. `test` não passa por essa função; só `enqueue_test_push`, que recusa se o VAPID não estiver configurado.

CRM (`crm_tracking.py`): `emit_order_fact` faz HTTP ao Sponge. Sem `LOJADEPAES_CRM_TRACKING_SECRET` só registra log e não persiste linha. A suíte zera o segredo.

Silêncio medido no contrato: `start_production` (com e sem exceção), `mark ready`, `complete`, `confirm_delivery`, `cancel` e `propose_production_date` não aumentam `email_outbox` do pedido nem `OpsPushDelivery` cujo `path` é `/admin/pedidos/{id}`. O aceite de solicitação, com VAPID fictício e inscrição falsa, cria um push `acceptance_update` em `awaiting`. O autoaceite cria `order_auto_accepted_admin`. O gateway de rede não é chamado.

| Kind | Canal | Gatilho | Destinatário | Dedupe | Supressão | Conteúdo essencial |
|---|---|---|---|---|---|---|
| `order_submitted` | e-mail cliente | `submit_order` sem autoaceite, `storefront_orders.py` 752 | e-mail do pedido | `{order.id}:order_submitted` | sem identidade SES → skipped | ref, data pedida, endereço, link protegido |
| `order_submitted_admin` | e-mail operação + push se VAPID | mesma ramificação, 753 | `LOJADEPAES_MAIL_OPS_TO`; inscrições push | kind admin do pedido | teste excluído; ops vazio → skipped | ref, data, itens, total, link do painel |
| `order_auto_accepted_admin` | e-mail operação + push | autoaceite, 750 | idem | kind admin | idem | “aceito automaticamente”, data, itens, total, link |
| `order_accepted` | e-mail cliente | `confirm_order`, `orders.py` 129 | cliente | `{order.id}:order_accepted` | SES | ref, data confirmada, itens, total, link de pagar |
| `acceptance_update_admin` | e-mail operação | `notify_acceptance`, `owner_alerts.py` 241–253 | ops | `acceptance:{request.id}:{order.id}` | ops vazio → skipped | resumo do pedido aceito a partir da solicitação |
| `acceptance_update` | Web Push (não é kind de `email_outbox`) | `record_owner_event` no mesmo aceite, linha 260 | inscrições | a mesma `event_key` | sem VAPID → 0 pushes | “Solicitação aceita” + ref |
| `payment_approved` | e-mail cliente | primeira quitação em `payment_webhooks.py` 248 | cliente | `{order.id}:payment_approved` | SES; webhook repetido não reenfileira | ref, itens, total, data; diz que não inicia produção |
| `payment_sync_alert` | e-mail operação + push | `review_sync_alert` após 90 s (`payment_alerts.py` 22, 75–77) | ops | id `sync-watch:{record.id}:…` | antes de 90 s não enfileira; ops vazio → skipped | ref, natureza da falha, link; não conclui que o cliente não pagou |
| `date_request_received` | e-mail cliente | `create_date_request`, `date_requests.py` 150 | cliente | sufixo da solicitação | SES | data pedida; não confirma fornada |
| `date_request_received_admin` | e-mail operação + push | linha 151 | ops | idem | ops vazio | ref da solicitação, data, link |
| `date_request_proposed` | e-mail cliente | ação `propose`, `date_requests.py` 216 | cliente | data proposta no sufixo | SES | data alternativa; não reserva |
| `date_request_available` | e-mail cliente (template) | **nenhum comando** chama; só `enqueue_date_request_email` se alguém passar o kind (`email_outbox.py` 74) | cliente | sufixo `available` | — | “há disponibilidade”; não reserva |
| `date_request_complete` | e-mail cliente | `request_date_request_completion`, `date_request_accept.py` 509 | cliente | solicitação + kind | SES | link protegido para completar endereço |
| `date_request_declined` | e-mail cliente | `close`, `date_requests.py` 228 | cliente | solicitação + kind | sem e-mail válido a ação nem grava | data e justificativa |
| `adaptation_proposed` | e-mail cliente | `evaluate_adaptation` ao propor, `adaptations.py` 264 | cliente | `{order.id}:adaptation_proposed` | SES | ref e link; silêncio não confirma |
| `adaptation_customer_replied_admin` | e-mail operação | resposta do cliente à proposta | ops | kind admin | teste excluído | pede nova avaliação; link do painel |
| `customer_verify` | e-mail cliente | `start_signup`, `customer_identity.py` 172 | e-mail informado | `customer:{challenge.id}:signup` | SES → skipped | código e link; o CPF não vai no corpo |
| `customer_resume` | e-mail cliente | mesmo emissor com purpose diferente de signup, linha 172 | e-mail | `customer:{challenge.id}:{purpose}` | SES | mesmo molde de código |
| `ops_attendance_summary` | e-mail operação | `enqueue_ops_attendance_summary`, `email_outbox.py` 586 | ops | chave recebida pelo chamador | ops vazio → skipped | contagens de pendência e link `/admin/pedidos` |
| `test` | Web Push | `enqueue_test_push`, `web_push.py` 217 | um aparelho | `test:{device.id}:{uuid}` | sem VAPID levanta `ValueError`; não cria e-mail | texto de teste |
| `pedido_enviar` | Sponge | `submit_order`, `storefront_orders.py` 757 | CRM | não há outbox | sem segredo: não persiste | situação `confirmed` ou `submitted` |
| `pedido_aceitar` | Sponge | `confirm_order` | CRM | não há outbox | sem segredo | fato do aceite |
| `pagamento_registrar` | Sponge | primeira transição financeira para `paid`, `payment_webhooks.py` 261 | CRM | não há outbox | repetição `was_paid` não reemite | `situacao=paid` |

## Transições que não avisam ninguém

Confirmado no código e na suíte `contract`:

- iniciar produção, com ou sem exceção de quitação
- marcar pronto
- concluir pela rota `complete` (Finalizado, sem carimbo de entrega)
- confirmar entrega
- cancelar
- nota interna
- correção assistida `ready → in_production`
- troca de método de pagamento (cancela a tentativa e abre outra; não enfileira kind)
- exclusão gerencial (não cria kind; tira o pedido da fila e pode suprimir aviso futuro)
- segunda chamada de aceite, de webhook com o mesmo `outbox_id`, de alerta de sincronização com a mesma ocorrência

`date_request_available` tem template e entra no CHECK do banco, e nenhum fluxo de `apply_date_request_action` o enfileira.
