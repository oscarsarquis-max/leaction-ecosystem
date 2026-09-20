# SPIDERBANK-IMP-002
## Segunda entrega — jornada demonstrativa de crédito com sistemas executores

**Data da prova:** 18 de setembro de 2026  
**Escopo:** SPIDERBANK-ARQ-004  
**Fronteira:** MOCK_ONLY / SIMULATED_INFRASTRUCTURE / NON_BINDING_DEMO  
**Não substitui:** [SPIDERBANK-IMP-001](SPIDERBANK-IMP-001.md)

## Conclusão

A jornada demonstrativa de capital de giro foi executada pelos sistemas simulados, com retorno ao SpiderBank e evidência no Monitor. Não houve decisão de crédito real, contratação nem desembolso.

Caminho observado: SpiderBank → SAT-003 → Spider (plano `WORKING_CAPITAL_DIAGNOSTIC_V1` e Capability Resolution) → `credit-provider-mock` (passos 2–6) → composição `PRESENT_OPTIONS` → SpiderBank. O card da Simulação apontou `http://127.0.0.1:5190/`.

## 1. Identidades da prova de sucesso

| Campo | Valor |
|---|---|
| Origem | `spiderbank` (EXPERIENCE) |
| Sujeito sintético | `cust-demo-ok` |
| Ambiente da sessão | `TEST_DOUBLE` |
| correlationId | `877ecdd5-3b36-49f2-ac9c-a6995b32100f` |
| decisionId | `spd-ab668d71-2946-4e63-9599-d3029406f411` |
| contextRef | `ctx-9fc735fc-8e75-41a4-afe7-f6596583ec65` |
| Intent / plano (Spider) | `SEEK_WORKING_CAPITAL` / `WORKING_CAPITAL_DIAGNOSTIC_V1` |
| Status SAT | `READY` / `PRESENT_SIMULATION` |
| Status BFF | `SIMULATION_SHOWN` |
| simulationComplete | `true` |
| analysisComplete | `false` |
| creditDecision | `NONE` |
| offerable / testDouble | `false` / `true` |
| Executor passos 2–6 | `credit-provider-mock` |
| Cálculo sintético | 1.000.000 centavos, 12 meses → total 1.120.000 centavos |
| Replay | mesmo `decisionId`, sem novo despacho de negócio no BFF |

Arquivos: `documents/evidencias/SPIDERBANK-IMP-002/journey-success.json`, `journey-replay.json`, `demo-session.json`.

## 2. Etapas e executores

| # | Capability | Executor na prova de sucesso |
|---|---|---|
| 1 | IDENTIFY_CUSTOMER | interno (`context-principal`), sujeito `cust-demo-ok` |
| 2 | GET_CUSTOMER_PROFILE | `credit-provider-mock` / `credit-mock/0.2` / `WORKING_CAPITAL_ASSESSMENT` |
| 3 | CHECK_CUSTOMER_REGISTRATION | idem |
| 4 | GET_CREDIT_PROFILE | idem |
| 5 | FIND_ELIGIBLE_PRODUCTS | idem; alternativa `WC_SYNTHETIC_TEST_1`, `offerable=false` |
| 6 | SIMULATE_WORKING_CAPITAL | `credit-provider-mock` / `credit-mock/0.1` / `WORKING_CAPITAL_SIMULATION` |
| 7 | PRESENT_OPTIONS | composição interna dos resultados recebidos |

O frontend e o BFF não calcularam parcelas nem fabricaram alternativa.

## 3. Impedimentos honestos (prova ao vivo)

| Caso | correlationId | decisionId | Resultado |
|---|---|---|---|
| Sem sessão/afirmação | `99bfe54e-6e7b-4645-8eb5-3b173769208c` | `spd-fcca8e3f-4085-4260-bded-f2a49abbe00e` | `ANALYSIS_BLOCKED`; IDENTIFY_CUSTOMER impedida; `providerDispatched=false` |
| Cadastro sintético pendente | `dfeaefbc-68ec-4aec-b9e2-b0f712ec0bc0` | `spd-51051674-ed9d-4bc5-8a00-06dfb7316dde` | `NEEDS_CONTEXT` em `CHECK_CUSTOMER_REGISTRATION`; sem simulação |
| Inelegibilidade sintética | `ba7eddad-927c-4390-ac28-dfea14ce9d3f` | `spd-ceb28602-24b1-45e4-acab-a1132ffcdb7a` | `SYNTHETIC_BLOCKED` em `FIND_ELIGIBLE_PRODUCTS`; sem simulação |
| Sem valor/prazo | `236ae5cf-e21d-41c5-9895-d6e79fb661ed` | `spd-4d5a6901-4a4d-485d-8085-3070dc98c16e` | `NEEDS_CONTEXT` (`principalCents`, `termMonths`) |
| Valor inválido | — | — | HTTP 400 `VALIDATION_ERROR` no BFF, sem chamada útil à Spider |
| Pendência humana sintética | `628d9596-fa4a-446e-a889-e881c094db78` | `spd-00ffe976-7fc6-4bfa-aa47-60cbecf0d9e0` | `SYNTHETIC_REVIEW`; `reviewQueued` não abre fila real |

Timeout, credencial inválida do mock e resposta adulterada (`offerable=true`) permanecem cobertos pelos testes do adapter/mock: HTTP 200 não basta; o adapter classifica como indisponibilidade técnica, sem fallback financeiro.

Capability/rota ausente: `WorkingCapitalDiagnosticExecutorTest.missingCapabilityRouteImpedesEvenIfTheMockCouldBeOnline` — `PLAN_IMPEDED` sem `providers.execute`.

## 4. Monitor e card

Eventos da correlação `877ecdd5-3b36-49f2-ac9c-a6995b32100f` em `monitor-events.json`:

- `originSatellite=spiderbank`, `currentComponent=SPIDER`, `aiUsage=NOT_USED`
- `CAPABILITY_DISPATCHED` e `PROVIDER_RESULT_RECEIVED` reais (não fabricados)
- `SATELLITE_RESPONSE_RETURNED` comprova a resposta da Spider; o BFF e o produto foram verificados à parte

Card da Simulação (`monitor-simulation.json`): `spiderbank.available=true`, `url=http://127.0.0.1:5190/`. SegSense permaneceu disponível. O `/health` do mock manteve `integratedWithSpider=false` e `chainReadiness=determined_by_spider`.

Um caso de cliente sintético recusado não tornou a infraestrutura indisponível.

## 5. Testes executados

| Suíte | Resultado |
|---|---|
| `mock-sistemas-credito` `npm test` (7 testes, 0.1 + 0.2) | passou |
| SpiderBank BFF `mvn test` | passou (reexecução posterior colidiu com `spring-boot:run` no mesmo `target`; a suíte já havia passado) |
| SpiderBank frontend `npm test` (3 testes) | passou |
| Spider `DemoCustomerAssertionTest`, `WorkingCapitalDiagnosticExecutorTest`, `SpiderBankSatelliteContractTest`, `SatelliteContractV1Test`, `SatelliteContractJsonSchemaTest`, `MonitorEventsTest`, `LocalDemoSimulationScenariosTest`, `SpiderBankSatelliteInteractionHttpTest` | passou |
| Spider `SatelliteInteractionHttpTest`, `SegSenseDemoDecisionServiceTest`, `CanonicalEngineMockIntegrationTest`, `LocalDemoCanonicalHttpAccessTest` | passou |
| Monitor frontend `SimulationPanel.test.jsx`, `MonitorShell.test.jsx` | passou (16 testes) |

Não foi reexecutada a suíte Maven completa do backend Spider nem o `npm test` integral do Monitor. CAP-021–026 e Reconciliation Workbench não foram abertos.

Não houve ferramenta de browser MCP nesta sessão. A prova de interface foi HTTP do produto (`:5190/`, BFF) + testes de componente. Isso não equivale a clique ponta a ponta.

## 6. Como reproduzir

Shell suportado: Windows PowerShell 5.1+.

1. Monitor (`:5180`) e SegSense podem permanecer no ar.
2. Engine `local-demo` em `:8080` precisa das mesmas variáveis `SPIDER_SPIDERBANK_DEMO_APPLICATION_SECRET`, `SPIDER_SPIDERBANK_CUSTOMER_ASSERTION_SECRET` e `SPIDER_CREDIT_MOCK_CREDENTIAL` (a lista viva é em memória: subir o mock e o BFF **antes** da prova final, depois do restart do engine).
3. Em `C:\Projetos\spider-bank`:

```powershell
.\scripts\setup-local-secrets.ps1
.\scripts\start-local.ps1
.\scripts\check-health.ps1
```

4. Abrir **http://127.0.0.1:5190/** — não `/spiderbank` do Monitor.
5. Usar a sessão demonstrativa, confirmar o objetivo, informar valor/prazo e enviar.
6. No Monitor, filtrar a correlação. Devem existir despacho e retorno de provider.
7. Encerrar só o que `start-local` registrou:

```powershell
.\scripts\stop-local.ps1
```

## 7. Limites permanentes desta fatia

- Sem aprovação, contratação, desembolso, bureau ou instituição financeira.
- `scenarioKey` é controle técnico de fixture; não aparece na UI pública.
- Idempotência de interação: replay devolve o resultado armazenado; não é exatamente uma vez.
- A afirmação HMAC é local-demo. Não é KYC nem IdP real.
- `READY` / `SIMULATION_SHOWN` significa simulação concluída, não análise de crédito concluída.
