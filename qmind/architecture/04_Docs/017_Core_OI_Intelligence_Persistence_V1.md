# 017 — Core OI Intelligence Persistence V1

- Status: Approved
- Date: 2026-08-17
- Sprint: **OI-010** (Core side)

## Objetivo

Persistir no QMind Core o envelope `OrganizationalInsights` recebido do QMind OI após uma análise bem-sucedida, com histórico consultável por organização.

## Ownership

| Responsabilidade | Dono |
|------------------|------|
| Produzir insights | QMind OI (HTTP) |
| Persistir envelope bruto | QMind Core |
| Interpretar / priorizar / extrair cláusulas | **Não nesta Sprint** (Core não interpreta) |

## Modelo

Tabela `organization_intelligence_runs` (uma linha = uma execução bem-sucedida):

| Campo | Papel |
|-------|--------|
| `id` | PK |
| `organization_id` | Tenant (FK → `organizations`) |
| `schema_version` | Eco do envelope |
| `request_id` / `correlation_id` | Rastreabilidade |
| `generated_at` | Eco do envelope OI |
| `insights` | **JSONB** — envelope `OrganizationalInsights` completo |
| `created_at` | Instantâneo de persistência no Core |

## Estratégia JSONB

A coluna `insights` guarda o envelope wire **inteiro** (não só o array `insights[]`), sem decomposição relacional. O Core não extrai confidence, prioridade, cláusula ou supporting facts para colunas próprias.

## Fluxo

```text
POST .../intelligence/analyze
  OrgContext → Profile → OrganizationContextInput
       → OI HTTP → OrganizationalInsights
       → INSERT organization_intelligence_runs
       → return OrganizationalInsights
```

Persistência **somente** após resposta OI válida. Timeout / rede / HTTP error / JSON inválido → **zero** rows.

## Tenancy

Padrão Core: `tenant_connection`, ENABLE+FORCE RLS, policy `organization_id = qmind_app.current_organization_id()`, grants a `qmind_app`. `organization_id` do INSERT vem do `OrgContext`, não do body.

## Endpoints

- `POST /api/v1/organizations/current/intelligence/analyze` — analisa + persiste
- `GET /api/v1/organizations/current/intelligence/runs` — histórico (mais recente primeiro, `limit` padrão do Core)
- `GET /api/v1/organizations/current/intelligence/runs/{run_id}` — detalhe

## Autorização

Mesma política de leitura do profile / analyze OI-009 (sem roles novas).

## Limitações

- Sem UI, dashboard, analytics, filtros, paginação por cursor.
- Sem UNIQUE em `request_id` (sem idempotência nova).
- Sem tabelas normalizadas por insight.
- Sem alteração no `qmind-oi`.

## Dívida técnica (não resolvida)

**TD — Contract Drift Core ↔ OI:** DTOs wire no Core espelham OI-001; falta validação automatizada de compatibilidade entre repositórios.
