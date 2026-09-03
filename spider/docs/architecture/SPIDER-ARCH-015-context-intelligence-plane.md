# SPIDER-ARCH-015 — Context Intelligence Plane

## 1. Objetivo

O Context Intelligence Plane acrescenta compreensão formal de objetivos de negócio sobre o
baseline determinístico 0.20.0. Ele transforma uma situação conhecida em `Intent Contract V1`,
aplica política contextual, compõe um Execution Plan empresarial, resolve suas Business
Capabilities e somente então seleciona routes/adapters elegíveis.

CTX-001 estabeleceu o plano contextual inicial; CTX-002 adicionou interpretação por provider
substituível; CTX-003 desacoplou formalmente Intent de Route sem alterar o Spider Core.

## 2. Posição arquitetural

```text
EXPERIENCE PLANE
  │
  ├─ Business Intent Cards (CTX-001)
  └─ Natural Language → AI Context Interpreter (CTX-002; OFF por padrão)
  │
  ▼
INTENT CONTRACT V1 ── fronteira formal
  │
  ▼
CONTEXT POLICY GUARD
  │
  ▼
DETERMINISTIC EXECUTION PLAN RESOLVER
  │
  ▼
BUSINESS CAPABILITIES
  │
  ▼
CAPABILITY RESOLVER
  │
  ▼
ROUTES / ADAPTERS
  │
  ▼
CANONICAL INGRESS → SPIDER CORE → RESULT
```

A zona probabilística termina no Intent Contract. Abaixo dessa fronteira, schema, política,
planejamento, resolução de capabilities, roteamento e execução permanecem determinísticos.

## 3. Intent Contract V1

O contrato tipado está em `context.contract.IntentContract`; seu schema normativo está em
`context/intent-contract-v1.schema.json`.

Campos:

- identidade: `schemaVersion`, `intent`;
- contexto de negócio: `domain`, `objective`;
- entidades necessárias: `entities`;
- restrições: `mutationAllowed`, `readOnly`, `confirmationRequired`;
- proveniência: `source` e `sourceRef`;
- confiança: `confidence`.

Cards determinísticos usam `confidence=1.0` e `provenance.source=BUSINESS_CARD`.
Interpretações CTX-002/003 usam `NATURAL_LANGUAGE` e ainda passam pelo mesmo Guard. CTX-003 preserva
V1 e representa contexto econômico nas entidades `purpose`, `amount` e `businessSituation`;
valores ausentes permanecem ausentes.

## 4. Catálogo de situações

`StaticBusinessIntentCatalog` preserva exatamente seis Business Intent Cards demonstrativos e
acrescenta `SEEK_WORKING_CAPITAL` ao vocabulário de interpretação, sem criar um sétimo card.

Intent, Execution Plan, capability, rota e operação canônica são identidades distintas. Por
exemplo:

```text
INVESTIGATE_CREDIT_RELEASE
  ↓ policy
CREDIT_RELEASE_INVESTIGATION_PLAN_V1
  ↓ composição
CREDIT_RELEASE_DIAGNOSTIC
  ↓ capability resolution
CREDIT_RELEASE_DIAGNOSTIC_V1
  ↓ mock binding do Data Plane
RETRY_THEN_SUCCESS
```

A UI recebe o contrato conhecido do catálogo, mas não conhece endpoint de sistema de destino,
adapter nem processor.

As seis situações produzem preview determinístico. Conforme o escopo do prompt, somente
`INVESTIGATE_CREDIT_RELEASE` está habilitada ponta a ponta em CTX-001; as demais deixam explícito
que a execução ainda é preview-only, em vez de reutilizar um mock semanticamente falso.

## 5. Context Policy Guard

`ContextPolicyGuard` valida antes do roteamento:

- presença dos campos obrigatórios;
- schema `1.0`;
- intent conhecida;
- coerência entre intent, domínio e objetivo;
- entidades obrigatórias;
- origem e confiança;
- identidade autenticada;
- política de mutação.

Decisões possíveis: `ACCEPTED`, `MISSING_CONTEXT`, `AMBIGUOUS`, `NOT_AUTHORIZED`,
`POLICY_REJECTED` e `UNSUPPORTED_INTENT`.

CTX-001 aceita somente consulta. `mutationAllowed=true` ou `readOnly!=true` é rejeitado antes do
Core. Preview e execução são operações separadas; a confirmação deve referenciar a mesma decisão
e o mesmo contrato.

## 6. Planejamento e resolução determinísticos

O `ExecutionPlanResolver` somente recebe contratos aceitos. Mesmos Intent Contract, Plan Catalog,
Business Capability Catalog e policies produzem o mesmo `ContextExecutionPlan`, inclusive
`planId`, steps e status. Cada step referencia somente `capabilityId`.

O `CapabilityResolver` avalia disponibilidade e seleciona deterministicamente uma route elegível.
O `DeterministicIntentRouter` permanece apenas como fachada de compatibilidade para a route
primária dos planos de um único step; ele já não recebe `IntentContract`.

> Intent não resolve diretamente para Route. Intent resolve deterministicamente para Execution
> Plan. Execution Plan é composto por Business Capabilities. Cada Capability é resolvida para
> Route/Adapter apropriado.

Não existe condicional de intent na Home e não existe chamada direta da experiência a endpoint de
sistema externo.

## 7. Execução e fronteira com o Core

`ContextIntelligenceService` materializa um pedido canônico comum e usa
`SubmitCanonicalExecutionUseCase`. Portanto continuam obrigatórios:

- autenticação do ingress;
- autorização capability/operation;
- correlação e idempotência;
- resolução de rota e plano;
- persistência, redaction e Operational Events;
- políticas de runtime e capacidade.

Um contrato inválido, não confirmado ou diferente do preview não chama o submit canônico. O teste
`ContextCoreBoundaryTest` congela essa fronteira.

## 8. Proveniência, eventos e auditabilidade

O read model contextual correlaciona `decisionId`, principal, Intent Contract, decisão da policy,
`planId`, plano, capabilities, routes, executionId e timestamps. O armazenamento contextual
permanece em memória no local-demo; ele não substitui a persistência técnica do Core.

O mecanismo existente de Operational Events recebe eventos da categoria `CONTEXT`:

- `INTENT_CREATED`;
- `INTENT_VALIDATED`;
- `EXECUTION_PLAN_RESOLVED` / `EXECUTION_PLAN_REJECTED`;
- `CAPABILITY_RESOLVED` / `CAPABILITY_UNAVAILABLE`;
- `ROUTE_RESOLVED`.

Os atributos passam pela allowlist e pela redaction existentes. Payloads, headers, tokens e
credenciais não entram no read model visual.

Eventos de planejamento anteriores à execução usam o `decisionId` como correlação contextual.
Quando há execução, `planId` é propagado para eventos e payload canônico seguro.

## 9. Context Journey

A Jornada 020B não foi substituída. Quando uma execução possui decisão contextual, o mesmo
componente apresenta:

```text
CONTEXTO
  ✓ Objetivo selecionado
  ✓ Intent construído
  ✓ Política validada
  ✓ Plano determinado
  ✓ Capabilities resolvidas

PLANO
  ○ Capability 1 — resolução, não execução
  ○ Capability 2 — resolução, não execução
  …

DATA PLANE
  ✓ Solicitação recebida
  ✓ Contrato canônico
  ✓ Engine
  …
```

As etapas vêm do read model produzido por resolução real, e não de timers ou animação. A zona
`PLANO` registra resolução e disponibilidade; seu marcador não afirma que a capability foi
executada. Execuções sem contexto continuam exibindo apenas o Data Plane.

### 9.1 Clareza visual da experiência — CTX-001A

A experiência contextual separa compreensão de execução. Business Cards e linguagem natural
convergem para o mesmo Intent Contract antes da entrada no Data Plane.

Na Home, o usuário percebe a sequência:

```text
OBJETIVO → INTENT → POLICY → PLANO → CAPABILITIES → EXECUTAR → JORNADA
```

O clique em **Investigar** encerra apenas a fase de compreensão e abre **SPIDER ENTENDEU**. Esse
painel projeta dados reais do contrato e da resolução: objetivo, intent, contexto econômico,
provenance, confidence, constraints, policy, Execution Plan e capabilities. Route/adapter aparece
somente no detalhe explicável da capability ou na execução.
Nenhum Data Plane é acionado nessa fase.

Somente Crédito oferece **Executar** no CTX-001. Os outros cinco cards mostram o mesmo contrato e a
mesma validação visual, mas declaram `preview-only` e não exibem ação de execução. Após a confirmação
de Crédito, a mesma Jornada 020B apresenta duas zonas:

- **CONTEXTO** — o que o usuário pretende e qual plano foi determinado;
- **PLANO** — quais capabilities foram resolvidas e para quais routes;
- **DATA PLANE** — como o Spider efetivamente executou a operação.

As etapas contextuais continuam selecionáveis e explicáveis. Seus textos usam intent, domínio,
constraints, policy, capability e rota do read model, sem inferência visual.

## 10. Flags e boundary

- `spider.context.enabled=false`;
- `spider.context.ui.enabled=false`;
- `spider.context.ai.enabled=false`;
- profile `local-demo`: Context/UI são `true`, mas IA só ativa por configuração explícita;
- integrações: `MOCK_ONLY`;
- runtime demonstrativo: `SIMULATED_INFRASTRUCTURE`;
- provider inicial: AWS Bedrock / Anthropic Claude, substituível pela porta interna;
- timeout: `PT8S`; retry do adapter: desabilitado; confidence mínima: policy centralizada em `0.80`.

`AI OFF` não significa `Context OFF`: cards, contrato, guard, router, auditoria e jornada funcionam
sem modelo.

## 11. Segurança e mutation safety

Context Intelligence não concede autorização. O controller reutiliza a autenticação deny-by-
default do ingress canônico, e o submit continua passando pela autorização canônica. Intenção
válida não implica execução permitida.

CTX-001/002 são somente leitura, exigem confirmação e rejeitam mutação. A interpretação
probabilística não altera constraints nem converte interpretação em efeito externo.

## 12. AI Context Interpreter — CTX-002

A IA é uma fonte probabilística de Intent Contract. Ela não possui autoridade de roteamento ou
execução.

```text
texto redigido
  → ContextInterpretationProvider
  → resposta estruturada
  → validação sintática/semântica contra catálogo
  → Intent Contract V1
  → mesmo Context Policy Guard
  → Deterministic Execution Plan Resolver
  → Capability Resolver
  → confirmação
  → Spider Core
```

`ContextInterpretationProvider` não expõe route, capability, endpoint, adapter ou Core. O adapter
inicial encapsula integralmente tipos AWS Bedrock/Anthropic e envia ao modelo somente texto redigido,
versões e o vocabulário controlado dos intents. O prompt
`context/context-interpreter-v1.txt` é versionado como `CTX-INTERPRETER-1.1`.

A resposta aceita é exclusivamente JSON estruturado com `status`, intent controlada, entidades
explicitamente extraídas, candidatos e confidence. Domain e objective são materializados a partir
do catálogo local; nunca são autoridades do modelo. Intent inexistente, chave de entidade não
permitida, JSON inválido, timeout ou indisponibilidade falham antes do Plan Resolver/Core.

Resultados:

- `MATCHED` com contexto completo: produz contrato `NATURAL_LANGUAGE`, passa pelo Guard e pelo
  planejamento determinístico;
- `MISSING_CONTEXT`: o Guard rejeita o contrato e a UI pergunta pelo identificador ausente;
- `AMBIGUOUS`: não produz contrato operacional nem rota;
- `UNSUPPORTED_INTENT`: não produz contrato operacional nem rota;
- falha técnica: fail-closed para IA e fail-open para cards/plataforma.

Metadados seguros — provider, model, prompt/schema version, latency, usage e campos redigidos — ficam
na evidência de interpretação associada ao decision record. Texto bruto não é persistido; somente a
versão redigida. Não há chain-of-thought.

Para evidência sem credenciais cloud existe provider `scripted-evidence`, condicionado simultaneamente
ao profile `local-demo`, provider `scripted` e opt-in `scripted-enabled=true`. Ele não é smoke Bedrock
e nunca é habilitado por padrão.

## 13. Execution Planning e Business Capabilities — CTX-003

`ContextExecutionPlan` é o contrato empresarial versionado anterior à route. Ele contém
`schemaVersion`, `planId`, `planType`, `intent`, `steps`, `constraints`, `provenance`, `status` e
motivos. Não se confunde com `execution.plan.ExecutionPlan`, que continua sendo a materialização
técnica e imutável de uma route para uma execução do Data Plane.

O catálogo canônico de capabilities registra descrição, contratos de entrada/saída, mutation type,
availability e routes elegíveis. `AVAILABLE` significa que existe resolução suportada no boundary;
`NOT_AVAILABLE` nunca aciona mock substituto. Planos usam `READY`, `PARTIALLY_AVAILABLE` ou
`NOT_EXECUTABLE`.

O primeiro plano composto é `WORKING_CAPITAL_DIAGNOSTIC_V1`. Estoque, reforço de caixa,
matéria-prima e sazonalidade convergem para `SEEK_WORKING_CAPITAL`, preservando `purpose`, valor
somente quando explícito e situação empresarial. Apenas a identificação pelo contexto autenticado
está disponível; as consultas, elegibilidade, simulação e apresentação restantes são declaradas
indisponíveis. Portanto o plano demonstrativo é parcial e não alcança o Data Plane.

CTX-003A não cria arquitetura nova: projeta a cadeia já existente na Home como **Jornada do
Objetivo**. Cada fase — Objetivo, Entendimento, Policy, Plano, Capacidades, Resolução, Execução e
Resultado — tem status, resumo, evidência e painel clicável no padrão 020B. O resultado é
determinístico. A IA permanece visível somente no Entendimento quando a origem é linguagem natural.

O usuário declara objetivos. A IA os compreende. O Spider os decompõe em capacidades. O ambiente
determina onde essas capacidades são executadas. A interface torna cada fase, decisão e resultado
visível e explicável.

## 14. Evolução futura, não implementada

Ficam fora de CTX-003/003A: Response Composer, embeddings, RAG, agents, planner LLM, tool calling,
ServiceNow real, operações mutáveis e integração corporativa real. CAP-021 permanece
`PLANNED / NOT_IMPLEMENTED` (`NOT_STARTED` neste ciclo).
