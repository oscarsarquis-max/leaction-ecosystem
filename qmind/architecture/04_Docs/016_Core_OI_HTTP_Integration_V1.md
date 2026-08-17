# 016 — Core → OI HTTP Integration V1

- Status: Approved
- Date: 2026-08-17
- Sprint: **OI-009** (Core side)

## Objetivo

Conectar QMind Core ao QMind OI exclusivamente via HTTP JSON, usando o contrato Boundary v1 e a API OI-008.

## Fronteira

```text
QMind Core
    |  OrganizationContextInput v1 (JSON)
    v
POST {QMIND_OI_BASE_URL}/api/v1/organizational-intelligence/analyze
    |  OrganizationalInsights v1 (JSON)
    v
QMind Core
```

Proibido: import Python de `qmind_oi`, models compartilhados, acesso a banco entre projetos.

## Endpoint Core

`POST /api/v1/organizations/current/intelligence/analyze`

1. `OrgContextDep` (membership + `X-Organization-Id`)
2. Lê Organization Profile (`get_or_create_organization_profile`)
3. Monta `OrganizationContextInput`
4. Cliente HTTP → OI
5. Devolve `OrganizationalInsights` (sem persistir)

## Autorização (decisão)

Reutiliza a **mesma política de leitura** do `GET /organizations/current/profile`:

`org_admin`, `consultant_auditor`, `quality_manager`, `process_owner`, `reader`, `action_owner`, `platform_admin`

Justificativa: análise da organização corrente é operação de leitura/interpretação sobre o profile já autorizado a esses papéis. Sem roles novas, sem mudança em Cognito/memberships.

## Tenancy

- `core_organization_id` = `ctx.organization_id` (OrgContext)
- Nunca aceito do body/frontend como tenant
- `tenant_connection` / RLS inalterados; OI não acessa Postgres do Core

## Configuração

| Env | Settings field | Papel |
|-----|----------------|--------|
| `QMIND_OI_BASE_URL` | `qmind_oi_base_url` | Base URL OI (sem hardcode de localhost no código) |
| `QMIND_OI_TIMEOUT_SECONDS` | `qmind_oi_timeout_seconds` | Timeout HTTP (default 30s) |

## Falhas OI

| Situação | Código AppError | HTTP |
|----------|-----------------|------|
| Base URL vazia | `oi_not_configured` | 503 |
| Timeout | `oi_timeout` | 504 |
| Rede / HTTP error | `oi_unavailable` | 502 |
| OI 4xx/5xx ou JSON inválido | `oi_bad_response` / `oi_error` / `oi_invalid_response` | 502 |

Sem retry, circuit breaker ou fallback inteligente. Sem escrita de insights.

## Mapeamento Profile → Input

Copia campos factuais do `OrganizationProfileOut` para `OrganizationProfileFacts`. Não busca assessments/findings. `context.organization` permanece `null` nesta Sprint (evita ler `organizations.name` como fonte extra).
