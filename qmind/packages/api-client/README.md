# `@qmind/api-client`

TypeScript client generated from the frozen OpenAPI contract (`openapi-v1-initial`).

## Rules

- **Source of truth:** `qmind/backend/openapi/openapi.json` (never a live server)
- **Do not edit** `src/generated/**`
- Regenerate only via the monorepo command
- Hand-written surface: `createQmindClient` (token, tenant, `QmindApiError`)

## Generate (single command)

From `qmind/`:

```powershell
npm run generate:api-client
```

Or:

```powershell
.\scripts\generate-api-client.ps1
```

## Drift check

```powershell
npm run check:api-client
```

CI runs the same check when OpenAPI or this package changes.

## Usage

```ts
import { createQmindClient, QmindApiError } from "@qmind/api-client";

let organizationId: string | null = null;

const client = createQmindClient({
  baseUrl: "http://localhost:8008",
  getAccessToken: () => sessionStorage.getItem("access_token"),
  getOrganizationId: () => organizationId,
});

// switch tenant
organizationId = nextOrgId;
client.invalidateTenant(); // apps must drop org-scoped caches/queries

try {
  const { data } = await client.api.listAssessments();
} catch (e) {
  if (e instanceof QmindApiError) {
    console.error(e.code, e.correlationId, e.fieldErrors);
  }
}
```
