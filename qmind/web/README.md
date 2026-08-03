# @qmind/web

React shell for QMind (Vite + React + TypeScript + Tailwind).

## Scripts

```bash
# from qmind/
npm run dev:web
npm run test:web
npm run build:web
```

## Environment

Copy `.env.example` → `.env.local`.

| Variable | Notes |
|----------|--------|
| `VITE_ENVIRONMENT` | `local` \| `dev` \| `prod` |
| `VITE_AUTH_MODE` | `cognito` \| `dev` — **dev forbidden when prod** |
| `VITE_API_BASE_URL` | Empty = same-origin (Vite proxy → `:8008`) |
| Cognito / `VITE_DEV_*` | See `.env.example` |

## Tenant isolation gate

On organization switch the shell:

1. Aborts in-flight requests
2. Calls `invalidateTenant()` on `createQmindClient`
3. Clears org-scoped React Query caches (`["org", organizationId, …]`)
4. Bumps request generation so late responses are ignored
5. Refetches memberships + assessments

Local persistence stores only a preferred organization UUID in `sessionStorage` — never tokens or tenant payloads.
