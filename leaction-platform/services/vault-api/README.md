# vault-api

Cofre de credenciais de infraestrutura do ecossistema LeAction. Serviço **separado** do Action Hub (`gateway-api`) e da Gestão de Identidade: banco próprio, login próprio, JWT próprio.

Rotação: automática (webhook S2S do satélite) ou manual (revelação única + confirmar aplicação). Versões `revogado` permanecem no banco.

## Isolamento

- Banco Postgres **`leaction_vault`** na instância local `:5434` (mesmo container `leaction_db`, database distinto de `leaction_hub`).
- Só o processo `vault-api` deve usar `VAULT_DATABASE_URL` (role `vault_api`). Não apontar o gateway do Hub para este banco.
- `VAULT_MASTER_KEY` e `VAULT_JWT_SECRET` nunca vão para o banco nem para o repositório.
- Não entra no sync LAN padrão do ecossistema (segredos não devem viajar “no bolo”).

## Variáveis de ambiente

| Variável | Uso |
|----------|-----|
| `VAULT_DATABASE_URL` | Conexão do processo com `leaction_vault` |
| `VAULT_MASTER_KEY` | AES-256-GCM (32 bytes: hex de 64 chars ou base64) |
| `VAULT_JWT_SECRET` | Assinatura do JWT local (TTL 2h). Não usar `JWT_SECRET` do Hub |
| `VAULT_PORT` | HTTP, default **4020** |

Bootstrap (scripts, não o daemon):

| Variável | Uso |
|----------|-----|
| `VAULT_BOOTSTRAP_DATABASE_URL` | Superuser local só para criar DB/role |
| `VAULT_DB_PASSWORD` | Senha da role `vault_api` |
| `VAULT_BOOTSTRAP_EMAIL` / `VAULT_BOOTSTRAP_PASSWORD` | Primeiro admin (`seed-admin.js`) |

## Subir local

```powershell
cd leaction-platform\services\vault-api
copy .env.example .env
# preencha VAULT_MASTER_KEY (64 hex) e VAULT_JWT_SECRET
npm install
node scripts/apply-schema.js
node scripts/seed-admin.js
npm start
```

Health: `http://127.0.0.1:4020/health`

## Rotas

| Método | Caminho | Auth |
|--------|---------|------|
| GET | `/health` | pública |
| POST | `/api/auth/login` `{ email, senha }` | pública |
| GET/POST | `/api/sistemas` | JWT vault |
| GET | `/api/secrets?sistema=` | JWT vault (valor mascarado; audit `lido`) |
| POST | `/api/secrets` `{ sistema, tipo, valor }` | JWT vault (não ecoa o valor) |
| GET | `/api/secrets/:id/revelar` | JWT vault (texto plano pontual, `Cache-Control: no-store`, audit `lido`) |
| POST | `/api/secrets/:id/rotacionar` `{ novo_valor? }` | JWT vault — auto (S2S) ou manual (valor uma vez, `no-store`) |
| POST | `/api/secrets/:id/confirmar-aplicacao` | JWT vault — fecha rotação manual |
| GET | `/api/secrets/:id/historico` | JWT vault — versões (metadados, sem valor) |
