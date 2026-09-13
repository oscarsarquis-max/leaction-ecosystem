# SEGSENSE_REV_014 — Revisão de aderência do PRM_014

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_REV_014 |
| Versão | 1.0 |
| Data | 13/09/2026 |
| Status | Executado nesta etapa; **não** autoaprovado. Não avança PRM_015. |

## Ressalva herdada (PRM_013)

Após o corretivo único, a cadeia HTTP era real, mas a UI induzia `analyzing` com `setTimeout(400)`. Isso era **impeditivo para apresentação**. Histórico em `SEGSENSE_REV_013`. Este PRM remove a transição fictícia.

## Adendo SAT-003

O contrato V1 existia antes desta execução. O BFF já usava `POST /v1/satellites/interactions`. Este PRM **não** amplia o contrato. Consome-o com honestidade de jornada.

## Matriz requisito → evidência → lacuna

| Requisito | Evidência | Lacuna |
|---|---|---|
| Sem timer de análise | `IntegratedMvpPage.tsx` sem `setTimeout`; testes de fonte e fake timers | — |
| Pré-proposta só com `decisionId` + `providerReference` | `CanonicalJourneyMapper` + UI `isConfirmedPreProposal` | — |
| Erro/timeout sem pré-proposta | testes frontend + mapper | — |
| Provenance sem default local | mapper não preenche `GovernedDemoOrigin` se a Spider omitir | — |
| ACL restrita | `setup-mvp-demo-secrets.ps1` + `Test-MvpRestrictedAcl`; `test-mvp-ops.ps1` | Se icacls falhar, start/load recusam a stack compartilhada |
| Preflight de identidade | `preflight-mvp-demo.ps1`; porta ocupada por processo estranho → erro, sem kill | — |
| SegSense não chama deprecated | `ExperienceSatelliteDecouplingTest` + adapter URI | Fatia deprecated ainda existe na Spider (intencional) |
| Prove canônico | `prove-mvp-http.ps1` | Spider-down live não derruba a JVM (restart longo); coberto por testes |
| Visual 1440/768/390/320/zoom/teclado | — | **Lacuna:** sem browser interativo nesta sessão |
| Independência | três processos; ArchUnit; mock TEST DOUBLE | — |

## Inventário por aplicação

### segsense/

UI honesta; mapper canônico; ACL/preflight/prove; documentos `SEGSENSE_PRM_014`, `SEGSENSE_JRN_EVID_001`, `SEGSENSE_SAT_V1_ADERENCIA_001`, esta revisão.

### spider/

Nenhuma alteração de contrato nesta etapa. Consumo apenas.

### segsense-provider-mock/

Nenhuma alteração de contrato nesta etapa.

### Não tocado

Panne, Hub, School, QMind, Phanton. Sem commit, push, deploy, `git init`. Sem PRM_015.

## Veredito de execução

PRM_014 **executado**, não autoaprovado. Há no máximo um corretivo para este original.
