# SEGSENSE_REV_016 — Revisão de aderência do PRM_016

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_REV_016 |
| Versão | 1.1 |
| Data | 14/09/2026 |
| Status | PRM_016 executado; único corretivo COR_001 executado nesta etapa. **Não** autoaprovado. Não inicia PRM_017. |

## Reprogramação

O identificador PRM_016 **não** entregou atribuição/indicadores. Entregou a primeira jornada contextual utilizável. Indicadores permanecem adiados (`SEGSENSE_PLN_001` v1.20, `SEGSENSE_ADR_005`). Sem renumeração silenciosa.

## Contrato V1

Schema `1.0` **não** foi alterado. Compatibilidade: `objective.text/origin`, `context.snapshot`, `inputs.scenarioKey`, status `MISSING_CONTEXT`/`AMBIGUOUS`/`REJECTED`. `scenarioKey` legado = `sourceId`; intenções novas = `sourceId|objective`. Rota deprecated `/v1/demo/segsense/**` não é caminho principal.

## Implementado vs mock vs seguradora

| Camada | Evidência |
|---|---|
| Implementado | Entrada texto/ditado/link governado; intenção confirmada; BFF V1; regras de allowlist na Spider; UI em quatro blocos; V14 |
| Mock sintético | Possibilidades `ILLUSTRATIVE_POSSIBILITY` / `ILLUSTRATIVE_NOT_ICATU_CONTRACT` |
| Dependente de seguradora autorizada | Cotação, proposta, produto Icatu, elegibilidade, URL pública arbitrária |

## Exemplos A/B (runtime de teste, não a stack da reunião)

| Entrada | `scenarioKey` enviado ao Test Double | Primeiro `code` |
|---|---|---|
| Fonte familiar + `UNDERSTAND_PROTECTION_OPTIONS` | `SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1\|UNDERSTAND_PROTECTION_OPTIONS` | `ILLUSTRATIVE_FAMILY_CONTINUITY_CONVERSATION` |
| Fonte renda + `COMPARE_COVERAGE_GAPS` | `SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1\|COMPARE_COVERAGE_GAPS` | `ILLUSTRATIVE_INCOME_GAP_COMPARE` |
| `REQUEST_BINDING_QUOTE` | — | Spider `REJECTED`; `providers.execute` nunca chamado |
| Relato `asdf` | — | SegSense `MISSING_CONTEXT`; gateway não chamado |
| URL `169.254.169.254` | — | `INVALID_CONTEXT_URL`; sem fetch |

Prova de encaminhamento: `SatelliteContractV1Test.differentSourceAndIntentionChangeScenarioKey` captura dois `ExecutionRequest` com `scenarioKey` distintos e capability `BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO`. Mock `handler.test.js` confirma títulos/códigos diferentes e ausência de `R$` / “Icatu Seguros”.

## Observabilidade Spider

Eventos `SATELLITE_REQUEST_RECEIVED`, `SATELLITE_AUTHENTICATED`, `SATELLITE_DECISION_CREATED`, `CAPABILITY_DISPATCHED`, `PROVIDER_RESULT_RECEIVED`, `SATELLITE_RESPONSE_RETURNED`. Store de idempotência em memória. Sem tela pública. Sem segredo no browser.

## Gates

| Gate | Resultado |
|---|---|
| Frontend Vitest | 15 arquivos, **67/67** |
| Frontend eslint | ok |
| Frontend `tsc -b && vite build` | ok |
| Mock `node --test` | **7/7** |
| Spider `SatelliteContractV1Test` + `SegSenseDemoDecisionServiceTest` | ok (`mvn`, exit 0) |
| SegSense `mvnw verify` | exit 0; Flyway V1–**V14** em banco Testcontainers vazio (duas subidas IT) |
| `ExperienceSatelliteDecouplingTest` | SegSense não referencia `:8095`, mock path nem `/v1/demo/segsense` |
| Prova isolada `PROVIDER_UNAVAILABLE` | **COMPROVADO** (`spd-7c507e58-…`; sem `capabilityId`/`providerReference`/itens). Mock reunião pid **10688** e Spider `:8080` pid **54468** inalterados. JVM isolada `25500` parada após verificação |
| E2E HTTP da jornada nova nos três processos da reunião (`:8095`/`8080`/`8088`) | **NÃO COMPROVADO** — listeners da reunião são anteriores a este código e **não** têm ledger; `stop-mvp-demo.ps1` recusaria. Não foram mortos |
| Ditado em navegador com Web Speech | **NÃO COMPROVADO**. jsdom: fallback “indisponível” + texto utilizável |
| Visual 1440/768/390/320, zoom 200%, teclado, impressão | **NÃO COMPROVADO** — não há browser interativo nesta sessão. Roteiro em `SEGSENSE_DEMO_RUN_001` v1.7 |
| Commit / push / deploy | Não executados |

## Correções herdadas do PRM_015

| Item | Resultado |
|---|---|
| Aceite visual | Continua **não executado** nesta sessão |
| Ledger / stop fail-closed / sem `pids.txt` | Preservado. Isolado não tocou a reunião |
| IDs/técnica na primeira dobra | Movidos para `details`. Primeira dobra: contexto, intenção, possibilidades |

## Lacunas honestas (não substituídas por narrativa)

1. Inspeção visual humana ausente.
2. Jornada causal A/B **não** foi vista na stack da reunião (código novo só em testes + Spider isolada).
3. Ditado real não exercitado.
4. V14 ainda **não** está no Postgres `:5437` da reunião até o BFF ser iniciado com este código.
5. Working tree Spider Experience Hub / screenshots **alheio**, não editado neste PRM.

## Veredito

PRM_016 **executado** para auditoria. Não autoaprovado. Não há PRM_017 nesta conversa.

## COR_001 — história dos cinco desvios

Único corretivo permitido. Não autoaprovado. Não inicia PRM_017.

| # | Antes (PRM_016) | Depois (COR_001) |
|---|---|---|
| 1 | `assembleContext` com URL e relato vazios chamava `family()` e podia seguir até o gateway | Fluxo público devolve `MISSING_CONTEXT`, sem Spider. Legado só em `POST /api/v1/public/demo/legacy-protection-journeys` |
| 2 | Replay comparava só `declaredObjective` | Fingerprint canônico SHA-256 (V15) **antes** do lookup; mesmo pedido → mesmo `id`; mudança material → 409 sem projeção. PII rejeitada antes do hash. Linha com fingerprint nulo → 409 |
| 3 | Editar relato/URL/intenção após READY mantinha possibilidades antigas; resolve A→B podia aplicar `resolved` tardio | Inputs congelados em `awaiting`; AbortController + serial; descarte + nova chave ao mudar inputs depois de `done`; impressão oculta o formulário |
| 4 | Copy “nada de áudio é enviado” | O SegSense não recebe nem grava áudio; o reconhecimento é do navegador e não é controlado pelo produto |
| 5 | E2E da versão nova **NÃO COMPROVADO** nos listeners da reunião | Stack isolada `:19095/:19080/:19088/:15178/:15437`; reunião preservada. Resultado HTTP: ver gates COR_001 abaixo |

### Gates COR_001

| Gate | Resultado |
|---|---|
| Frontend Vitest | 15 arquivos, **74/74** |
| Frontend eslint | ok |
| Frontend `tsc -b && vite build` | ok |
| Mock `node --test` | **7/7** |
| SegSense `mvnw verify` | exit 0; Flyway V1–**V15** em banco Testcontainers vazio |
| `prove-isolated-cor016.ps1` | **COMPROVADO** (`isolatedHttpProof=COMPROVADO`). A/B chaves no mock: `SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1\|UNDERSTAND_PROTECTION_OPTIONS` e `SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1\|COMPARE_COVERAGE_GAPS`. REJECTED sem provider. Vazio/insuficiente sem Spider. Conflito `AMBIGUOUS`. URL inválida 400. Revogada 409. Replay idêntico. 409 em mudança de contexto. Provider down `MOCK_UNAVAILABLE` sem itens |
| Stack da reunião `:8095/:8080/:8088/:5178` | Preservada (pids 10688 / 54468 / 20736 / 47472). `meetingStackUntouched=true`. Volume `segsense_pgdata` não tocado. Isolated Postgres `:15437` volume `segsense_pgdata_isolated_cor016` |
| Visual 1440/768/390/320, zoom 200%, teclado, impressão, ditado real | **NÃO COMPROVADO** — não há browser interativo nesta sessão. Roteiro em `SEGSENSE_DEMO_RUN_001` v1.8. HTTP 200 do Vite isolado **não** é prova visual |
| Commit / push / deploy | Não executados |

## Veredito COR_001

COR_001 **executado** para auditoria. Não autoaprovado. Sem PRM_017. Pendências residuais seguem como ressalvas do único corretivo.

