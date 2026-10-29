# ACTIONFINANCE_REV_008_COR_001 — Confiabilidade da consulta via Spider

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_008_COR_001 |
| Prompt | [ACTIONFINANCE_PRM_008_COR_001](../prompts/ACTIONFINANCE_PRM_008_COR_001.md) |
| Data | 30/09/2026 |
| Executor | Cursor |
| Ambiente | Isolado. Sem deploy, commit, push, pagamento real ou PRM_009. |
| Aceite | Analista: **aprovado e encerrado** em 01/10/2026 com o ciclo PRM_008. [Encerramento](ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA.md). Relato original abaixo preservado. |

Este corretivo não declara Pay real integrado, payout, baixa automática nem viabilidade geral da Spider. A prova continua sendo orquestração AF→Spider→borda, com simulador na borda salvo FORWARD validado.

## Residual independente do PRM_007

O restore PITR isolado foi **limpo** no ciclo anterior **antes** de comprovar invalidação das sessões restauradas (`SPRING_SESSION`). Esse gate **não** está concluído. Este corretivo **não** recria RDS, **não** pede novo login e **não** interrompe a consulta isolada.

Publicação de `https://actionfinance.actionhub.com.br` permanece não declarada.

## Separação das alterações

| Origem | O que mudou | O que não mudou |
|---|---|---|
| ActionFinance | V10 `lookup_attempt` + `last_attempt_*` + REFUNDED; serviço sem TX durante HTTP; 409 de vínculo; regras de observação vs tentativa; painel UX | Núcleo financeiro, baixa, PRM_006, ingresso AWS |
| Spider | Validação de identidade da resposta Pay; nota SAT 1.3 | Contratos 1.0–1.2; EXPERIENCE sem EXECUTE |
| Borda Hub | SIMULATOR/FORWARD exclusivos; HTTPS; sem fallback a fixture | Núcleo de checkout/payout do Hub |
| Hub gateway | Rota de consulta continua off por padrão; sandbox só com prova | Sem simulação de payout |

Documentação 1.3 (INT 0.5, DAT 0.8, UX 0.8, SAT §14) não reescreve evidência anterior ao 1.3.

## Tabela C1–C5

| ID | Pedido | O que foi feito | Evidência | Classificação |
|---|---|---|---|---|
| **C1** | Modos exclusivos; FORWARD tipado; sandbox comprovado; HTTPS; rota Hub isolada | `resolveMode` SIMULATOR/FORWARD; 404/401/500/corpo/timeout sem fixture; `http:` remoto recusado; `https.request` com `rejectUnauthorized: true`; Hub exige `LOOKUP_ENABLED` **e** `LOOKUP_ISOLATED` | `node --test edge.test.js` **7/7 skip 0**; `spider-pay-lookup.test.js` **5/5 skip 0** | **Comprovado em contrato da borda/Hub.** FORWARD contra Hub local com fixture descartável **não** foi exercitado neste corretivo. Não é sandbox vivo do processador. |
| **C2** | Identidade empresa+ref; 409 outro título; fingerprint com título; concorrência; reconsulta ≠ replay imutável | Unique `(tenant,company,origin,ref)`; insert com recuperação de unique; fingerprint `company\|ref\|ACTIONHUB_PAY\|titleId` + upgrade de legado; mapping/vínculo antes de replay; cada tentativa em `lookup_attempt` | `ExternalLookupServiceTest` **7/7**; `ExternalLookupReliabilityIT` **6/6 skip 0** (Postgres 17.6): criação concorrente 1 operação; 409 outro título; empresas distintas; revogação esconde GET e recusa POST; resposta atrasada | **Comprovado em Postgres real do IT.** Não é idempotência durável de comando financeiro. |
| **C3** | Identidade da resposta; amountMinor exacto; observação ≠ tentativa; divergência; REFUNDED; sem observedAt inventado | Regras em `ExternalLookupRules` + `ActionHubPayLookupIdentity`; timeout preserva CONFIRMED; valor divergente → REVIEW sem trocar valor; REFUNDED sucede CONFIRMED; fração/overflow rejeitados | `ExternalLookupRulesTest` **7/7**; `ActionHubPayLookupIdentityTest` **4/4**; IT timeout e late observation | **Comprovado em unidade + IT.** Sem baixa/estorno automático. |
| **C4** | Intenção antes do HTTP; sem TX aberta no transporte; log de tentativas; Spider RAM declarada | `insertAttempt(STARTED)` + `markAttemptStarted` **antes** de `spider.lookup`; update versionado depois; comentário SQL: não é outbox | Fluxo em `ExternalLookupService`; IT conta ≥2 tentativas na criação concorrente | **Consulta somente leitura.** Restart AF preservaria a operação no Postgres; **memória da Spider continua não durável.** Pagamento/criação de cobrança bloqueados. |
| **C5** | Gates, C1–C4, navegador 1280/360, correlação, Spider down | Testes acima + Vitest painel; script Playwright `frontend/scripts/capture-prm008-cor-001-lookup.mjs`; HTTP Spider 1.3 + schemas 1.0–1.3 | AF `mvn verify`: Surefire **42** + Failsafe **49** = **91**, 0 fail, 0 skip. Frontend Vitest **38/38 skip 0**. Spider (esta sessão, seleção 1.0–1.3 + identidade): V1 22, schema 5, AF HTTP 4, satélite HTTP 4, SpiderBank HTTP 3, identity 4 — **0 fail / 0 skip**. Jornada Playwright **não executada**: stack AF+Spider+borda não estava no ar neste corretivo | **Contrato/orquestração com simulador.** Sem afirmação de Pay real. Sem captura 1280/360 neste ciclo. |

## Caminho AF → Spider → provider

- AF só conhece `spiderBaseUrl` (`HttpSpiderInteractionClient`). Sem URL/secret do Pay.
- Spider `QUERY_STATUS` 1.3 seleciona `LOOKUP_ACTIONHUB_PAYMENT` e chama a borda. EXPERIENCE não executa capability (`ActionFinanceSatelliteInteractionHttpTest`).
- Correlação: AF envia `correlationId`; borda devolve o mesmo; adapter recusa correlação/referência/empresa divergentes.
- Spider down: AF registra tentativa `UNAVAILABLE` e **não** altera a observação financeira. Sem fallback para Pay.
- Contagem de chamadas: borda incrementa por `payAppId:externalReference`; AF grava uma linha `lookup_attempt` por tentativa (STARTED + resultado).

Não foi montada instrumentação de rede compose neste corretivo. A prova de “desligar Spider impede chegar ao provider” no código: o cliente AF não tem outro host.

## Hub local vs simulador

A rota `GET /v1/integration/payments/:id` existe e permanece desligada sem os dois flags isolados. **Não** exercitamos o Hub local com fixture descartável neste corretivo (bloqueio operacional: stack Hub+Pay local não foi subida). Classificação: **contrato/orquestração com simulador**. Não afirmar Pay real integrado. Não foi criada cobrança no Mercado Pago.

## Limites declarados (não inferir sucesso)

- Spider em RAM: limitação desta consulta sem efeito de cobrança. Sem aceite de idempotência durável de comandos financeiros.
- `integration_message` OUTBOX/INBOX **não** é fila. O log efetivo é `lookup_attempt`.
- Origem `ACTIONHUB_PAY` só após FORWARD com envelope válido e `sandbox: true`.
- Loja de Pães de produção (`624023a4-…`) **não** está no binding local-demo.
- Sem conector Panne, sem PRM_009, sem dinheiro real.

## Comandos desta sessão (C5)

```text
cd spider/tools/actionhub-pay-edge && node --test edge.test.js
  → 7 pass, 0 skip

cd leaction-platform/services/gateway-api && node --test domain/spider-pay-lookup.test.js
  → 5 pass, 0 skip

cd ActionFinance/frontend && npm test -- --run
  → 38 pass, 0 skip (6 arquivos)

cd spider/backend && mvn -q test "-Dtest=ActionHubPayLookupIdentityTest,ActionFinanceSatelliteInteractionHttpTest,SatelliteContractJsonSchemaTest,SatelliteContractV1Test"
  → BUILD SUCCESS (22+5+4+4 nesta seleção; suites 1.0–1.2 do mesmo target: SatelliteInteractionHttpTest 4, SpiderBank 3)

cd ActionFinance/backend && mvn -q test "-Dtest=ExternalLookupRulesTest,ExternalLookupServiceTest"
  → 7+7 pass, 0 skip

cd ActionFinance/backend && mvn -q verify "-Dit.test=ExternalLookupReliabilityIT"
  → 6 pass, 0 skip, Flyway V1–V10

cd ActionFinance/backend && mvn -q verify
  → Surefire 42 + Failsafe 49 = 91, 0 fail, 0 skip (Flyway V10 em todos os ITs)
```

Jornada Playwright: `node frontend/scripts/capture-prm008-cor-001-lookup.mjs` (exige UI local + `ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A` + `ACTIONFINANCE_INTEGRATION_HOMOLOG=true`). **Não rodada.**

## Encerramento

Ciclo **pronto para revisão do analista**. Sem autoaceite. Sem deploy, commit ou push. Sem PRM_009.

**Encerrado pelo analista em 01/10/2026** com o ciclo PRM_008. Parecer: [ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA](ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA.md).
