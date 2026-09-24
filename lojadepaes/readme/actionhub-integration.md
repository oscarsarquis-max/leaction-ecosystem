# Integração financeira — ActionHub (cobrança avulsa)

A Loja de Pães **é dona do valor** em centavos BRL. O ActionHub cobra no Mercado Pago (Pix ou cartão Brick) e notifica a Loja. Não há SKU, plano, crédito nem assinatura neste fluxo.

Contrato no Hub: `POST /v1/checkout/amount` (isolado de Inove `/v1/checkout/sessions` e PanelDX `/v1/payments`). A API externa do Mercado Pago é `https://api.mercadopago.com/v1/payments` — não confundir com a rota legada do Hub `POST /v1/payments` (PanelDX). Documentação do Hub: `leaction-platform/leaction-platform_docs/CHECKOUT-AMOUNT.md`.

## Ambiente local desta validação

Hub usado: **local** (`http://127.0.0.1:4001` gateway, `http://localhost:4000` frontend, Postgres `leaction_hub` em `:5433`). Não é `actionhub.com.br`.

Loja: API `http://127.0.0.1:5075`, vitrine `http://127.0.0.1:5175`, Postgres Compose `lojadepaes` / banco `lojadepaes` em `:5438`.

### App no Hub

- `AMOUNT_CHECKOUT_APP_IDS` no `.env` da raiz `leaction-platform/` — incluir `lojadepaes` **sem** apagar outros ids já listados.
- Registro em `app_registry` (`app_id=lojadepaes`). Reutilizar a linha se já existir; o secret fica em `webhook_secret` (Hub) e `LOJADEPAES_ACTIONHUB_APP_SECRET` (`.env` da Loja). Não versionar, não colar no React, não imprimir.
- `webhook_url`: `http://127.0.0.1:5075/api/v1/webhooks/actionhub` (destino local; o Mercado Pago não alcança isso).
- `return_origins`: `http://127.0.0.1:5175` e `http://localhost:5175`. Sem `*`.
- Variáveis da Loja (privadas): `LOJADEPAES_ACTIONHUB_BASE_URL=http://127.0.0.1:4001`, `LOJADEPAES_ACTIONHUB_APP_ID=lojadepaes`, `LOJADEPAES_PUBLIC_ORIGIN=http://127.0.0.1:5175`.

Gerar secret só para linhas sem credencial: `node leaction-platform/scripts/generate-app-secrets.js` — o script imprime o valor no terminal; copiar direto para o `.env` da Loja e apagar o histórico do terminal. Não colar o secret em documentação.

### Marca na página de pagamento

A URL Brick leva `client=lojadepaes` (origem da Loja). O Hub escolhe o logo e as cores **dessa origem** em `client-branding.ts`. Inove, School e PanelDX permanecem com os temas já cadastrados; o recorte do logo da Loja é o mesmo da vitrine (não um quadrado 40×40 que esconderia o lettering).

Voltar após o Brick: `return_origin` + `return_to=/pedido/{ref}`. Sem origem, o Hub não deve cair no fallback Inove/PanelDX para caminhos `/pedido`.

## Unidades e métodos

- Contrato Loja↔Hub: centavos inteiros, moeda `BRL`.
- Conversão para o decimal do Mercado Pago só no adapter do Hub.
- `method=pix` devolve QR, copia-e-cola e `date_of_expiration` **somente** se o MP enviar. Sem chave Pix estática.
- `method=card` devolve URL Brick no Hub (`/dashboard?checkout=&client=lojadepaes`). O cartão Inove/PanelDX não muda.
- Troca de método: conciliar a tentativa anterior; se ainda pendente, o Hub cancela o Pix no MP e a Loja abre `payment_request_id` nova. Sem `replace`, a Loja recusa a troca.

## Reserva da fornada

- Pagamento **não** ocupa capacidade.
- O aceite administrativo em `/admin/pedidos` (`submitted` → `confirmed`) ocupa a data (`reservation_policy=admin_accept`).
- Pagar ≠ confirmar a fornada. A vitrine e o e-mail deixam isso explícito.

## Conectividade

| Trecho | Ambiente local |
|---|---|
| Browser → Loja | `http://127.0.0.1:5175` (proxy `/api` → `:5075`) |
| Loja → Hub | `http://127.0.0.1:4001/v1/checkout/amount` (Bearer do app) |
| Mercado Pago → Hub | **Não alcança localhost.** Precisa de HTTPS de homologação apontando só ao webhook MP do Hub, sem expor `/admin` sem senha |
| Hub → Loja | `http://127.0.0.1:5075/api/v1/webhooks/actionhub` (JWT `iss=leaction-hub`, secret do app) |
| Retorno Brick → pedido | `http://127.0.0.1:5175/pedido/{ref}` |

Não abra túnel para a API no loopback com `LOJADEPAES_ADMIN_LOCAL_PASSWORDLESS=true`.

## E-mail (Amazon SES)

O Hub já envia alerta operacional por **Amazon SES API** (`services/gateway-api/lib/ses-mailer.js`), região **us-east-2**, conta fora do sandbox. A Loja reutiliza o mesmo serviço e a mesma outbox (`email_outbox`): não há SMTP e não há segundo fluxo.

Configuração local (sem segredo): `LOJADEPAES_MAIL_BACKEND=ses`, `LOJADEPAES_SES_REGION=us-east-2`, `LOJADEPAES_MAIL_FROM=loja@lojadepaes.com.br`, `LOJADEPAES_MAIL_FROM_NAME=Loja de Pães`, `LOJADEPAES_MAIL_IDENTITY_READY=true` com identidade e DKIM verificados. Credencial: cadeia AWS padrão (a mesma do Hub), nunca no React.

**Remetente da aplicação:** `loja@lojadepaes.com.br` (não `pedidos@`). Identidade de domínio no SES `us-east-2`: verificação **Success**, DKIM **Success**. TXT `_amazonses` e 3 CNAME DKIM estão na zona `Z04478628VQ84VS1J0YU`. `oscar@oscarsarquis.com.br` é só destinatário do teste `ses-identity-test-17b`, não destinatário padrão nem cópia de pedido.

Não há MX na zona: `loja@` ainda não recebe respostas. Não configurar Reply-To nem encaminhamento automático para o endereço pessoal de teste. Caixa postal ou encaminhamento fica para decisão posterior do proprietário.

`order_submitted` fala da **data solicitada** (ainda não reservada). `order_accepted` fala da **data confirmada**. Mensagens `skipped` antigas **não** são reenviadas em massa; o worker só processa `pending`/`failed`.

Aceitação pelo SES devolve `MessageId` (`provider_message_id`). Isso não prova entrega na caixa nem abertura da mensagem.

## HTTPS de homologação (Mercado Pago → Hub)

Existente e **produção**, mesmo IP: `https://api.actionhub.com.br/health`, `https://actionhub.com.br/webhooks/mercadopago`. Não há hostname de homologação do Hub. Não apontar o webhook de teste do Hub local para essa URL, nem o DNS de `lojadepaes.com.br` para localhost.

Plano concreto **antes** de criar recurso pago ou alterar DNS: registro `homolog.actionhub.com.br` na zona Route 53 já existente de `actionhub.com.br`, certificado HTTPS, processo Hub separado, webhook MP da aplicação **TEST** só nesse host; Loja de homologação com admin autenticado (nunca o modo local sem senha). Não alterar MX.

## Já implementado

- Pedido público `submitted` com total calculado no servidor, token opaco (`X-Order-Token`) e idempotência de envio.
- `payment_records` por tentativa (`pix`/`card`), referência Hub, QR persistido para recuperar a cobrança no recarregamento.
- Webhook S2S JWT em `POST /api/v1/webhooks/actionhub`. Evento duplicado não reaplica. Valor aprovado diferente do esperado fica inconsistente, não pago.
- Reconciliação por `GET` no Hub (`/storefront/orders/{ref}/reconcile`) quando o webhook atrasa.
- Estorno satélite: o Hub **não** expõe API de refund neste ciclo. Pedido pago e não atendido é procedimento no painel Mercado Pago.

Não armazenar cartão, CVV, tokens de acesso do MP nem payload completo indiscriminado.
