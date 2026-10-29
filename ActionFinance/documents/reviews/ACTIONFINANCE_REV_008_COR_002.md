# ACTIONFINANCE_REV_008_COR_002 — Fechamento da consulta pela Spider

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_008_COR_002 |
| Prompt | [ACTIONFINANCE_PRM_008_COR_002](../prompts/ACTIONFINANCE_PRM_008_COR_002.md) |
| Data | 30/09/2026 |
| Executor | Cursor |
| Ambiente | Isolado (AF `:8091`/`:5179`, Spider `:8080`, borda SIMULATOR `:8097`, Postgres 17.6 `:5439`). Sem deploy, commit, push, pagamento real ou PRM_009. |
| Aceite | Analista: **aprovado e encerrado** em 01/10/2026. [Encerramento](ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA.md). Relato original abaixo preservado. |

Este complemento não declara Pay real integrado, payout, baixa automática nem viabilidade geral da Spider. A prova continua sendo orquestração AF→Spider→borda, com **simulador explicitamente identificado**. FORWARD contra Hub local **não** foi exercitado.

## Residual independente do PRM_007

O restore PITR isolado foi **limpo** no ciclo anterior **antes** de comprovar invalidação das sessões restauradas (`SPRING_SESSION`). Esse gate **não** está concluído. Este corretivo **não** recria RDS, **não** pede login humano e **não** declara publicação.

## Escolha de identidade (DAT)

**Uma linha com conclusão.** `lookup_attempt.id` é estável: `beginAttempt` insere `STARTED` e `finishAttempt` conclui a **mesma** linha (`completed_at`, `received_outcome`, `observation_applied`, `discarded_reason`). O salto HTTP usa `attempt_correlation_id` = `afa-{attemptId}`, distinto de `external_operation.correlation_id`.

`observation_applied` só é verdadeiro quando `updateIfVersion` gravou mudança financeira desta tentativa. Descarte explícito: `CONCURRENT`, `STALE`, `RECOVERED`. O booleano de `updateIfVersion` não é mais ignorado.

Intenção e conclusão usam transações curtas `REQUIRES_NEW`. Nenhuma transação permanece aberta durante o HTTP.

V11 é incremental: V1–V10 não foram editadas. Eventos V10 irmãos (STARTED e resultado com ids distintos) **não são pareados**; o backfill só preenche `completed_at` quando o `outcome` já não era `STARTED`. Vínculos não são inventados.

## 1. Identidade e recuperação — evidência

| Pedido | Resultado | Classificação |
|---|---|---|
| Duas consultas simultâneas, identidades distintas | `ExternalLookupReliabilityIT.concurrentFirstCreateKeepsSingleOperation`: 1 operação, 2 `lookup_attempt.id` distintos, 0 `completed_at` nulo | **Executado** em PostgreSQL 17.6 (Testcontainers) |
| Resposta descartada não marcada aplicada | `staleResponseIsNotMarkedApplied`: 1 linha `discarded_reason=STALE` e `observation_applied=false` | **Executado** |
| Queda após intenção + reinício | IT `persistedStartWithoutResponseIsRecoveredWithoutLosingObservation` **e** ensaio no Postgres local: INSERT `STARTED` → `stop-local`/`start-local` → GET: tentativa `UNAVAILABLE`/`RECOVERED`, observação `REVIEW_REQUIRED` + `12550` preservada | **Executado** |
| Observação anterior não perdida | GET após reinício: `externalStatus=REVIEW_REQUIRED`, `amountMinor=12550`; tentativa recuperada `observation_applied=f` | **Executado** |

IT: **10** testes, **0** fail, **0** skip (após o complemento de recuperação concorrente). Flyway **V1–V11** (log: `Migrating ... version "11 - lookup attempt identity"`).

Contagem no Postgres local após a jornada (não é o container do IT):

| Referência | Tentativas | Ids distintos | STARTED aberto | `observation_applied` |
|---|---|---|---|---|
| `pay-homolog-0001` | 18 | 18 | 0 | 4 |
| `pay-homolog-ausente` | 8 | 8 | 0 | 0 |

## 2. Jornada UX 1280 / 360

Fatia subida com scripts existentes: `start-prm008-edge` (TEST_CONTROL=1), Spider `spring-boot:run` `local-demo`, `start-local.ps1` com homolog. Stack desligada foi só preparação.

Roteiro: `frontend/scripts/capture-prm008-cor-002-lookup.mjs`. Removidas esperas com catch vazio e asserções que passavam só com o texto estático “Simulador”. Cada cenário exige o `dd[data-lookup-observation]` e `dd[data-lookup-attempt]` específicos **antes** da captura. A mesma referência `pay-homolog-0001` evolui por fixture da borda.

| Cenário | Observação exigida | Tentativa exigida | Capturas |
|---|---|---|---|
| Referência inexistente | Aguardando envio | Falha de transporte — observação anterior preservada | `*-inexistente.png` |
| Consulta válida | Confirmado pelo Pay | Resposta válida recebida | `*-confirmada.png` |
| Indisponível após válida | Confirmado pelo Pay (conservada) | Falha de transporte — observação anterior preservada | `*-indisponivel.png` |
| Recuperação | Confirmado pelo Pay | Resposta válida recebida | `*-recuperacao.png` |
| Divergência (mesma ref) | Requer revisão | Divergência em revisão | `*-divergencia.png` |

Medidas Playwright: `scrollWidth=clientWidth` em **1280** e **360** (10 capturas). Foco no botão Consultar verificado. Flash: “O título não foi baixado.” Origem: “Simulador da borda Pay”. Data: “Sem carimbo do provedor” quando a fixture não envia `providerObservedAt`.

Arquivos: [`documents/reviews/screenshots/prm-008-cor-002/`](screenshots/prm-008-cor-002/). Log: `journey-log.json`.

## 3. Prova da Spider em execução

Registro sem segredos: [`spider-interrupt-recovery.json`](screenshots/prm-008-cor-002/spider-interrupt-recovery.json).

| Ponto | Antes | Spider só interrompida | Spider religada |
|---|---|---|---|
| AF | Consulta via `spiderBaseUrl` | Tentativa `UNAVAILABLE`; observação `REVIEW_REQUIRED` (anterior) | Mesmo caminho; observação `REVIEW_REQUIRED` |
| Spider | `dispatched=14`, `capabilityId=LOOKUP_ACTIONHUB_PAYMENT`, correlações `afa-…` | Health down | Health up; RAM zerada (`dispatched=1`); última correlação `afa-b3846dc9-…`; capability `LOOKUP_ACTIONHUB_PAYMENT` |
| Borda | `homolog-padaria:pay-homolog-0001` = **11**, mode=SIMULATOR | Contador **11** (não aumentou); health UP | Contador **12** |

A borda permaneceu saudável. Só a Spider isolada foi interrompida. EXPERIENCE sem `EXECUTE_CAPABILITY` (regressão `ActionFinanceSatelliteInteractionHttpTest`). Credenciais do Pay continuam fora do AF.

## 4. Limites e classificação

| Afirmação | Estado |
|---|---|
| SIMULATOR comprova orquestração, não Pay vivo | **Declarado.** Capturas e JSON identificam o simulador. |
| FORWARD / Hub local com dados descartáveis | **Não executado.** Rota Hub continua off por padrão. |
| Fila durável / cobrança / motor de pagamentos | **Não implementado.** |
| Spider em RAM | **Limitação explícita** (stats e idempotência somem no restart da Spider; o AF Postgres permanece). |
| Panne / compras | **Fora.** |
| `mvn verify` completo AF após V11 | Ver complemento do parecer (abaixo). |
| Regressão Hub | **Não executada** (Hub não alterado). |
| Capturas COR_001 | **Não reutilizadas.** |

## Testes (esta sessão)

| Comando | Resultado | Tipo |
|---|---|---|
| `mvn test -Dtest=ExternalLookupRulesTest,ExternalLookupServiceTest` | BUILD SUCCESS (reexecutado após o ajuste da chave) | Executado |
| `mvn verify -Dit.test=ExternalLookupReliabilityIT` | **8** completed, 0 fail, 0 skip; Flyway V11 | Executado |
| `cd frontend && npm test -- --run` | **38** pass, 0 skip | Executado |
| `npm run lint` + `npm run build` | eslint ok; Vite build ok | Executado |
| `node --test edge.test.js` | **7** pass, 0 skip (reexecutado após Maps locais) | Executado |
| Spider `ActionHubPayLookupIdentityTest,ActionFinanceSatelliteInteractionHttpTest,SatelliteContractJsonSchemaTest,SatelliteContractV1Test` | BUILD SUCCESS | Executado |
| `node scripts/capture-prm008-cor-002-lookup.mjs` | 10 PNG + log; sem overflow | Executado |
| Interrupção/recuperação Spider | JSON acima | Executado |
| Reinício AF com STARTED persistido | GET + SQL `RECOVERED` | Executado |
| FORWARD Hub local | — | Não executado |
| `mvn verify` AF integral | surefire **31** + failsafe **53** = **84**, 0 fail, 0 skip; BUILD SUCCESS (complemento) | Executado |

## Migrations e stack final

- Nova: `database/migrations/V11__lookup_attempt_identity.sql`. Runtime ganha UPDATE em `lookup_attempt`.
- Stack ao parar para o aceite: Postgres AF `:5439` no ar (volume preservado); API `127.0.0.1:8091` `homologIntegration=true` / `spiderIntegrationStatus=HOMOLOG_LOOKUP`; UI `:5179`; Spider `:8080`; borda `:8097` SIMULATOR TEST_CONTROL. Monitor `:5180` **não** foi exigido nesta fatia.

## Documentação atualizada só onde o comportamento mudou

DAT 0.91, UX 0.9, INT 0.61, índice, SAT-003 §14 (lookup-stats), parecer do analista. Prompt integral em `documents/prompts/ACTIONFINANCE_PRM_008_COR_002.md`.

## Encerramento (entrega original)

Ciclo **pronto para revisão do analista**. Sem autoaceite. Sem deploy, commit ou push. Sem PRM_009.

## Complemento — parecer do analista (recuperação concorrente)

Parecer integral copiado em [`ACTIONFINANCE_REV_008_COR_002_PARECER_ANALISTA.md`](ACTIONFINANCE_REV_008_COR_002_PARECER_ANALISTA.md). Evidências visuais e `spider-interrupt-recovery.json` **não** foram refeitas.

### Correção

`recoverStale` deixa de decidir pelo `ExternalLookupView` lido antes da transação. Relê a operação com `FOR UPDATE`, lista tentativas `STARTED` com `completed_at` nulo e `started_at` ≤ limiar, e só então `finishAttempt` (`UNAVAILABLE` / `RECOVERED`, `observation_applied=false`). `markRecoveredIfCurrentAttempt` exige `last_attempt_id` = tentativa expirada, `last_attempt_outcome=STARTED` e `last_attempt_at` ≤ limiar. Tentativa nova não é marcada pela recuperação da antiga.

`complete` bloqueia a operação e a tentativa (`attemptStillOpen`). Se a linha já estiver `RECOVERED`, a resposta tardia não aplica observação. Locks só nas transações curtas; HTTP continua fora de TX.

### ITs com barreiras (sem sleep como sincronização)

`LookupConcurrencyGate` (no-op em produção). Contagem atual: **10** testes em `ExternalLookupReliabilityIT`.

| Teste | Barreira | Esperado |
|---|---|---|
| `recoveringExpiredAttemptDoesNotDiscardNewerStartedAttempt` | GET lê A expirada → POST inicia B **sem** recuperar A → GET recupera A → B responde | Após o GET: A `RECOVERED`/`observation_applied=false` e a operação ainda aponta B (`last_attempt_id` ≠ A, `last_attempt_outcome=STARTED`). Depois: B `DELIVERED` rastreável; observação de B aplicada pela política normal (`REFUNDED`) |
| `recoverAndCompleteSameAttemptStayConsistent` | Recuperação e conclusão da mesma tentativa no mesmo `go` | Uma conclusão; se `RECOVERED`, observação anterior `CONFIRMED` e auditoria sem apply; se `DELIVERED`, apply só quando a política gravou |

O IT anterior permitia que o POST chamasse `recoverStale` antes de `beginAttempt`, recuperando A **antes** de B existir. Isso não cobria o interleaving do parecer. O POST da disputa A/B agora suprime a recuperação nesta thread (`LookupConcurrencyGate.suppressRecoverOnThisThread`); o GET é quem recupera A depois de B ser `last_attempt_id`.

### `mvn verify` AF (estado final, sem skip) — 01/10/2026

Primeira passagem integral desta sessão falhou só em `MixedCompanyAuthorizationIT` ao carregar o contexto: `Demo token viewerA is missing`. O IT não fixava tokens de viewer no `DynamicPropertySource` e herdava o vazio de `application-local-demo.properties`. Isolamento de teste (iguais aos demais ITs); produto e tokens reais inalterados. Hub, frontend e Spider **não** reexecutados.

| Comando | Resultado | Tipo |
|---|---|---|
| `mvn verify -Dit.test=ExternalLookupReliabilityIT` | **10** completed, 0 fail, 0 skip; Flyway V11 | Executado (01/10/2026) |
| `mvn verify` AF integral | surefire **31** + failsafe **53** = **84**, 0 fail, 0 skip; Flyway V11 em todos os ITs; BUILD SUCCESS (01:38). `ExternalLookupReliabilityIT` **10**/10. `MixedCompanyAuthorizationIT` **1**/1. | Executado (01/10/2026) |
| Hub / frontend / Spider | — | Não repetidos (inalterados neste complemento) |

Documentação: DAT **0.91**, INT **0.61**, índice, parecer. UX 0.9 sem reabertura de layout (aviso verde e fullPage no meio do documento ficam como nota do analista, sem mudança de shell).

### Limites (inalterados)

FORWARD/Hub real não exercitado. Spider em RAM. Sem dinheiro real, baixa automática, Panne, deploy, commit ou push. PRM_007 separado (invalidação de sessão no restore pendente). Sem RDS novo e sem login humano. Sem PRM_009.

**Encerrado pelo analista em 01/10/2026.** Parecer: [ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA](ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA.md). Sem PRM_009.
