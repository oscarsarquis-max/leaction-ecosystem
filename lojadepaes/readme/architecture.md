# Arquitetura — Loja de Pães

Aplicação independente no monorepo `C:\Projetos`. Não compartilha processo, banco nem deploy com Action Hub, Inove, School ou Panne.

## Superfícies

```
browser  :5175  →  frontend (Vite + React)
               ↘  /api/v1/*  →  backend FastAPI :5075
                                      ↘  PostgreSQL :5438 (SQLAlchemy 2, Alembic)
```

A vitrine consome `/api/v1/catalog` para os pães padrão e `/api/v1/schedule` para o calendário de fornadas. O assistente de criação continua demonstrativo. A gestão (`/admin/pedidos`, `/admin/produtos` e `/admin/agenda`) usa cookie de sessão e `/api/v1/admin`.

## Frontend

- `src/app` — vitrine (`App`), detalhe `/paes/:slug` e `Root` (`/admin` → gestão)
- `src/admin` — login, pedidos e editor de produtos
- `src/shop` — catálogo público, detalhe e seleção local (sem checkout)
- `src/components` — logo, cabeçalho, rodapé, cartão de opção, layout da loja
- `src/features/bread-builder` — assistente (estado local, dados demonstrativos)
- `src/features/inspiration` — mural
- `src/features/baker-library` — artigos em `<dialog>`
- `src/services` — cliente HTTP da vitrine
- `src/styles/global.css` — identidade do protótipo
- `src/styles/responsive.css` — layout fluido permanente (a partir de 320 px, zoom 200%, sem rolagem horizontal da página)
- `images/` — logo oficial `images/lojadepaeslogo.png` e fotos editoriais `internal*`

Fotos de produto cadastradas pelo admin **não** substituem o mapeamento editorial de `internal*`. A vitrine não ganha atalho de admin (ocultar link não é autorização).

## Backend

- FastAPI `create_app()`, prefixo `/api/v1`
- `LOJADEPAES_*` via Pydantic Settings
- CORS com origens explícitas e credenciais
- SQLAlchemy 2 síncrono + `psycopg`
- `get_db()`: commit se a rota concluir; sempre fecha a sessão
- Modelos em `app/models/` (inclui `admin_sessions` e `admin_login_attempts`)
- Transições em `app.domain.orders` (as mesmas do painel)
- Admin: uma credencial no servidor, sessão no Postgres, CSRF, limite de tentativas
- Seed `python -m app.seed`; pedidos demo `python -m app.seed.demo_orders`
- `GET /health` e `GET /ready` inalterados

### Endpoints `/api/v1/admin`

| Método | Caminho | Uso |
|---|---|---|
| POST | `/login` | cria sessão |
| GET | `/session` | restaura sessão e rotaciona CSRF |
| POST | `/logout` | revoga sessão |
| GET | `/orders` | lista paginada e filtros |
| GET | `/orders/{id}` | detalhe |
| POST | `/orders/{id}/confirm` | confirmar |
| POST | `/orders/{id}/start-production` | iniciar produção |
| POST | `/orders/{id}/mark-ready` | marcar pronto |
| POST | `/orders/{id}/complete` | concluir |
| POST | `/orders/{id}/cancel` | cancelar (motivo) |
| POST | `/orders/{id}/notes` | nota interna |
| GET | `/products` | lista de produtos |
| POST | `/products` | criar rascunho |
| GET | `/products/{id}` | editar |
| PUT | `/products/{id}` | salvar |
| POST | `/products/{id}/image` | foto destacada |
| POST | `/products/{id}/publish` | publicar |
| POST | `/products/{id}/unpublish` | voltar a rascunho |
| POST | `/products/{id}/archive` | arquivar |
| DELETE | `/products/{id}` | apagar rascunho ou arquivado |
| POST | `/products/{id}/availability` | disponibilidade |
| GET | `/media/{id}` | servir foto (admin) |

### Catálogo público `/api/v1/catalog`

| Método | Caminho | Uso |
|---|---|---|
| GET | `/products` | vitrine paginada (`Cache-Control: no-store`) |
| GET | `/products/{slug}` | detalhe público |
| GET | `/media/{id}` | foto se o produto estiver publicado |

Rascunhos e arquivados não saem nestas rotas, nem por UUID. Sem credencial configurada: **503** só no admin.

Implantação futura: HTTPS, `LOJADEPAES_COOKIE_SECURE=true`, segredos fora do repositório, origem CORS restrita ao domínio da gestão.

## Banco

PostgreSQL 16 (`database/docker-compose.yml`), porta **5438**. Migrações: `0001_baseline`, `28420c077dcd`, `b4e8d2a91c70`, `c8f3a1b27d09`. Sem `create_all()`. Testes em `lojadepaes_test`. Fotos em `var/media/` (persistente, backup necessário).

## `services/`

Reserva para workers e integrações.

## Fora de escopo nesta etapa

Processador de pagamentos, webhook ActionHub, checkout na vitrine, contas de cliente, receitas (Panne), DNS, publicação. A seleção de pães padrão no navegador não cria pedido.
