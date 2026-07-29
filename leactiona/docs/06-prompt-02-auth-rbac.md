# Prompt 2 — auth-rbac

## Endpoints

- `POST /api/v1/auth/login` — JWT RS256 (15 min) + refresh; exige `code_challenge` S256 + header `DPoP`
- `POST /api/v1/auth/token` — refresh com `code_verifier` + DPoP
- `GET /api/v1/admin/ping` — somente `ADMIN` (RBAC)

## Segurança

- AES-256-GCM PII (já em `lib/crypto.ts`)
- bcrypt (custo 12) + política mín. 12 chars + dicionário comum
- DPoP (jkt no access token) · PKCE no login/refresh
- Helmet + rate-limit (auth mais restrito)
