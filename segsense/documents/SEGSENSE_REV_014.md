# SEGSENSE_REV_014 — Revisão de aderência do PRM_014

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_REV_014 |
| Versão | 1.1 |
| Data | 14/09/2026 |
| Status | PRM_014 + COR_001 executados; **não** autoaprovados. Não avança PRM_015. |

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

## Veredito de execução (PRM_014 original)

PRM_014 **executado**, não autoaprovado. Há no máximo um corretivo para este original.

## Adendo COR_001 (14/09/2026)

Único corretivo de linguagem comprovada. Copy-only na Spider (`explanation` READY/REJECTED) e na UI de espera/pré-proposta. Satellite Contract V1, mock e fatia deprecated **inalterados estruturalmente**.

| Requisito COR_001 | Evidência | Lacuna |
|---|---|---|
| Espera só como fato do cliente | `IntegratedMvpPage.tsx`: `Solicitação enviada; aguardando resposta do SegSense…` em `phase=awaiting` | — |
| Sem “Spider recebeu/analisa” no pendente | testes frontend pending + falha de rede | — |
| Explicação READY determinística | `SatelliteInteractionService` + `SatelliteContractV1Test` | — |
| Explicação REJECTED sem “compreendeu” | mesmo serviço + teste REJECTED | — |
| Pré-proposta ecoa `explanation` da Spider | mapper passa `text(node, "explanation")`; frontend não substitui | — |
| Matriz de evidência alinhada | `SEGSENSE_JRN_EVID_001` v1.1 | — |
| Home `/` e Icatu | auditoria de copy: posicionamento / editorial; esta página não chama a Spider | Sem alteração de copy; não há ocorrência de jornada canônica nessas rotas |
| Prove canônico com redação nova | `prove-mvp-http.ps1`: READY e BFF ecoam a copy determinística; REJECTED usa allowlist; 401/400/409; scan de segredo ok | `mockDownStatus=READY`: o primeiro `mock=` em `pids.txt` estava obsoleto; o Test Double em `:8095` não foi interrompido. `PROVIDER_UNAVAILABLE` permanece coberto por teste unitário. |
| Visual 1440/768/390/320/zoom/teclado | — | **Lacuna:** sem browser interativo nesta sessão. Auditoria independente anterior: desktop + uma pré-proposta; **não** substitui a matriz. |

### Inventário COR_001 por aplicação

- `segsense/`: copy da jornada, testes, prove HTTP, docs `SEGSENSE_PRM_014_COR_001`, JRN_EVID, este REV, DEMO_RUN.
- `spider/`: somente strings `explanation` READY/REJECTED. Schema e endpoint intactos.
- `segsense-provider-mock/`: sem alteração.

Veredito COR_001: **executado**, não autoaprovado. Não há segundo corretivo do PRM_014. Não inicia PRM_015.
