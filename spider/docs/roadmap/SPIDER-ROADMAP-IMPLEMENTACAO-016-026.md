# SPIDER Roadmap de Implementação — Prompts 016–026

| Campo | Valor |
|-------|--------|
| Artefato | Vivo — fonte alinhada ao manifesto `spider-capability-manifest.json` |
| Escopo | Jornada oficial pós-console (015) até piloto controlado (026) |
| Boundary atual | Integrações `MOCK_ONLY` (ativo). CAP-019/020 usam `SIMULATED_INFRASTRUCTURE`. `CORPORATE_SANDBOX` / `REAL_PILOT` são **planejados**, não ativos. |

## Regra de artefato vivo

1. Este documento e o manifesto de capabilities devem permanecer **idênticos** quanto a grupos, títulos, objetivos, status, runtime e níveis de integração de 015–026.
2. Drift é bloqueado por teste de contrato no backend.
3. O cockpit e o Modo Apresentação consomem apenas `GET /v1/console/implementation` — não hardcodam a sequência.

## Legenda de status

| Status | Significado |
|--------|-------------|
| VERIFIED | Entregue e validado por testes |
| PLANNED | Aprovado no roadmap; ainda não iniciado |
| IN_PROGRESS | Somente após emissão formal do prompt |
| IMPLEMENTED / BLOCKED / DEPRECATED | Conforme ciclo de vida |

Runtime: `OFF_BY_DEFAULT` | `NOT_IMPLEMENTED` | …  
Integração planejada ≠ ativa: `MOCK_ONLY`, `SIMULATED_INFRASTRUCTURE`, `CORPORATE_SANDBOX`, `REAL_PILOT`. **Nunca `PRODUCTION` nesta jornada.**

## Grupos oficiais (015–026)

| Código | Prompts | Nome |
|--------|---------|------|
| `GROUP_A_VISIBILITY_OBSERVABILITY` | 015–018 | Visibilidade e observabilidade |
| `GROUP_B_RUNTIME_OPERATIONS` | 019–021 | Operações de runtime |
| `GROUP_C_PLATFORM_READINESS` | 022–024 | Prontidão de plataforma |
| `GROUP_D_REAL_INTEGRATION` | 025–026 | Integração real |

`currentGroup` = **`GROUP_B_RUNTIME_OPERATIONS`** (Grupo B **2/3** — CAP-019 e CAP-020 VERIFIED). Grupo A permanece **4/4 VERIFIED**. `currentPrompt` = **SPIDER-PROMPT-020**.

Agrupamentos históricos de 001–014 permanecem no manifesto para rastreio, sem substituir estes grupos.

## Sequência e objetivos

| Prompt | Grupo | Título | Objetivo | Status | Runtime | Integração planejada |
|--------|-------|--------|----------|--------|---------|----------------------|
| 015 | A | Console Operacional Canônico e Visualização da Execução | Console, cockpit e apresentação dinâmica | VERIFIED | OFF_BY_DEFAULT | MOCK_ONLY |
| 016 | A | Telemetria Canônica e Operational Events | Logs, métricas, traces e eventos correlacionados | VERIFIED | OFF_BY_DEFAULT | MOCK_ONLY |
| 017 | A | Saúde, SLIs, SLOs Provisórios e Cockpit Operacional | Health, SLIs/SLOs simulados, error budget e dashboards | VERIFIED | OFF_BY_DEFAULT | MOCK_ONLY |
| 018 | A | Laboratório de Falhas e Jornadas Operacionais | Fault injection visual, evidências e runbooks Mock | VERIFIED | OFF_BY_DEFAULT | MOCK_ONLY |
| 019 | B | Runtime de Workers Duráveis e Scheduling | Workers, leases, fencing, drain e backlog | VERIFIED | OFF_BY_DEFAULT | SIMULATED_INFRASTRUCTURE |
| 020 | B | Capacidade, Backpressure e Resiliência Governada | Limits, bulkheads, circuits, quotas e load shedding | VERIFIED | OFF_BY_DEFAULT | SIMULATED_INFRASTRUCTURE |
| 021 | B | Operações Governadas e Reconciliation Workbench | Commands seguros e workbench operacional | PLANNED | NOT_IMPLEMENTED | MOCK_ONLY |
| 022 | C | Topologia, Alta Disponibilidade e Continuidade Simulada | Multi-instância, convergência, restore e DR simulado | PLANNED | NOT_IMPLEMENTED | SIMULATED_INFRASTRUCTURE |
| 023 | C | SDK da Porta Universal e Kit de Certificação de Adapters | SDK, harness, simuladores e conformidade | PLANNED | NOT_IMPLEMENTED | MOCK_ONLY |
| 024 | C | Certificação, Quality Gates e Readiness Review | Gates objetivos e decisão READY_FOR_PILOT | PLANNED | NOT_IMPLEMENTED | SIMULATED_INFRASTRUCTURE |
| 025 | D | Fundações Corporativas de Segurança e Transporte | IdP, mTLS, KMS e primeiro binding em sandbox | PLANNED | NOT_IMPLEMENTED | CORPORATE_SANDBOX |
| 026 | D | Primeiro Legado Real, Canary e Migração Controlada | Piloto real, canary, reconciliação e rollback | PLANNED | NOT_IMPLEMENTED | REAL_PILOT |

### Contagens após 020

- Grupo A: **4/4 VERIFIED** (completo)
- Grupo B: **2/3 VERIFIED** (019–020); 021 PLANNED
- 021 elegível (gate 020 cumprido), **não iniciado**
- Grupos C–D: todos PLANNED
- Produto: **0.20.0** · baseline confirmado: **374 backend / 67 frontend** · `npm run build` verde

## Dependências

```text
016 → 015
017 → 016
018 → 017
019 → fechamento do Grupo A (018)
020 → 019
021 → 020
022 → fechamento do Grupo B (021)
023 → 022
024 → 023
025 → 024 (READY_FOR_PILOT)
026 → 025 + aprovação formal do piloto
```

## Pontos de revisão

1. 018 concluído e verificado; Grupo A fechado (4/4).
2. 019 VERIFIED — abre o Grupo B (1/3); runtime OFF_BY_DEFAULT / SIMULATED_INFRASTRUCTURE.
3. 020 VERIFIED — Grupo B 2/3; capacidade/backpressure OFF_BY_DEFAULT / SIMULATED_INFRASTRUCTURE.
4. Fechamento Grupo B (021): gate para 022.
5. 024 = READY_FOR_PILOT: gate para 025.
6. 025 sandbox: gate para 026 piloto; nunca pular para PRODUCTION neste roadmap.

## Referências

- Manifesto: `backend/src/main/resources/implementation/spider-capability-manifest.json`
- Contrato anti-drift: `backend/src/main/resources/implementation/spider-roadmap-015-026-contract.json`
- ARCH-013: `docs/architecture/SPIDER-ARCH-013-console-operacional-e-visualizacao.md`
- ARCH-014: `docs/architecture/SPIDER-ARCH-014-arquitetura-funcional-do-produto.md`
- Técnico 015: `docs/technical/SPIDER-PROMPT-015-operational-console.md`
- Técnico 018: `docs/technical/SPIDER-PROMPT-018-failure-lab-operational-journeys.md`
- Técnico 019: `docs/technical/SPIDER-PROMPT-019-durable-workers-scheduling.md`
- Técnico 020: `docs/technical/SPIDER-PROMPT-020-capacity-backpressure-resilience.md`
- Técnico 021 (autorização de implementação; CAP-021 ainda PLANNED): `docs/technical/SPIDER-PROMPT-021-governed-operations-reconciliation-workbench.md`
