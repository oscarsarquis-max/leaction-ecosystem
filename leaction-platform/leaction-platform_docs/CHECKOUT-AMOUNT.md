# Checkout avulso por valor — Action Hub

Rota nova, isolada dos contratos Inove (`POST /v1/checkout/sessions`, exige `sku` + plano) e PanelDX (`POST /v1/payments`, exige `sku` + campos PanelDX). **Não altera permissões nem validações desses fluxos.**

## Rota

`POST /v1/checkout/amount`

Autenticação: `Authorization: Bearer <webhook_secret>` ou `X-App-Secret`, com `app_id` no corpo **igual** ao aplicativo autenticado. O `app_id` do corpo não troca de identidade.

Autorização extra: o `app_id` precisa estar em `AMOUNT_CHECKOUT_APP_IDS` (lista separada por vírgula no ambiente do gateway). Outros apps permanecem sem acesso.

Não envie `webhook_url` no corpo. A notificação sai pelo `webhook_url` cadastrado em `app_registry`.

### Corpo

| Campo | Unidade / regra |
|---|---|
| `app_id` | identidade autenticada |
| `order_reference` | referência estável do pedido na Loja |
| `payment_request_id` | identificador estável da solicitação de pagamento |
| `amount_cents` | inteiro positivo em centavos (1–10_000_000), moeda `BRL` |
| `currency` | `BRL` |
| `description` | até 120 caracteres; sem plano/SKU/crédito/assinatura |
| `customer.email` | subject do Hub para esta cobrança (e-mail) |
| `customer.name` | opcional |
| `method` | `pix` ou `card` (padrão `card`, para não quebrar clientes que já falam cartão) |
| `return_origin` | origem HTTP(S) que precisa estar em `return_origins` do app |
| `return_to` | caminho absoluto da Loja (`/pedido/...`) |
| header `Idempotency-Key` | obrigatória |

Resposta: `order_id`, `status`, `method` (`pix`|`card`), `checkout_mode` (`hub_brick` ou `pix`), `amount_cents`, `currency`. Cartão inclui `checkout_url` (Brick no Hub: `/dashboard?checkout=`). Pix inclui `pix.qr_code`, `pix.qr_code_base64`, `pix.ticket_url` e `pix.date_of_expiration` **somente** se o Mercado Pago devolver esses campos — o Hub não inventa validade nem chave Pix estática.

Mesma chave + mesmo payload (incluindo `method`) reutiliza; mesma chave + payload diferente → 409. Troca de método exige `payment_request_id` nova após `POST /v1/checkout/amount/:orderId/cancel` (cancela Pix pendente via `PUT /v1/payments/:id { status: cancelled }`).

## Reconciliação

- `GET /v1/checkout/amount/:orderId?app_id=`
- `GET /v1/checkout/amount?app_id=&payment_request_id=`

Mesma autenticação S2S. Só devolve cobranças `source=amount_checkout` daquele app.

## Unidades

Contrato satélite↔Hub: **centavos inteiros**. Conversão para o decimal do Mercado Pago só em `lib/money-cents.js` (aritmética de inteiros). O fluxo legado PanelDX/Inove continua com `valor_negociado` em reais.

## Notificações (Mercado Pago → Hub → satélite)

Webhook MP existente (`POST /webhooks/mercadopago`). Para pedidos `source=amount_checkout`:

- valida o valor aprovado contra `amount_cents`
- **não** cria contrato, créditos nem entitlement
- **não** dispara o webhook legado em `orders.payment_url`
- enfileira `webhook_outbox` com JWT HS256 (`iss=leaction-hub`, secret do app)

Eventos: `PAYMENT_CONFIRMED`, `PAYMENT_UPDATED`, `PAYMENT_INCONSISTENT` (valor divergente).

Pix usa a mesma Payments API do cartão (`POST /v1/payments` com `payment_method_id=pix`). Não há chave Pix estática da padaria. Sandbox de cartão TEST não habilita Pix automaticamente.

## Estorno

O Hub **não** expõe endpoint autenticado de estorno por valor/referência nesta etapa. Pedido pago e não atendido exige procedimento operacional no painel Mercado Pago. Não há botão fictício de estorno.

## Cadastro de teste da Loja

Use o procedimento já existente de `app_registry` (admin de apps do Hub). Não invente token em documentação. Depois:

1. `AMOUNT_CHECKOUT_APP_IDS=lojadepaes`
2. `return_origins` com a origem da vitrine de teste (`http://127.0.0.1:5175`)
3. `webhook_url` da Loja (`http://127.0.0.1:5075/api/v1/webhooks/actionhub`) — em local o worker entrega na LAN; o Mercado Pago continua exigindo URL pública para o webhook **dele** no Hub

## Compatibilidade

Inove e PanelDX seguem nas rotas antigas. Produto interno `AMOUNT_CHECKOUT` não concede créditos.
