# Prompt 1 — database-core

Configura Postgres + Prisma na raiz `leaction-ecosystem/leactiona` (monorepo; não `C:\Projetos\leactiona`).

## Como subir

```powershell
cd C:\Projetos\leaction-ecosystem\leactiona
docker compose -f database/docker-compose.yml up -d

# .env a partir do example + chave PII
copy .env.example .env
# gerar chave: node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"

npm install
npx prisma migrate deploy
npx prisma generate
npm run test:db
```

## Artefatos

- `prisma/schema.prisma` — Organization(global), User (PII enc), Course, Module, Lesson, Enrollment, GamificationProfile, Badge, UserBadge
- `backend/src/lib/crypto.ts` — AES-256-GCM + emailHash HMAC
- `backend/src/lib/prisma.ts` — cliente Fastify
- `tests/database-core.test.ts`
