# Integração com Action Hub

O **inove4us** é demandante do Action Hub (`app_id: inove4us`).  
O secret compartilhado é `app_registry.webhook_secret`, localmente `ACTIONHUB_WEBHOOK_SECRET` (ou `ACTION_HUB_APP_SECRET`).

Documento irmão no Hub:  
`leaction-platform/leaction-platform_docs/RESUMO-TECNICO.md`

---

## Identidade

| Campo | Valor |
|-------|--------|
| `app_id` | `inove4us` |
| Subject de cobrança | e-mail do usuário (`subject_id` / `mail_clie`) |
| Secret S2S | `ACTIONHUB_WEBHOOK_SECRET` = Hub `webhook_secret` |

---

## URLs

| Papel | Local | Produção |
|-------|--------|----------|
| Hub API | `http://localhost:4001` | `https://actionhub.com.br/hub-api` |
| Hub público (browser) | `http://localhost:4000` | `https://actionhub.com.br` |
| App (return/CORS) | `http://localhost:5174` | `https://inove4us.com.br` |
| Webhook inbound | `POST /api/webhooks/actionhub` | idem no host do app |

---

## inove4us → Hub

1. **Checkout S2S:** `POST /v1/checkout/sessions` (Bearer secret)  
   Body: `app_id`, `subject_id`, `sku`, `return_origin`,  
   `return_to=/mesa-do-inovador?paid=1`, `hub_public_url`.

2. **Vitrine (browser):** `{HUB_PUBLIC}/checkout/inove4us?email=&return_origin=&return_to=…`  
   via `GET /api/billing/plans-url` (fluxo principal do modal Upgrade).

3. **CRM / Action-Sponge:** `POST /api/crm/tracking/receber` (header `x-crm-secret`)  
   via proxy `POST /api/tracking/enviar` (`sistema_origem: inove4us`).

4. **CMS:** `GET /api/cms/posts?sistema_destino=inove4us`  
   via `GET /api/noticias` (cache em memória; degradação silenciosa).

> Não há polling periódico de `GET /v1/entitlements` hoje. Créditos entram pelo webhook `CREDITS_GRANTED`.

---

## Hub → inove4us

- **Endpoint:** `POST /api/webhooks/actionhub` (sem sessão; isento do gatekeeper).
- **Auth:** JWT HS256 (`Authorization: Bearer`, `X-Hub-Signature` ou body `token`), assinado com o mesmo secret.
- **Eventos:**
  - `CREDITS_GRANTED` → soma créditos em `ctdi_clie.creditos_ia` (por e-mail).
  - `PAYMENT_NOTICE` → grava aviso em `hub_notices` (UI na Mesa).
  - `CONTRACT_ACTIVATED` → apenas log (entitlements persistidos: futuro).
- Resposta de negócio: HTTP **200** com `{ status: "received", … }` para não reenfileirar o outbox.

Implementação: `backend/webhook_routes.py`.

---

## Fluxo de checkout no browser

1. Usuário autenticado abre Upgrade → backend monta URL da vitrine Hub (`GET /api/billing/plans-url`).  
2. Pagamento no Hub (Brick white-label / catálogo).  
3. Retorno para `{FRONTEND_ORIGIN}/mesa-do-inovador?paid=1`.  
4. Frontend faz polling de `GET /api/auth/me` até o webhook refletir o novo saldo (ou timeout ~90s).

SKU: body `sku` ou alias `golive-50` remapeado por `ACTION_HUB_DEFAULT_SKU` quando configurado.

---

## Créditos (contrato de saldo)

- Freemium local: saldo em Postgres (`creditos_ia`, default 3).
- Débito: geração bem-sucedida no wizard (`POST /api/wizard/estruturar`).
- Crédito: somente via webhook Hub (`CREDITS_GRANTED`).
- Refresh UX:
  - `/api/auth/me` sempre recarrega saldo + notices;
  - polling ~20s com aba visível;
  - após `?paid=1`, polling ~1s até ~90s até o saldo subir.

---

## Variáveis de ambiente mínimas

```env
ACTION_HUB_APP_ID=inove4us
ACTION_HUB_APP_SECRET=<igual ao webhook_secret do Hub>
ACTIONHUB_WEBHOOK_SECRET=<igual ao webhook_secret do Hub>
ACTION_HUB_API_URL=http://localhost:4001
ACTION_HUB_PUBLIC_URL=http://localhost:4000
ACTION_HUB_CRM_TRACKING_URL=http://127.0.0.1:4001/api/crm/tracking/receber
CRM_TRACKING_SECRET=<igual CRM_TRACKING_SECRET do Hub>
ACTION_HUB_DEFAULT_SKU=<SKU real do catalog_plans se FE usar golive-50>
FRONTEND_ORIGIN=http://localhost:5174
CORS_ORIGINS=http://localhost:5174
```

Ver também `.env.example` na raiz do `inove4us`.
