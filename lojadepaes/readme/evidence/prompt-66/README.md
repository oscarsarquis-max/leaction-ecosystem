# Prompt 66 — Pedidos e solicitações de data invisíveis no admin

## Causa comprovada

Não houve pedido novo em 05–06/10/2026. O banco (`lojadepaes` no Lightsail, então Alembic `c8e2f1a90b64`) tinha 14 pedidos; o mais recente é `LP2BEEEFEB18` (28/09). Os dois eventos de 05–06/10 são **solicitações de data**, com `date_request_received` **sent**.

O e-mail do teste do proprietário é o persistido `Solicitação de data — Loja de Pães` às 06/10 00:59 BRT (prefixo `51a91eff`). Não foi reenviado. O WhatsApp do cliente coincide com a solicitação das 05/10 21:30 BRT (prefixo `15bd4592`), sem presunção de identidade.

O proprietário olhou **Pedidos**. Essas solicitações só existiam no fim da **Agenda**. `order_submitted_admin` não disparou porque não houve pedido. Solicitação de data não tinha aviso administrativo.

A fila antiga também escondia `submitted` padrão não pago com mais de 24 h (`LPB0DA668D3F`). Isso não explica o teste de 05–06/10.

## Correção

- Toda encomenda `submitted` permanece na lista até aceite ou cancelamento.
- Pedidos avisa quantas solicitações de data estão abertas e leva à Agenda.
- O painel de datas fica no topo da Agenda.
- Diagnóstico `GET /api/v1/admin/ops/attendance-health` (sem PII). Log `lojadepaes.ops` se `hidden_submitted > 0`.
- Novas solicitações de data enfileiram `date_request_received_admin` no `MAIL_OPS_TO` já autorizado. As duas históricas não foram reenviadas (`admin_date_outbox=0` após o deploy).

## Isolado

`tests/test_prompt66.py` e `tests/test_prompt66_browser.py` (executados). Sem cobrança nem e-mail real. A referência criada aparece na lista administrativa do navegador isolado. Relato: `isolated.json`.

## Produção

| Item | Valor |
|---|---|
| Imagem | `lojadepaes:prod-20261006a` |
| Rollback de app | `prod-20261001j` |
| Bundle | `/assets/index-CzCz9NC1.js` |
| Alembic | `e1b6d3f82a19` |
| Backup | `20261006T043842Z` |

Leitura no container da API (mesma consulta de `list_orders`): 9 na fila, 3 `submitted` visíveis incluindo `LPB0DA668D3F`, 2 datas abertas, `discrepancy=false`. Health/ready ok. Sem sessão administrativa no navegador — confirmação visual do painel **não** foi feita.

## Reconciliação pós-deploy

1. `GET /api/v1/health` e `/ready`.
2. No container: `attendance_health` — `hidden_submitted` deve ser 0; `queue_total` = `list_orders` sem filtro; `open_date_requests` é fila da Agenda, não de Pedidos.
3. Conferir as duas solicitações de data em `/admin/agenda` e os `submitted` em `/admin/pedidos`.
4. Não restaurar dump antigo sobre vendas atuais. Rollback de app: imagem `prod-20261001j` sem reverter a constraint se já aplicada.
