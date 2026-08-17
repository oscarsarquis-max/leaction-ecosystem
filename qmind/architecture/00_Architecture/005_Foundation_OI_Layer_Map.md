# Mapa de camadas — Foundation e Organization Intelligence

- Status: **Aprovado**
- Data: 2026-08-17
- ADR: [`../05_ADR/ADR-012-foundation-and-organization-intelligence.md`](../05_ADR/ADR-012-foundation-and-organization-intelligence.md)

## Visão

```text
┌─────────────────────────────────────────────────────────────┐
│                     Experiência (Web)                         │
│   Shell · Tour · Plan · Field · Map · Actions · Assistant   │
└────────────────────────────┬────────────────────────────────┘
                             │
         ┌───────────────────┴───────────────────┐
         ▼                                       ▼
┌─────────────────────┐               ┌─────────────────────┐
│   FOUNDATION v1.0   │               │   OI Alpha (visão)  │
│   Operação          │◄── insights ──│   Compreensão       │
│                     │─── APIs ─────►│   Inteligência      │
└──────────┬──────────┘               └──────────┬──────────┘
           │                                     │
           ▼                                     ▼
   PostgreSQL + RLS                      Artefatos OI
   (tenant = organization)               (futuro, org-scoped)
```

## Regra de dependência

```text
Foundation
    ↓  (APIs / eventos / master data)
   OI
    ↓  (insights, scores, recomendações)
 Insights
    ↓  (comandos sugeridos / escrita controlada)
Foundation
```

- **Foundation → OI:** a OI conhece contratos públicos da Foundation.
- **OI → Foundation:** apenas via APIs/comandos estáveis; sem acesso privilegiado a engines internos.
- **Foundation ↛ OI:** nenhum import, feature flag obrigatória ou acoplamento de schema OI dentro de módulos Foundation.

## Fronteiras de dados

| Dado | Dono | Consumidor típico |
|------|------|-------------------|
| Memberships, OrgContext | Foundation | OI (leitura autorizada) |
| Organization Profile | Foundation | OI + jornada |
| Guided session JSONB | Foundation (sessão) | Bridge futura OI/Foundation |
| Evidence / Findings | Foundation | OI (agregados/insights) |
| Fit / Pain / Journey scores | OI (futuro) | Tour, Map, Assistant (leitura) |

## Isolamento

OI **herda** o isolamento da Foundation. Não há segundo mecanismo de tenant. Toda leitura/escrita OI futura deve usar o mesmo `OrgContext` + RLS.

## Relação com ADR-008

A camada de IA generativa (ADR-008), quando usada pela OI, permanece subordinada à governança já aceita: sugestão, revisão humana, proveniência, sem bypass de autorização.
