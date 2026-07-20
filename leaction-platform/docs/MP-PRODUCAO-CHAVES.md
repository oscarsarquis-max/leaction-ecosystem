# Mercado Pago — o que você precisa para produção (Action Hub)

Antes do cutover de pagamento real (inove4us ↔ Action Hub), tenha em mãos:

## 1. Credenciais de produção (obrigatório)

Painel: https://www.mercadopago.com.br/developers/panel/app  
Aplicação → **Credenciais de produção** (não as de teste).

| Variável | Onde | Formato |
|----------|------|---------|
| `MP_ACCESS_TOKEN` | `leaction-platform/.env` (gateway) | `APP_USR-…` |
| `MP_PUBLIC_KEY` | mesmo `.env` | `APP_USR-…` |
| `NEXT_PUBLIC_MP_PUBLIC_KEY` | FE / `.env.production` do action-hub | **igual** à Public Key |

Sem essas três (Access + Public no gateway e Public no Next), o deploy remoto (`setup-env-remote.ps1`) **recusa** gravar TEST.

## 2. Webhook no painel MP (obrigatório para pending → approved)

URL de notificação (produção):

```text
https://actionhub.com.br/webhooks/mercadopago
```

Eventos: pagamentos (`payment`).  
Sem isso, cobranças que ficam “em análise” não liberam créditos até alguém consultar a API.

## 3. Segredos Hub (já no cutover)

| Variável | Nota |
|----------|------|
| `JWT_SECRET` | Forte; alinhado ao que as apps usam se houver JWT legado |
| `APP_WEBHOOK_URL_INOVE4US` | `https://inove4us.com.br/api/webhooks/actionhub` |
| Secret do `app_registry` inove4us | Igual a `ACTIONHUB_WEBHOOK_SECRET` no inove4us |

## 4. O que **não** vai para produção

- Chaves `TEST-…`
- `ALLOW_PAYMENT_SIMULATION=1` (simular pagamento fica off com `NODE_ENV=production`)
- CPF sandbox `12345678909` (só com token TEST)

## 5. Como entregar as chaves neste fluxo

1. Coloque `APP_USR-…` no `.env` **local** do Hub (não commitar).
2. Avise que as chaves estão no `.env` — o agente/deploy usa `setup-env-remote.ps1` sem colar segredo no chat.
3. Ou cole aqui só o **prefixo** (`APP_USR-xxxx…` primeiros 12 chars) para confirmar o par; o valor completo fica só no `.env`/EC2.

## 6. Smoke após gravar

1. `GET https://actionhub.com.br` / health do gateway com `NODE_ENV=production`
2. `GET /config/payments` → `sandbox_mode: false`, `allow_payment_simulation: false`
3. Compra mínima no inove4us → PAID → outbox delivered → saldo sobe
