# SPIDER-ARCH-003 — Contrato Canônico e Modelo de Execução

| Campo | Valor |
|---|---|
| Identificador | SPIDER-ARCH-003 |
| Título | Contrato Canônico e Modelo de Execução |
| Status | Proposta arquitetural inicial |
| Predecessor | SPIDER-ARCH-002 — Metamodelo Contextual |
| Escopo | Contratos e semântica de execução, sem implementação |

## 1. Objetivo

Formalizar o contrato canônico e o modelo determinístico de execução do Spider. Este documento define o envelope técnico universal recebido pela Engine, a fronteira entre Engine e Adapter, os resultados e erros canônicos e os requisitos de identidade, estado, versionamento, idempotência, callback, auditoria e rastreabilidade.

Este documento não define tabelas, classes, endpoints, tecnologia de transporte, regras bancárias nem integração com legados reais. Não autoriza alteração do código de produção.

## 2. Vocabulário normativo

Os termos “deve”, “não deve” e “somente” expressam requisitos arquiteturais. “Pode” expressa uma possibilidade admitida. “Contrato publicado” é um contrato aprovado, versionado, imutável e elegível para uso no Data Plane.

## 3. Decisão central

O Contrato Canônico é um **envelope técnico universal com referências contextuais**. Ele transporta somente os dados necessários à execução autorizada e referencia o contexto e as definições governadas que lhe deram origem.

O Contrato Canônico:

- não é uma réplica do Contexto;
- não consolida cadastros mestres de cliente, conta, contrato, produto ou transação;
- não duplica dados de negócio disponíveis em sistemas responsáveis;
- não transforma o Spider em System of Record;
- não impõe o contrato de um legado aos demais destinos;
- não incorpora decisões ou regras bancárias;
- deve adotar referências estáveis e autorizadas em vez de cópias de dados mestres;
- pode transportar em `payload.canonicalData` apenas o conjunto mínimo de dados necessário ao passo ou à execução.

A persistência associada ao contrato é técnica: identidade da execução, versões resolvidas, estados, idempotência, evidências, auditoria e referências. Dados de negócio eventualmente presentes no payload permanecem sob política de minimização, classificação, mascaramento e retenção.

## 4. Posição na cadeia arquitetural

```text
Contexto
   ↓ evidencia
Intenção
   ↓ requer
Capacidade
   ↓ é realizada por
Produto/Serviço
   ↓ disponibiliza
Jornada
   ↓ produz uma intenção técnica executável
Contrato Canônico
   ↓ é resolvido contra
Rota versionada
   ↓ materializa
Steps
   ↓ invocam pela porta universal
Adapter
   ↓ integra nesta fase / na fase final
Mock Endpoint / Legado real
```

As camadas anteriores ao Contrato Canônico resolvem o resultado desejado e fixam referências governadas. A partir do Contrato Canônico, a Engine executa uma intenção técnica explícita; ela não reinterpreta a necessidade original.

## 5. Fronteiras de responsabilidade

### 5.1 Responsabilidades da Engine

A Engine deve:

- validar o envelope, sua versão e as referências obrigatórias;
- resolver somente rotas e definições publicadas e compatíveis;
- fixar a versão exata da rota e das dependências usadas;
- construir e executar um plano determinístico;
- coordenar steps e seus estados técnicos;
- aplicar políticas técnicas aprovadas de timeout, retry, resiliência e idempotência;
- invocar adapters por contrato universal;
- normalizar resultados técnicos, mantendo separado o resultado de negócio delegado;
- produzir evidências, auditoria, métricas e traces correlacionados;
- realizar callbacks somente quando declarados e autorizados.

A Engine **não interpreta a necessidade bancária e não decide nem executa regra de negócio**. Ela não calcula elegibilidade, risco, limite, preço, score ou aprovação; não altera resultados emitidos pelo domínio responsável; e não escolhe livremente produtos, endpoints ou comportamentos fora das versões governadas.

### 5.2 Responsabilidades do Adapter

O Adapter deve:

- implementar a porta canônica vista pela Engine;
- traduzir entrada, saída e erro entre o modelo canônico e o contrato externo;
- encapsular transporte, serialização, autenticação técnica e particularidades do destino;
- declarar capacidades operacionais, limites e garantias de idempotência;
- preservar correlação e propagação de trace quando o destino permitir;
- impedir o vazamento de detalhes tecnológicos para a Engine.

Regras bancárias continuam no domínio responsável. Um Adapter traduz e integra; ele não deve se tornar um local oculto de decisão bancária.

## 6. CanonicalExecutionRequest

### 6.1 Estrutura lógica

```text
CanonicalExecutionRequest
│
├── contract
│   ├── schemaVersion
│   └── contractVersion
│
├── execution
│   ├── executionId
│   ├── timestamp
│   └── idempotencyKey
│
├── contextRef
│   ├── contextId
│   ├── intentId
│   ├── capabilityId
│   ├── productServiceId
│   └── journeyId
│
├── origin
│   ├── channel
│   ├── originatorId
│   └── interactionRef
│
├── trace
│   ├── correlationId
│   ├── traceparent
│   └── tracestate
│
├── target
│   ├── capability
│   └── operation
│
├── payload
│   └── canonicalData
│
├── executionPolicy
│   ├── timeout
│   ├── retryPolicyRef
│   └── resiliencePolicyRef
│
└── callbackRef
```

### 6.2 Semântica dos campos

| Campo | Obrigatoriedade | Semântica |
|---|---|---|
| `contract.schemaVersion` | Obrigatório | Versão do schema estrutural usado para validar o envelope |
| `contract.contractVersion` | Obrigatório | Versão semântica do contrato canônico e de suas regras de compatibilidade |
| `execution.executionId` | Obrigatório | Identidade única e imutável desta execução |
| `execution.timestamp` | Obrigatório | Instante de criação do pedido, em formato temporal interoperável |
| `execution.idempotencyKey` | Condicional | Chave da mesma operação lógica dentro de escopo e janela definidos |
| `contextRef.contextId` | Obrigatório | Referência à ocorrência contextual de origem |
| `contextRef.intentId` | Obrigatório | Intenção resolvida e governada |
| `contextRef.capabilityId` | Obrigatório | Capacidade principal solicitada |
| `contextRef.productServiceId` | Obrigatório | Produto ou serviço governado associado |
| `contextRef.journeyId` | Obrigatório | Jornada selecionada; deve permitir identificar sua versão fixada |
| `origin.channel` | Obrigatório | Canal ou classe do originador |
| `origin.originatorId` | Obrigatório | Identidade lógica autenticada do originador |
| `origin.interactionRef` | Condicional | Referência à interação de origem, sem exigir sua cópia no Spider |
| `trace.correlationId` | Obrigatório | Correlação funcional ponta a ponta, estável entre interações relacionadas |
| `trace.traceparent` | Obrigatório na fronteira distribuída | Contexto W3C que identifica trace e span corrente |
| `trace.tracestate` | Opcional | Estado adicional de fornecedores conforme W3C Trace Context |
| `target.capability` | Obrigatório | Capacidade técnica canônica a acionar |
| `target.operation` | Obrigatório | Operação governada dentro da capacidade |
| `payload.canonicalData` | Condicional | Dados mínimos, validados por schema e necessários à execução |
| `executionPolicy.timeout` | Condicional | Limite solicitado, sujeito aos limites da política governada |
| `executionPolicy.retryPolicyRef` | Condicional | Referência a política publicada; nunca definição arbitrária inline |
| `executionPolicy.resiliencePolicyRef` | Condicional | Referência a política publicada de resiliência |
| `callbackRef` | Condicional | Referência governada ao callback autorizado, não URL arbitrária em claro |

Identificadores de catálogo devem referenciar versões exatas ou permitir que a resolução governada as fixe antes do início da execução. A evidência da execução deve registrar sempre as versões exatas utilizadas.

### 6.3 Exemplo ilustrativo não normativo

```json
{
  "contract": {
    "schemaVersion": "1.0",
    "contractVersion": "1.0.0"
  },
  "execution": {
    "executionId": "exec-018f-example",
    "timestamp": "2026-08-21T12:00:00Z",
    "idempotencyKey": "originador:operacao:123"
  },
  "contextRef": {
    "contextId": "ctx-123",
    "intentId": "COMPREENDER_COBRANCA@1.0.0",
    "capabilityId": "CONSULTAR_LANCAMENTO@2.0.0",
    "productServiceId": "SERVICO_ATENDIMENTO_FINANCEIRO@1.0.0",
    "journeyId": "JORNADA_ESCLARECIMENTO_COBRANCA@2.0.0"
  },
  "origin": {
    "channel": "ASSISTED_CHANNEL",
    "originatorId": "originator-logical-id",
    "interactionRef": "interaction-456"
  },
  "trace": {
    "correlationId": "corr-789",
    "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    "tracestate": "vendor=value"
  },
  "target": {
    "capability": "CONSULTAR_LANCAMENTO",
    "operation": "CONSULTAR"
  },
  "payload": {
    "canonicalData": {
      "accountRef": "account-ref-opaque",
      "entryRef": "entry-ref-opaque"
    }
  },
  "executionPolicy": {
    "timeout": "PT5S",
    "retryPolicyRef": "RETRY_IDEMPOTENT_READ@1.0.0",
    "resiliencePolicyRef": "DEFAULT_CRITICAL_DEPENDENCY@1.0.0"
  },
  "callbackRef": "CALLBACK_ORIGINADOR_ASSISTIDO@1.0.0"
}
```

O exemplo demonstra forma e separação de responsabilidades. Não cria taxonomia oficial, endpoint ou modelo de dados bancário.

## 7. Modelo determinístico de execução

```text
CanonicalExecutionRequest
        ↓ validação estrutural, identidade e autorização
Route Resolver
        ↓ seleção explicável
Route Definition + versão exata
        ↓ compilação/expansão determinística
Execution Plan
        ↓
Step 1 → Adapter → Mock Endpoint / Legado real
        ↓
Step 2 → Adapter → Mock Endpoint / Legado real
        ↓
       ...
        ↓
CanonicalExecutionResult
        ↓
Audit / Trace / Context Reference
```

### 7.1 Route Resolver

O Route Resolver deve usar referências, critérios e prioridades publicados. Deve rejeitar ausência, incompatibilidade ou ambiguidade não governada. Não pode selecionar por ordem acidental de consulta, descoberta oportunista de endpoints ou inferência probabilística durante a execução.

Sua saída deve incluir a rota e versão exata, os candidatos relevantes, os critérios aplicados e o motivo normalizado da seleção ou rejeição.

### 7.2 Route Definition e Execution Plan

A Route Definition é imutável quando publicada. O Execution Plan é a materialização daquela definição para uma execução específica, com:

- versões exatas de rota, steps, adapters, contratos e políticas;
- dependências e ordem de execução;
- entradas e saídas esperadas de cada step;
- condições técnicas declaradas;
- classificação de idempotência;
- timeouts e políticas de resiliência efetivas;
- tratamento de erro, espera externa e compensação delegada;
- callback ou resultado terminal aplicável.

O plano pode conter sequência, paralelismo e espera assíncrona quando explicitamente representados. Não pode criar passos, decisões ou desvios não previstos na versão publicada.

### 7.3 Steps

Cada step deve declarar identidade, capacidade, operação, contratos de entrada e saída, dependências, binding do Adapter, política técnica e possíveis estados. A saída de um step somente alimenta outro por mapeamento explícito e validado.

Uma decisão de negócio retornada pelo destino pode orientar uma transição já definida na rota, mas a Engine não produz nem modifica essa decisão.

## 8. Contrato universal Engine ↔ Adapter

A comunicação entre Engine e Adapter deve obedecer a uma porta universal e tecnologicamente neutra. A Engine conhece a operação canônica, seus dados mínimos, metadados técnicos e taxonomia de resultado; não conhece endpoint, fila, tópico, WSDL, layout de arquivo, driver, framing ou protocolo proprietário.

```text
Engine
  ↓ contrato universal
Adapter
  ├── REST/HTTP
  ├── SOAP/XML
  ├── MQ, fila, tópico ou barramento
  ├── arquivo ou batch
  ├── gRPC
  └── tecnologia proprietária
```

O contrato interno deve permitir, no mínimo:

- receber identidade de execução, correlação e contexto de trace;
- receber capacidade, operação, dados canônicos e políticas efetivas;
- devolver resultado canônico, erro normalizado e referências de evidência;
- representar conclusão imediata, aceitação assíncrona e espera externa;
- declarar semântica de idempotência e repetição segura;
- preservar detalhes externos somente como evidência protegida e observável, sem acoplá-los ao fluxo da Engine.

Uma troca de implementação atrás do Adapter não pode mudar o significado da porta canônica.

## 9. Estratégia Mock-first e integração final

Nesta fase, todos os Adapters devem apontar **somente para Mock Endpoints, stubs ou simuladores contratuais controlados**. Nenhum legado real deve ser conectado antes da fase final.

Mocks devem permitir testar sucesso, erro técnico, resultado de negócio negativo, latência, timeout, indisponibilidade, resposta inválida, repetição idempotente, execução assíncrona e callback. Eles devem obedecer aos mesmos contratos de conformidade exigidos futuramente dos Adapters ligados a destinos reais.

Na fase final, cada integração real exigirá análise de segurança, rede, contrato, dados, operação, resiliência e observabilidade. A substituição:

```text
Adapter → Mock Endpoint
```

por:

```text
Adapter → Legado real
```

**não pode exigir alteração da Engine nem do Contrato Canônico**. Diferenças de REST, SOAP, MQ, arquivo, gRPC ou tecnologia proprietária ficam isoladas no Adapter e em configurações governadas de ambiente.

## 10. CanonicalExecutionResult

Toda execução deve produzir um resultado canônico, inclusive quando rejeitada antes da chamada externa.

```text
CanonicalExecutionResult
│
├── contract
│   ├── schemaVersion
│   └── contractVersion
├── execution
│   ├── executionId
│   ├── state
│   ├── startedAt
│   └── completedAt
├── contextRef
│   └── contextId
├── trace
│   └── correlationId
├── resolution
│   ├── routeId
│   └── routeVersion
├── outcome
│   ├── technicalStatus
│   ├── businessOutcome
│   └── canonicalData
├── errors[]
├── callback
│   ├── callbackRef
│   └── deliveryState
└── evidenceRefs[]
```

`technicalStatus` descreve a execução do Spider. `businessOutcome` transporta, sem reinterpretar, um resultado emitido pelo domínio responsável. Um resultado de negócio negativo não é automaticamente falha técnica. `canonicalData` de saída também deve ser mínimo e validado por schema.

## 11. Estados de execução e de steps

O ciclo técnico mínimo da execução é:

```text
RECEIVED → VALIDATED → RESOLVED → PLANNED → RUNNING → SUCCEEDED
    │          │           │          │          ├──► PARTIALLY_SUCCEEDED
    │          │           │          │          ├──► WAITING_EXTERNAL
    │          │           │          │          ├──► FAILED
    │          │           │          │          └──► COMPENSATING
    └──────────┴───────────┴──────────┴──────────────► REJECTED

COMPENSATING → COMPENSATED | FAILED
WAITING_EXTERNAL → RUNNING | SUCCEEDED | FAILED | TIMED_OUT
```

Cada step deve possuir estados próprios, no mínimo `PENDING`, `READY`, `RUNNING`, `WAITING_EXTERNAL`, `SUCCEEDED`, `FAILED`, `SKIPPED`, `TIMED_OUT` e, quando aplicável, `COMPENSATED`.

Transições devem ser válidas, atômicas no controle técnico e auditáveis. Retomada ou replay não pode apagar tentativas anteriores. Estados de negócio permanecem separados dos estados técnicos.

## 12. Identidade, correlação e W3C Trace Context

- `executionId` identifica uma instância de execução e nunca deve ser reutilizado para outra instância.
- `contextId` liga a execução à ocorrência contextual sem incorporar todo o Contexto ao envelope.
- `correlationId` relaciona interações pertencentes ao mesmo fluxo funcional e pode abranger múltiplas execuções.
- `traceparent` e `tracestate` seguem W3C Trace Context para propagação distribuída; spans novos preservam a relação causal.
- `interactionRef` liga o pedido à interação no canal ou originador.
- identificadores externos devem ser tratados como referências opacas e classificados.

Correlação funcional, identidade da execução e identidade de trace não são intercambiáveis. Logs, métricas, auditoria e traces devem permitir navegação entre elas sem expor dados sensíveis.

## 13. Idempotência

A idempotência deve possuir escopo, janela, proprietário e semântica explícitos. A chave deve ser avaliada em conjunto com originador, operação, versão compatível do contrato e, quando necessário, referências contextuais.

Para a mesma operação lógica válida:

- repetição não deve causar efeito duplicado;
- o Spider deve retornar o resultado já conhecido ou o estado corrente de forma consistente;
- payload incompatível sob a mesma chave deve gerar conflito explícito;
- tentativas e respostas reutilizadas devem permanecer auditáveis;
- retry automático somente é permitido quando o step e o destino suportarem repetição segura;
- a garantia efetiva do Adapter e do destino deve ser declarada, sem prometer exactly-once quando não puder ser demonstrado.

## 14. Versionamento e compatibilidade

`schemaVersion` identifica a estrutura validável; `contractVersion` identifica a semântica do contrato. Ambas devem ser verificadas antes da resolução.

Regras mínimas:

- contratos publicados são imutáveis;
- mudança incompatível exige nova versão principal;
- ampliação compatível exige versão menor e regras claras para campos desconhecidos;
- correção sem mudança observável pode usar versão de patch;
- campos obrigatórios não podem ser removidos ou mudar de significado de forma compatível;
- uma execução fixa todas as versões antes de iniciar steps;
- resultado, erro, callback e evidência registram a versão aplicável;
- compatibilidade Engine–Adapter deve ser verificada por testes de contrato;
- versões em execução permanecem reproduzíveis mesmo após depreciação.

## 15. Erros canônicos

Erros devem ser normalizados sem perder a causa externa permitida. Cada erro deve conter, no mínimo, código canônico, categoria, mensagem segura, origem, capacidade de retry, step relacionado, timestamp e referência protegida a detalhes técnicos.

| Categoria | Semântica |
|---|---|
| `VALIDATION` | Envelope ou dados incompatíveis com schema |
| `AUTHENTICATION` | Identidade não autenticada |
| `AUTHORIZATION` | Originador ou ator sem permissão |
| `RESOLUTION` | Rota ausente, ambígua ou incompatível |
| `CONTRACT` | Incompatibilidade de contrato interno ou externo |
| `TIMEOUT` | Limite temporal excedido |
| `UNAVAILABLE` | Destino ou dependência indisponível |
| `RATE_LIMITED` | Limite operacional excedido |
| `IDEMPOTENCY_CONFLICT` | Mesma chave associada a pedido incompatível |
| `BUSINESS_OUTCOME` | Resultado negativo emitido pelo domínio, não falha criada pela Engine |
| `INTERNAL` | Falha técnica não classificada, sem exposição indevida |

Erros externos devem ser mapeados no Adapter. Stack traces, secrets, topologia e payloads sensíveis não devem integrar mensagens públicas.

## 16. Callbacks e execução assíncrona

`callbackRef` aponta para uma definição governada contendo destino lógico, contrato, segurança, política de entrega e ambiente. O request não deve aceitar URL arbitrária como autoridade para saída de dados.

Callbacks devem:

- usar o `executionId`, `contextId` e `correlationId` originais;
- carregar versão de contrato e estado/resultados canônicos;
- possuir identidade própria de entrega e chave de idempotência;
- registrar tentativas, tempos, confirmações e falhas;
- aplicar retry somente conforme política publicada;
- autenticar o Spider e validar o destino;
- permitir consulta ou reconciliação quando a entrega permanecer inconclusiva.

Aceitação assíncrona não equivale a sucesso final. O estado `WAITING_EXTERNAL` deve explicitar a espera, o prazo e a forma autorizada de retomada.

## 17. Auditoria, trace e evidências

Cada execução deve produzir evidências suficientes para responder:

- quem ou qual sistema originou o pedido;
- qual contexto, intenção, capacidade, produto/serviço e jornada foram referenciados;
- qual rota, steps, adapters, contratos e políticas, com versões exatas, foram usados;
- quais critérios levaram à resolução;
- quais estados e transições ocorreram;
- quais tentativas, tempos, callbacks e interações externas aconteceram;
- qual resultado técnico e qual resultado de negócio delegado foram obtidos;
- quais erros normalizados ocorreram e se eram repetíveis;
- quais referências permitem localizar evidências externas autorizadas.

Auditoria não substitui logs, métricas ou traces. Evidências devem ser íntegras, temporalmente ordenáveis, protegidas contra alteração indevida e submetidas a controle de acesso, minimização, mascaramento e retenção. O Spider registra referências e fatos técnicos necessários, não um espelho do dado bancário.

## 18. Segurança e proteção de dados

- O envelope deve ser autenticado, autorizado e validado antes da resolução.
- Identidades de ator e delegação, quando necessárias, devem usar referências ou credenciais apropriadas, nunca dados improvisados em `canonicalData`.
- Secrets, tokens de acesso e endereços sensíveis não pertencem a contratos versionados em claro.
- O payload deve obedecer ao princípio do menor dado necessário.
- Logs, traces, auditoria e erros devem aplicar mascaramento e classificação.
- Callbacks e retomadas assíncronas devem prevenir falsificação, replay e desvio de destino.
- O Adapter deve aplicar o perfil de segurança exigido pelo destino sem expor detalhes à Engine.

## 19. Decisões arquiteturais consolidadas

1. O Contrato Canônico é envelope técnico universal com referências contextuais.
2. O Spider não replica dados mestres nem se torna System of Record.
3. `canonicalData` contém somente dados mínimos exigidos pela execução.
4. A cadeia completa é Contexto → Intenção → Capacidade → Produto/Serviço → Jornada → Contrato Canônico → Rota → Steps → Adapter → Mock/Legado.
5. A Engine recebe intenção técnica canônica e executa plano governado e determinístico.
6. A Engine não interpreta necessidade bancária nem executa regra de negócio.
7. Route Resolver e Execution Plan operam somente sobre definições publicadas e versões fixadas.
8. O contrato Engine–Adapter é universal e tecnologicamente neutro.
9. REST, SOAP, MQ, arquivo, gRPC e tecnologias proprietárias ficam atrás do Adapter.
10. Resultado técnico e resultado de negócio delegado permanecem separados.
11. Identidade, idempotência, estados, erros, callback e evidências são partes normativas do modelo de execução.
12. W3C Trace Context é o padrão de propagação de trace distribuído.
13. Nesta fase são permitidos somente Mock Endpoints, stubs e simuladores contratuais.
14. Legados reais somente serão integrados na fase final.
15. Trocar Mock por legado real não pode exigir mudança da Engine nem do Contrato Canônico.

## 20. Invariantes arquiteturais

1. Todo request aceito possui `executionId`, `contextId`, `correlationId` e versões de contrato válidas.
2. Toda execução fixa rota e dependências por versões exatas antes de executar steps.
3. Nenhum step chama diretamente um destino sem passar pela porta de Adapter governada.
4. Particularidades de protocolo ou contrato externo não atravessam a fronteira do Adapter.
5. Nenhum payload canônico vira cadastro mestre ou histórico bancário oficial no Spider.
6. Nenhuma política técnica cria, altera ou substitui decisão bancária.
7. Retry é proibido sem semântica de idempotência compatível.
8. A mesma chave idempotente não pode aceitar pedidos logicamente incompatíveis.
9. Toda transição de estado e tentativa permanece auditável.
10. Todo erro externo é normalizado pelo Adapter antes de chegar à Engine.
11. Todo callback usa referência governada e produz evidência de entrega.
12. Um resultado de negócio negativo não é automaticamente erro técnico.
13. Execução assíncrona mantém correlação, prazo e forma de retomada explícitos.
14. Mock e destino real devem passar pelos mesmos testes aplicáveis do contrato canônico.
15. Nenhum legado real é conectado antes da fase final.
16. A troca do destino atrás do Adapter não altera a Engine nem o Contrato Canônico.

## 21. Pontos ainda abertos

| Tema | Questão a decidir |
|---|---|
| Representação física | JSON Schema inicial e eventual suporte a Protobuf, Avro, XSD ou equivalentes |
| Catálogo de contratos | Repositório, resolução, assinatura, publicação e cache de schemas |
| Identificadores | Formato definitivo de IDs, geração, unicidade e exposição externa |
| Referências versionadas | Separação física entre código, versão e ambiente em `contextRef` |
| Canonical data | Convenções de tipos, extensões, referências e limites de tamanho |
| Operações | Taxonomia entre comando, consulta, evento e processo longo |
| Resultado | Schema definitivo de `CanonicalExecutionResult` e outcomes delegados |
| Erros | Códigos, mapeamentos, exposição segura e critérios de retry |
| Idempotência | Escopo por operação, janelas, armazenamento, concorrência e reconciliação |
| Roteamento | Linguagem de critérios, prioridades, empates e cache do Route Resolver |
| Plano de execução | Formato, paralelismo, join, condições, suspensão e retomada |
| Estados | Máquina de estados definitiva e regras de recuperação após falha |
| Processos longos | Persistência, timers, eventos, polling, expiração e intervenção operacional |
| Callbacks | Contrato de registro, autenticação, assinatura, retry e dead-letter |
| Compensação | Catálogo de capacidades compensatórias e limites de reversibilidade |
| W3C Trace Context | Política para entrada inválida, confiança entre zonas e baggage |
| Auditoria | Imutabilidade, retenção, acesso, não repúdio e vínculo com evidências externas |
| Segurança | Identidade delegada, autorização contextual, mTLS, assinatura e gestão de secrets |
| Testes de contrato | Harness, certificação de Adapters e critérios iguais para Mock e legado |
| Fase final | Inventário, priorização e critérios de aceite para integração de legados reais |

## 22. Critérios de aceite

O SPIDER-ARCH-003 é considerado apto a orientar a próxima etapa quando:

1. o envelope canônico é aceito como técnico, mínimo e baseado em referências;
2. a separação entre Contexto, Contrato Canônico, Rota, Engine e Adapter está inequívoca;
3. a estrutura mínima de `CanonicalExecutionRequest` está aprovada;
4. o fluxo determinístico e a fixação de versões estão aprovados;
5. resultado técnico, resultado de negócio delegado e erro estão separados;
6. requisitos de identidade, trace, idempotência, estados, callbacks e evidências são suficientes para detalhamento posterior;
7. a neutralidade tecnológica da porta Engine–Adapter está preservada;
8. a estratégia Mock-first e o adiamento de legados reais estão formalizados;
9. não há necessidade de alterar a Engine ou o Contrato Canônico ao trocar Mock por legado;
10. os pontos ainda abertos estão explicitamente registrados, sem implementação prematura.

## 23. Próxima etapa recomendada

Antes de alterar código, recomenda-se detalhar em artefatos arquiteturais subsequentes os schemas normativos de request, result e erro; o formato da Route Definition e do Execution Plan; a máquina de estados; e o protocolo universal Engine–Adapter.

Prompts de implementação devem continuar em documentos separados `SPIDER-PROMPT-NNN`, somente após a aprovação da sequência arquitetural aplicável. Este documento não autoriza implementação nem integração com sistemas reais.
