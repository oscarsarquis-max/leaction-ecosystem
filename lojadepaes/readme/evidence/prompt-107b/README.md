# Prompt 107B — envio isolado de falhas do Hub

29/10/2026. Hub só simulado por HTTP. Nenhum pedido nem cobrança foi criado em produção para este teste.

A pré-criação do Pix no aceite automático fica num savepoint. Falha de cobrança não desfaz o pedido. A rota pública de checkout continua gravando `sanitized_error` e respondendo 422.

## Antes da correção

| Cenário | HTTP | Pedido | Avisos | PaymentRecord | Commits no envio |
|---|---|---|---|---|---|
| H1 Pix válido | 200 | confirmed, reserva | order_accepted, order_auto_accepted_admin | pending, `hub-107b`, sem erro | 1 |
| H2 timeout | 200 | confirmed, reserva | os mesmos | pending, sem referência, erro “timeout ao criar cobrança no ActionHub” | 2 |
| H3 HTTP 503 | 200 | confirmed, reserva | os mesmos | pending, sem referência, erro “ActionHub indisponível” | 2 |
| H4 HTTP 409 | 200 | confirmed, reserva | os mesmos | pending, sem referência, erro “chave de cobrança já usada com outro valor ou método” | 2 |
| H5 2xx sem order_id | 500 KeyError | não existe | nenhum | nenhum | 0 |
| H6 amount_cents não numérico | 500 ValueError | não existe | nenhum | nenhum | 0 |
| H7 URL inválida | 500 InvalidURL | não existe | nenhum | nenhum | 0 |
| H8 falha em attach_hub_checkout | 500 RuntimeError | não existe | nenhum | nenhum | 0 |

H2 a H4 já não derrubavam o envio, mas `start_checkout` fazia `session.commit()` no erro. H5 a H8 escapavam de `ConfirmationError` e o `rollback` de `get_db` apagava o pedido. Nesta versão do httpx, `InvalidURL` não é `HTTPError`.

## Depois da correção

| Cenário | HTTP | Pedido | Avisos | PaymentRecord | Commits no envio |
|---|---|---|---|---|---|
| H1 | 200 | confirmed, reserva | order_accepted, order_auto_accepted_admin | pending, `hub-107b`, QR gravado, sem erro | 1 |
| H2 a H8 | 200 | confirmed, reserva | os mesmos | pending, sem referência e sem erro gravado | 1 |

O cliente abre o pagamento depois pela página do pedido. Nessa rota, HTTP 503 continua 422 e o erro “ActionHub indisponível” permanece em `sanitized_error`.

O fato de CRM e a fidelidade continuam no mesmo ponto de antes, anteriores ao savepoint. `_parse_result` não foi alterado.

## Publicação

Imagem `lojadepaes:prod-20261029a` (`sha256:d029e9c3be89ee85724ab90b3b6aa300c3a173ea44946ae3efeb7cb4e6cba31d`). Retorno `lojadepaes:prod-20261028c`. Backup `lojadepaes-20261029T180119Z.sql.gz`, 118572 bytes, gravado antes da troca. Alembic `d5e9f2a18b33` (head). No contêiner, `commit_on_error` e `begin_nested` estão em `storefront_orders.py`. Health e ready públicos: `{"status":"ok","service":"lojadepaes"}`.

O bundle `index-CHig2hvs.js` manteve o SHA-256 `efc5c09e9fba1b6e16cb9799c2b6ddf76736f0df1acc517946c5424397a94bcc`. O teste `frontend/src/admin/stageContract.test.ts`, de 29/10, importa `node:fs` e faz o `tsc` da imagem falhar. Ele não entra no bundle. O `.dockerignore` deixa esse arquivo de fora do build, que é o mesmo conjunto de fontes do frontend com que `prod-20261028c` foi gerada. O arquivo de teste permanece no repositório.

O `.tar` local `C:\Temp\loja-prod-20261029a.tar` foi apagado depois do deploy confirmado. Os quatro `.tar` anteriores em `C:\Temp` ficaram no lugar.
