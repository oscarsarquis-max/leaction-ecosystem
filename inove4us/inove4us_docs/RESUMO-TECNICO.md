# inove4us — Resumo técnico

> Escopo: `inove4us`  
> Atualizado: 2026-07-25

## Propósito

App **freemium** (Top of Funnel) em **inove4us.com.br**: Mesa do Inovador para professores/professores.

- Autônomo: banco e deploy próprios.  
- **Não edita** PanelDX; cópia operacional da Oficina em `source-from-paneldx/` + `backend/paneldx_port/`.  
- Consome o Action Hub para checkout, créditos (webhook), CRM e CMS.  
- Ledger freemium local: `ctdi_clie.creditos_ia`.

Fluxo de valor: e-mail → créditos IA → wizard Desafio → Dia a Dia → Agenda/Kanban → upgrade de créditos via Hub.

Integração Hub (detalhe): [`INTEGRACAO-ACTION-HUB.md`](./INTEGRACAO-ACTION-HUB.md)

---

## Stack e serviços locais

| Camada | Tecnologia | Porta |
|--------|------------|-------|
| Frontend | React 18, Vite 6, React Router 6, Tailwind 3 | `:5174` |
| Backend | Flask 3, psycopg2, PyJWT, requests, boto3 (Bedrock/SES) | `:5011` (ambiente atual; default docs/example `:5010`) |
| DB | Postgres `inove4us` no `leaction_db` | `:5434` |
| Oficina legada | EJS sob `/inovador` | mesmo Flask |

**Regra local:** ao subir o inove4us, subir também o Action Hub e serviços atrelados (Postgres, Gateway `:4001`, Marketplace `:4012`, FE `:4000`).

---

## Funcionalidades principais

### Auth
- E-mail + código de acesso; cookie de sessão.
- `GET /api/auth/me` — créditos + `hub_notices`.
- FE: `/acesso` (`Acesso.jsx`, `lib/auth.jsx`).

### Mesa do Inovador
- Home: `/mesa-do-inovador` — agenda, mapa, badge de créditos, Upgrade.
- Oficina legada: `/inovador` (`paneldx_port/inovador_routes.py`).

### Wizard / Desafio (IA)
- `POST /api/wizard/estruturar`, `POST /api/wizard/selecionar-caminho`.
- Consome 1 `creditos_ia` em sucesso Bedrock (`INSUFFICIENT_CREDITS` → 403).
- FE: `/desafio`.

### Dia a Dia
- Aulas ~50 min, catálogo de dinâmicas, Kanban de ciclo.
- APIs: `/api/daily*`.
- FE: `/dia-a-dia`, `/dia-a-dia/nova`, `/dia-a-dia/:id`.
- Catálogo: `core/catalogo_metodologias_dia.py`.

### Agenda / Kanban / Execução
- `agenda_routes.py` — `/api/agenda-eventos*`.
- Retomada: `/execucao/:idEvento`.

### Billing / créditos
- Proxy Hub: `billing_routes.py` — `GET /api/billing/plans-url`, `POST /api/billing/checkout`.
- Retorno: `/pagamento/sucesso|pendente|erro` e `/mesa-do-inovador?paid=1`.

### Gatekeeper
- `gatekeeper_routes.py` — `/manutencao`, `/gatekeeper/*`.
- Isentos: `/api/webhooks/*`, `/api/tracking/*`, health.

### Tracking PLG
- `POST /api/tracking/enviar` → Hub Action-Sponge.
- FE: `lib/tracking.js`, `CrmPageTracker.jsx`.

### CMS / notícias
- `GET /api/noticias` ← Hub `GET /api/cms/posts` (cache em memória).

### Webhooks Hub
- `POST /api/webhooks/actionhub` — créditos + notices.

### Feedback / co-criação
- `POST /api/feedbacks`.

---

## Subida local (referência)

```powershell
# Preferido — sobe Hub + inove juntos
cd C:\Projetos\leaction-ecosystem\inove4us
.\scripts\dev\start-inove.ps1

# Equivalente manual:
# 1) Action Hub
cd C:\Projetos\leaction-ecosystem\leaction-platform
.\scripts\dev\start-hub.ps1

# 2) API inove4us
cd C:\Projetos\leaction-ecosystem\inove4us\backend
.\.venv\Scripts\Activate.ps1
# carregar .env da raiz inove4us
python app.py   # FLASK_PORT=5011 neste ambiente

# 3) FE
cd ..\frontend
npm run dev     # http://localhost:5174
```

| URL | Uso |
|-----|-----|
| http://localhost:5174/acesso | Login |
| http://localhost:5174/mesa-do-inovador | Mesa |
| http://127.0.0.1:5011/api/health | Health API |

> Atenção: `frontend/vite.config.js` pode proxyar para `:5011` enquanto `.env.example` cita `:5010` — alinhar porta e proxy.

---

## Mapa do repositório

```
inove4us/
├── README.md, CHANGELOG.md, VERSION
├── .env.example
├── backend/
│   ├── app.py
│   ├── db.py
│   ├── billing_routes.py
│   ├── webhook_routes.py
│   ├── tracking_routes.py
│   ├── cms_noticias_routes.py
│   ├── gatekeeper_routes.py
│   ├── wizard_routes.py
│   ├── agenda_routes.py
│   ├── routes/daily_routes.py
│   ├── paneldx_port/
│   ├── services/              # hub_cms_cache, methodology_service
│   └── core/                  # catalogo_metodologias_dia
├── frontend/                  # Vite React :5174
├── infra/                     # migrations, terraform, scripts
├── source-from-paneldx/       # cópia operacional (não editar PanelDX)
└── inove4us_docs/             # documentação deste projeto
```
