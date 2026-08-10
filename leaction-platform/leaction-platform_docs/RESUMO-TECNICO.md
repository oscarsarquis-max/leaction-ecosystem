# Action Hub — Resumo técnico

> Escopo: `leaction-platform` (Action Hub / MudaEdu B2B)  
> Atualizado: 2026-07-25

## Propósito

O Action Hub é o **hub comercial e operacional** do ecossistema LeAction: portal B2B, catálogo/planos white-label, checkout (Mercado Pago), contratos/entitlements, CMS headless, CRM de tracking (Action-Sponge) e curadoria de marketplace.

Ele **orquestra** apps satélite (ex.: inove4us) via `app_registry` + secrets + webhooks — **sem embutir** o código das demandantes.

- Superfície pública: ActionHub / MudaEdu  
- Produção (referência): `actionhub.com.br`  
- Versão baseline: `1.0.0` (2026-07-20)

---

## Stack e serviços locais

| Camada | Tecnologia | Porta |
|--------|------------|-------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind 4 | `:4000` |
| Gateway API | Node/Express 5, `pg`, JWT, S3 (CMS), Mercado Pago | `:4001` |
| Marketplace | Flask 3 + SQLAlchemy | `:4012` |
| Banco | Postgres (`leaction_hub` no container `leaction_db`) | `:5434` → `5432` |

Ordem de subida (`scripts/dev/start-hub.ps1`):

1. Postgres  
2. Gateway `:4001`  
3. Marketplace `:4012`  
4. Next `:4000`

Scripts locais:

- `scripts/dev/start-hub.ps1`
- `scripts/dev/status-hub.ps1`
- `scripts/dev/stop-hub.ps1`
- Logs: `leaction-platform/.dev-logs/`

---

## Funcionalidades principais

### Auth / usuários
- Login/registro Hub, JWT (`JWT_SECRET`), perfil e pedidos.

### Pagamentos / checkout
- Mercado Pago: Brick/cartão, assinaturas, webhooks.
- S2S: `POST /v1/checkout/sessions` (Bearer / secret do app).
- Catálogo público: `GET /v1/catalog/:app_id`, `POST /v1/checkout/catalog`.
- FE: `/checkout/inove4us`, `/checkout/paneldx`, `/checkout/direct`.
- Fulfillment: marca PAID → contrato/entitlement → outbox (+ webhook JWT legado quando aplicável).

### Contratos & entitlements
- Tabelas: `app_registry`, `contracts`, `contract_items`, `entitlement_snapshots`, `webhook_outbox`, `catalog_plans`.
- `GET /v1/entitlements?app_id=&subject_id=` (Bearer / `X-App-Secret`).
- Outbox worker (~5s): JWT `iss=leaction-hub` → `webhook_url` do satélite.

### Admin
- Apps, planos, créditos, pagamentos (`/dashboard/admin/*`).

### CMS (headless + site)
- Posts: `/api/cms/posts` (público + admin).
- Site config: `/api/public/cms`, `/api/admin/cms` (`config_key=default|inove4us`).
- Upload: `/admin/cms/upload` (S3/local).
- **Persistência:** Postgres operacional + snapshot S3 `/{prefix}/site/{config_key}.json` quando `CMS_S3_BUCKET` está definido. PUT admin grava DB+S3; no boot o gateway reidrata do S3. Deploy de app **não** apaga o S3.
- Bootstrap one-shot: `node scripts/push-cms-site-to-s3.js [--key=inove4us]`
- UI: `/dashboard/cms/*`.

### CRM (Action-Sponge)
- Ingest: `POST /api/crm/tracking/receber` (`x-crm-secret` / `CRM_TRACKING_SECRET`).
- Funil: `/api/crm/dashboard/funil-freemium`.
- UI: `/dashboard/crm/tracking`.

### Marketplace / curadoria
- Ofertas (Mercado Livre / Amazon opcional), regras de curadoria.
- UI: `/dashboard/marketplace/curadoria`.

### PanelDX (legado / parcialmente desligado)
- Checkout e vitrine ainda existem no código.
- Link público no Hub: **desligado** (`PANEL_DX_HUB_LINKED = false`).
- CMS da home pública do PanelDX passou a consumir o Hub.

### Gatekeeper / monitoramento
- `system_config.system_locked` + rotas `/gatekeeper/*`.
- Monitor UI: `/dashboard/monitor` → `GET /api/sys/status` (JWT admin). Sessão 401 **não** pinta serviços como DOWN.
- Alertas prod: Gateway `lib/status-watcher.js` (SES) → `suporte@leaction.com.br` em transição DOWN/UP. Env: `STATUS_ALERT_*` em `.env.production.example`.

---

## Integração com satélites (padrão)

1. Registrar app em `app_registry` (`app_id`, `webhook_secret`, `webhook_url`, return origins).  
2. Chamadas S2S com o secret (checkout, entitlements; opcional CRM/CMS).  
3. Pagamento confirmado → contrato/entitlement → **outbox** entrega JWT no webhook do app.

### inove4us (ativo)
| Concern | Mecanismo |
|---------|-----------|
| Identity | `app_id=inove4us` |
| Secret | `ACTION_HUB_APP_SECRET` / `ACTIONHUB_WEBHOOK_SECRET` ↔ `webhook_secret` |
| Hub API | `ACTION_HUB_API_URL` → `:4001` |
| Checkout | S2S + browser `/checkout/inove4us` |
| Webhooks | Outbox → `/api/webhooks/actionhub` |
| CRM / CMS | Tracking + posts do Hub |

Documentação detalhada do lado demandante:  
`inove4us/inove4us_docs/INTEGRACAO-ACTION-HUB.md`

---

## Mapa do repositório

```
leaction-platform/
├── docker-compose.yml              # leaction_db :5434
├── .env                            # DATABASE_URL, JWT, MP, secrets
├── ecosystem.config.js             # PM2 prod
├── scripts/dev/                    # start/status/stop locais
├── shared/database/                # schema + patches
├── services/gateway-api/           # Express :4001
│   ├── server.js
│   ├── mercadopago.js, payment-fulfillment.js, hub-auth.js, crm-tracking.js
│   ├── admin/
│   └── domain/                     # entitlements, checkout, CMS, outbox, gatekeeper
├── backend/                        # Flask marketplace :4012
└── frontend/action-hub/            # Next :4000
    ├── src/app/page.tsx
    ├── src/app/dashboard/**
    ├── src/app/checkout/**
    └── src/app/api/**
```

### Healthchecks locais

| Serviço | URL |
|---------|-----|
| FE | `http://127.0.0.1:4000/api/health` |
| Gateway | `http://127.0.0.1:4001/health` |
| Marketplace | `http://127.0.0.1:4012/api/marketplace/health` |
