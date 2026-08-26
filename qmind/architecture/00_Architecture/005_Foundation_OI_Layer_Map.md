# Mapa de camadas — Foundation e Organization Intelligence

- Status: **Aprovado**
- Data: 2026-08-17
- ADR: [`../05_ADR/ADR-012-foundation-and-organization-intelligence.md`](../05_ADR/ADR-012-foundation-and-organization-intelligence.md)

## Visão

```text
┌─────────────────────────────────────────────────────────────┐
│                     Experiência (Web)                         │
│   Shell · Tour · Plan · Field · Map · Execução · Cockpit · Actions · Assistant   │
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
- **OI → Foundation:** insights e recomendações; escrita operacional só via comandos humanos na Foundation.
- **ISOI-007 (2026-08-24):** workspace de execução (board/sprints/squads) é **somente Foundation/Core**; fatos de execução (check-ins, impedimentos, métricas de sprint) serão insumos futuros para Execution Intelligence no OI (ISOI-009), sem contrato OI alterado neste marco.
- **ISOI-008 (2026-08-24):** evidência contextual e medição do resultado (planos, indicadores versionados, leituras append-only, posturas) são fatos Foundation/Core. A avaliação de meta é determinística e local.
- **ISOI-009 (2026-08-26):** o Core publica um snapshot factual V1 para o mecanismo OI `execution-intelligence-rules-v1`; valida a resposta e guarda histórico append-only. O OI interpreta, mas não escreve dados operacionais. Meta atingida permanece insumo da decisão humana de eficácia, nunca sua substituta.
- **ISOI-010 (2026-08-26):** Cockpit organizacional Core-only (`9d17fee`); consolidação de fatos/freshness/fila sem fan-out OI; OI permanece em `34ead2e`.
- **ISOI-011 (2026-08-26):** Hotpage pública e apresentação guiada V2 narram o ciclo até EI/Cockpit; `/` estática sem dados tenant; `/guided-tour` GET-only sobre dados autorizados; OI sem alteração funcional.
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
