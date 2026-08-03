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

## Assessment setup (this slice)

- Create draft (`POST /assessments`) using the **active** org header — never `organization_id` in the body
- Detail: scope/team editable only in `draft` and only for mutate roles (`org_admin`, `consultant_auditor`, `quality_manager`)
- Readers see the resource without mutation controls
- `plan` requires confirmation (locks scope/team); no optimistic cache write; success invalidates org-scoped caches
- API errors show `code`, `message`, and `correlation_id`

## Assessments (MVP)

- `/assessments` — list for the selected organization
- `/assessments/new` — create draft (catalog UUIDs; optional env defaults)
- `/assessments/:id` — manage scope/team while `draft`, then `plan` → `planned`

Optional defaults in `.env.local`:

```
VITE_DEFAULT_ASSESSMENT_MODEL_ID=
VITE_DEFAULT_STANDARD_VERSION_ID=
VITE_DEFAULT_REQUIREMENT_ID=
```

