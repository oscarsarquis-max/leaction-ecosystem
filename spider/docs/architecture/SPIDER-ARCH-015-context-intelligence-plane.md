# SPIDER-ARCH-015 — Context Intelligence Plane

## 1. Objetivo

O Context Intelligence Plane acrescenta compreensão formal de objetivos de negócio sobre o
baseline determinístico 0.20.0. Ele transforma uma situação conhecida em `Intent Contract V1`,
aplica política contextual, determina capability e rota e somente então entrega um pedido ao
ingress canônico já protegido.

CTX-001 estabeleceu o plano determinístico; CTX-002 adicionou interpretação por provider
substituível sem alterar o Spider Core.

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
DETERMINISTIC ROUTER
  │
  ▼
CANONICAL INGRESS → SPIDER CORE → RESULT
```

A zona probabilística termina no Intent Contract. Abaixo dessa fronteira, schema,
política, autorização, roteamento e execução permanecem determinísticos.

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
`NATURAL_LANGUAGE` existe no vocabulário para compatibilidade futura, mas não é produzido nem
interpretado neste incremento.

## 4. Catálogo de situações

`StaticBusinessIntentCatalog` contém exatamente uma situação demonstrativa para cada domínio
inicial: crédito, cobrança, faturamento, dados do cliente, atendimento e incidente.

Intent, capability, rota e operação canônica permanecem identidades distintas. Por exemplo:

```text
INVESTIGATE_CREDIT_RELEASE
  ↓ policy
CREDIT_RELEASE_DIAGNOSTIC
  ↓ deterministic route
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

## 6. Deterministic Router

`DeterministicIntentRouter` somente recebe contratos aceitos. Mesma entrada, catálogo e policy
produzem o mesmo `IntentRouteResolution`. A resolução declara capability e rota contextual; o
binding canônico continua sendo resolvido pelo catálogo de rotas existente no Core.

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
rota, executionId e timestamps. CTX-001 usa armazenamento em memória, coerente com o boundary
local-demo; ele não substitui a persistência técnica do Core.

O mecanismo existente de Operational Events recebe eventos da categoria `CONTEXT`:

- `INTENT_CREATED`;
- `INTENT_VALIDATED`;
- `ROUTE_RESOLVED`.

Os atributos passam pela allowlist e pela redaction existentes. Payloads, headers, tokens e
credenciais não entram no read model visual.

Rejeições anteriores à criação de uma execução ficam no read model de decisão contextual; não são
forçadas para Operational Events com um `executionId` fictício.

## 9. Context Journey

A Jornada 020B não foi substituída. Quando uma execução possui decisão contextual, o mesmo
componente apresenta:

```text
CONTEXTO
  ✓ Objetivo selecionado
  ✓ Intent construído
  ✓ Política validada
  ✓ Rota determinada

DATA PLANE
  ✓ Solicitação recebida
  ✓ Contrato canônico
  ✓ Engine
  …
```

As quatro etapas de card — ou cinco etapas de linguagem natural, incluindo a interpretação — vêm
do read model produzido por resolução real, e não de timers ou animação. Execuções sem contexto
continuam exibindo apenas o Data Plane.

### 9.1 Clareza visual da experiência — CTX-001A

A experiência contextual separa compreensão de execução. Business Cards e linguagem natural
convergem para o mesmo Intent Contract antes da entrada no Data Plane.

Na Home, o usuário percebe a sequência:

```text
OBJETIVO → INTENT → POLICY → ROTA → EXECUTAR → JORNADA
```

O clique em **Investigar** encerra apenas a fase de compreensão e abre **SPIDER ENTENDEU**. Esse
painel projeta dados reais do contrato e da resolução: objetivo, intent, domínio, provenance,
confidence, constraints, decisão do Guard, policy, capability, rota e disponibilidade de execução.
Nenhum Data Plane é acionado nessa fase.

Somente Crédito oferece **Executar** no CTX-001. Os outros cinco cards mostram o mesmo contrato e a
mesma validação visual, mas declaram `preview-only` e não exibem ação de execução. Após a confirmação
de Crédito, a mesma Jornada 020B apresenta duas zonas:

- **CONTEXTO** — o que o usuário pretende e como o Spider determinou o tratamento;
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
  → mesmo Deterministic Router
  → confirmação
  → Spider Core
```

`ContextInterpretationProvider` não expõe route, capability, endpoint, adapter ou Core. O adapter
inicial encapsula integralmente tipos AWS Bedrock/Anthropic e envia ao modelo somente texto redigido,
versões e o vocabulário controlado dos seis intents. O prompt
`context/context-interpreter-v1.txt` é versionado como `CTX-INTERPRETER-1.0`.

A resposta aceita é exclusivamente JSON estruturado com `status`, intent controlada, entidades
explicitamente extraídas, candidatos e confidence. Domain e objective são materializados a partir
do catálogo local; nunca são autoridades do modelo. Intent inexistente, chave de entidade não
permitida, JSON inválido, timeout ou indisponibilidade falham antes do Router/Core.

Resultados:

- `MATCHED` com contexto completo: produz contrato `NATURAL_LANGUAGE`, passa pelo Guard e Router;
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

## 13. Evolução futura, não implementada

Ficam fora de CTX-002: Response Composer, embeddings, RAG, agents, planner LLM, tool calling,
ServiceNow, novas intents, operações mutáveis e integração corporativa real. CAP-021 permanece
`PLANNED / NOT_IMPLEMENTED`.
