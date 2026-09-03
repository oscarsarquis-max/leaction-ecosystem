# SPIDER-ARCH-016 — Execution Planning and Business Capability Composition

## 1. Decisão

CTX-003 formaliza quatro níveis não sinônimos:

```text
INTENT
  → CONTEXT EXECUTION PLAN
  → BUSINESS CAPABILITIES
  → CAPABILITY RESOLUTION
  → ROUTES / ADAPTERS
  → SPIDER CORE
```

Intent define o que o usuário quer. Context Execution Plan define o que precisa ser feito.
Business Capability define a competência empresarial necessária. Route/Adapter define quem
executa e como.

É proibido resolver Intent diretamente para Route. Também é proibido à IA criar planos, selecionar
capabilities, routes, adapters, endpoints ou sistemas.

## 2. Dois planos com responsabilidades diferentes

`context.planning.ContextExecutionPlan` é o plano empresarial anterior à route. Seu contrato
versionado contém `schemaVersion`, `planId`, `planType`, `intent`, `steps`, `constraints`,
`provenance`, `status` e motivos. Cada step contém `capabilityId`, obrigatoriedade, justificativa e
um campo opcional de condição determinística; não contém endpoint, adapter, target ou route.

`execution.plan.ExecutionPlan`, já existente no Data Plane, continua sendo a materialização técnica
imutável de uma route para uma execução específica. Ele fixa bindings, operações, policies e
versões depois que a route já foi resolvida. Os dois contratos não são intercambiáveis.

## 3. Plan Resolver

`DeterministicExecutionPlanResolver` recebe somente Intent Contract aceito pelo Context Guard.
Consulta `StaticExecutionPlanCatalog` e o catálogo canônico de capabilities. Não recebe provider,
prompt, modelo ou saída livre de IA.

Para a mesma combinação de Intent Contract, catálogo e policies, ele produz o mesmo plano e o mesmo
`planId`, calculado por digest estável do contrato econômico e do `planType`.

Status:

- `READY`: todas as capabilities obrigatórias estão disponíveis;
- `PARTIALLY_AVAILABLE`: ao menos uma está disponível e ao menos uma obrigatória não está;
- `NOT_EXECUTABLE`: nenhuma capability obrigatória está disponível.

Intent inválido, ambíguo, incompleto ou rejeitado não produz plano.

## 4. Business Capability Catalog

`StaticBusinessCapabilityCatalog` é o catálogo canônico usado por planejamento e resolução. Cada
entrada registra:

- `capabilityId` e versão;
- descrição empresarial;
- contratos tipados de input/output;
- mutation type;
- availability;
- routes elegíveis.

Capabilities representam competências, nunca sistemas. `GET_CUSTOMER_PROFILE` não significa
`CUSTOMER_SYSTEM`. Uma route pode futuramente usar ServiceNow ou outro executor, mas ServiceNow não
participa do planejamento e não está integrado neste incremento.

As capabilities de capital de giro são `IDENTIFY_CUSTOMER`, `GET_CUSTOMER_PROFILE`,
`CHECK_CUSTOMER_REGISTRATION`, `GET_CREDIT_PROFILE`, `FIND_ELIGIBLE_PRODUCTS`,
`SIMULATE_WORKING_CAPITAL` e `PRESENT_OPTIONS`. As seis capabilities diagnósticas anteriores foram
preservadas somente para compatibilidade dos seis cards.

## 5. Capability Resolver

`DeterministicCapabilityResolver` percorre os steps na ordem do plano, encontra a definição
canônica e escolhe a route elegível por ordenação estável. O resultado explicável contém descrição,
razão, contratos, disponibilidade, route e adapter/target seguro quando houver.

`NOT_AVAILABLE` não é convertido em mock genérico. O plano composto não é enviado ao Data Plane se
alguma capability obrigatória impedir execução integral.

## 6. Capital de giro

Os quatro contextos convergem para `SEEK_WORKING_CAPITAL`:

- estoque → `purpose=INVENTORY`;
- reforço de caixa → `purpose=CASH_FLOW`;
- matéria-prima → `purpose=RAW_MATERIAL`;
- sazonalidade → `purpose=SEASONALITY`.

`amount` aparece somente quando explicitamente declarado. `businessSituation` preserva a situação
econômica controlada sem escolher produto ou sistema.

O plano `WORKING_CAPITAL_DIAGNOSTIC_V1` contém as sete capabilities na ordem declarada. No boundary
atual, `IDENTIFY_CUSTOMER` usa apenas o contexto autenticado já disponível; as demais capabilities
não têm executor de negócio implementado. O plano é `PARTIALLY_AVAILABLE`, não mostra botão
Executar e não alcança o Data Plane.

## 7. Compatibilidade

`INVESTIGATE_CREDIT_RELEASE` produz `CREDIT_RELEASE_INVESTIGATION_PLAN_V1`, composto por
`CREDIT_RELEASE_DIAGNOSTIC`, que resolve para `CREDIT_RELEASE_DIAGNOSTIC_V1`. O fluxo anterior
continua executável após confirmação.

Os outros cinco cards permanecem demonstráveis e não fingem execução. Natural language, Bedrock,
provenance, confidence, mutation safety, Context Guard, Journey 020B, Engine, runtime e
capacity/backpressure permanecem preservados.

## 8. UI e auditabilidade

`SPIDER ENTENDEU` responde:

1. o que eu quero — Intent e contexto econômico;
2. o que precisa ser feito — Execution Plan e Business Capabilities;
3. como foi executado — routes/adapters e Data Plane Journey.

Capabilities são selecionáveis e exibem somente evidência segura. A Home CTX-003A acrescenta a
**Jornada do Objetivo** com as fases Objetivo → Entendimento → Policy → Plano → Capacidades →
Resolução → Execução → Resultado. Cada fase é clicável, projeta status real e distingue capability
necessária, disponível e executada. PLAN JOURNEY explica o que precisa ser feito; a Execution
Journey 020B continua explicando como o Data Plane executou.

O read model correlaciona `decisionId`, `planId`, capability, route e `executionId`.

O usuário declara objetivos. A IA os compreende. O Spider os decompõe em capacidades. O ambiente
determina onde essas capacidades são executadas. A interface torna cada fase, decisão e resultado
visível e explicável.

Operational Events reutilizados: `EXECUTION_PLAN_RESOLVED`, `EXECUTION_PLAN_REJECTED`,
`CAPABILITY_RESOLVED` e `CAPABILITY_UNAVAILABLE`.

## 9. Boundary

- runtime: `SIMULATED_INFRASTRUCTURE`;
- integrações de negócio: `MOCK_ONLY`;
- produção: fora de escopo;
- CAP-021: `NOT_STARTED`;
- fora de escopo: ServiceNow real, adapter bancário real, planner LLM, agent, RAG, autonomous tool
  calling, Response Composer e execução fictícia de capabilities.
