# QMind Foundation — Baseline v1.0

- Status: **Aprovado**
- Data: 2026-08-17
- Marco: ARCH-001
- ADR: [`../05_ADR/ADR-012-foundation-and-organization-intelligence.md`](../05_ADR/ADR-012-foundation-and-organization-intelligence.md)
- Código de referência: monorepo `qmind/` após commit Organization Profile (ICP-01)

## Propósito

Registrar oficialmente a **primeira geração operacional** do QMind — a Foundation — como baseline permanente sobre a qual a linha **Organization Intelligence (OI)** será construída.

A Foundation **não será descartada**. Toda inteligência futura deve consumi-la, não substituí-la.

## Versão

| Artefato | Versão | Nota |
|----------|--------|------|
| Foundation (documental + superfície operacional) | **v1.0** | Baseline ARCH-001 |
| Tag histórica relacionada | `mvp-fullstack-v0` (+ incrementos ICP-01) | Recuperável; OI não altera o número de versão executável neste marco |
| Organization Intelligence | **OI Alpha** (visão) | Sem módulo de negócio implementado neste ADR |

## O que é a Foundation

Camada responsável por **operar** a plataforma: autenticar, isolar tenants, conduzir a jornada de diagnóstico/auditoria, persistir evidências e planos, e expor contratos estáveis.

## Módulos da Foundation v1.0

| Módulo | Responsabilidade resumida | Âncoras no código / docs |
|--------|---------------------------|---------------------------|
| Authentication | Cognito OIDC / auth dev; Principal | `backend/app/auth/` |
| Organizations | Criação e leitura da org corrente | `modules/orgs/` |
| Memberships | Vínculo user↔org + papéis | `memberships` + `OrgContext` |
| Tenant isolation | Header `X-Organization-Id`, RLS FORCE | ADR-002, `db.tenant_connection` |
| Organization Profile | Master data 1:1 org-scoped | ICP-01, `/organizations/current/profile` |
| Guided Tour / Guided Assessment | Wizard e contexto de sessão | `modules/guided/`, FE guided |
| Audit Plan | Plano e agenda da auditoria | `modules/audit_plan/` |
| Field Central | Hub de campo `/work` | FE field + assessment work |
| Evolution Map | Sugestões determinísticas + review | `modules/evolution_map/` |
| Action Items | Planos de ação e itens | `modules/actions/` |
| Evidence / Findings / Maturity | Domínio de avaliação | módulos respectivos |
| Reports / PDF | Pacotes e exportação | `modules/reports/`, jobs |
| Assistant | Assistente contextual determinístico | FE `assistant/` |
| Agenda | Calendário org-scoped | `modules/agenda/` |
| OpenAPI + api-client | Contrato e SDK | `openapi/`, `packages/api-client` |

> Organization Profile faz parte da Foundation (master data operacional). Extensões analíticas (Pain, Fit, Journey recommendation) pertencem à **OI**, não a esta baseline.

## Invariantes da Foundation

1. Tenant = `Organization.id`; org ativa nunca vem do body como fonte de verdade.
2. Membership ativa é pré-requisito de `OrgContext`.
3. FORCE RLS em tabelas org-scoped; role `qmind_app` + GUC `app.organization_id`.
4. Guided `context` JSONB permanece dado de sessão/assessment até bridge explícita.
5. Maturity / Evolution Map / Assistant atuais são capacidades Foundation; OI não as reescreve nesta fase.
6. A Foundation deve permanecer utilizável **sem** a OI instalada.

## Relação com a OI

```text
Foundation (v1.0)  ──consome──►  OI (Alpha)
                      ▲
                      │ insights / sugestões (futuro)
                      └──────────┘
```

Detalhes: [`005_Foundation_OI_Layer_Map.md`](005_Foundation_OI_Layer_Map.md).

## O que este baseline NÃO inclui

- Operational Profile / Pain Profile / Fit Assessment (OI)
- Motores generativos de recomendação de jornada
- Onboarding ICP completo
- Dependência de implementação OI em qualquer módulo Foundation

## Critério de mudança de versão Foundation

- **v1.x**: evolução compatível (campos/API aditivos, bridges, hardening).
- **v2.0 Foundation** (se houver): somente com ADR explícito e plano de migração — distinto de “OI v2 Vision”, que é a linha de inteligência, não a substituição da operação.
