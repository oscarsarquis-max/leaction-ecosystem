# SEGSENSE_ADR_005 — Reprogramação do PRM_016 e compatibilidade do Satellite Contract V1

## Controle

- Projeto: SegSense
- Categoria: decisão arquitetural
- Versão: 1.0
- Data: 14/09/2026
- Estado: vigente nesta etapa; **não** autoaprovada

## Decisão

O identificador `SEGSENSE_PRM_016` deixa de designar atribuição/indicadores nesta execução. A etapa entrega a **primeira jornada contextual de negócio utilizável** (contexto mostrado, intenção declarada e confirmada, possibilidades ilustrativas, explicação Spider, pendências humanas). Atribuição e indicadores **permanecem adiados**. Não houve renumeração silenciosa: o trabalho original de indicadores **não** passou a ser o PRM_017. O PRM_017 continua Segurança e conformidade.

## Por que não houve versão nova de schema

O Satellite Contract V1 já comporta a fatia:

| Necessidade da UI | Campo V1 existente | Uso nesta etapa |
|---|---|---|
| Intenção humana confirmada | `objective.text` + `objective.origin` | `origin=USER_DECLARED` no BFF; allowlist na Spider |
| Contexto governado | `context.snapshot.provenance` + `attributes` (máx. 8 chaves × 200) | tema, situação, necessidade, horizonte, restrição + canal/versão |
| Distinção A/B sem segunda capability | `inputs.scenarioKey` (máx. 120) | `sourceId` no legado; `sourceId\|objective` nas intenções novas |
| Insuficiência / conflito | `MISSING_CONTEXT` / `AMBIGUOUS` | HTTP 200 no envelope válido; 400 se o envelope não tem snapshot |
| Recusa sem provedor | `REJECTED` + allowlist de objetivos | `REQUEST_BINDING_QUOTE` não está na lista |

Nenhuma alteração de JSON Schema `1.0`. Clientes que enviam o objetivo legado `UNDERSTAND_FAMILY_PROTECTION_OPTIONS` continuam a receber `scenarioKey` igual ao `sourceId` familiar. A rota deprecated `/v1/demo/segsense/**` **não** é o caminho principal.

## O que isto não autoriza

- URL pública arbitrária, fetch cego ou SSRF.
- Intent Contract pleno, CTX-004, Eligibility Gate, Data Plane.
- Cotação, proposta, produto Icatu, composição de apólice, IA ou avaliação atuarial.
- Tela pública de auditoria da Spider.
- Commit, push ou deploy.

## Consequência operacional

A stack da reunião que já estava no ar **sem** ledger `.mvp-logs/owned-run.json` não é parada por `stop-mvp-demo.ps1`. A jornada nova só aparece depois de uma partida que carregue este código. V14 adiciona `MISSING_CONTEXT` e `AMBIGUOUS` ao CHECK da tabela demo; V15 adiciona `request_fingerprint` nullable. V1–V14 não foram reescritas. A prova COR_001 usa volume isolado `segsense_pgdata_isolated_cor016`, não `segsense_pgdata`.
