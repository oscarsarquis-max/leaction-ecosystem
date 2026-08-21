# SPIDER-ARCH-004 — Schemas Canônicos, Resultados e Erros

| Campo | Valor |
|---|---|
| Identificador | SPIDER-ARCH-004 |
| Título | Schemas Canônicos, Resultados e Erros |
| Status | Proposta arquitetural inicial |
| Predecessor | SPIDER-ARCH-003 — Contrato Canônico e Modelo de Execução |
| Escopo | Especificação lógica normativa, sem implementação |

## 1. Objetivo

Detalhar os schemas lógicos normativos do contrato canônico definido no SPIDER-ARCH-003. Este documento estabelece estruturas, obrigatoriedade, tipos, validações e compatibilidade para:

- `CanonicalExecutionRequest`;
- `CanonicalExecutionResult`;
- `CanonicalError`;
- resultados imediatos e assíncronos;
- callbacks;
- evidências e referências técnicas.

Este documento não escolhe biblioteca, framework, linguagem de programação, banco de dados ou produto de schema registry. Também não autoriza alteração do código de produção ou integração com legados reais.

## 2. Decisões de representação

1. JSON é a representação de referência inicial para documentação e testes de contrato.
2. JSON Schema Draft 2020-12 é a candidata inicial para validação dos envelopes JSON.
3. A semântica canônica é independente de serialização; formatos como Protobuf, Avro ou XML podem ser adicionados por perfil aprovado.
4. A forma serializada não altera a responsabilidade de nenhum campo.
5. Campos de extensão livres no núcleo são proibidos por padrão.
6. Novos campos compatíveis devem ser opcionais e possuir semântica documentada.
7. Dados ausentes não devem ser representados por valores vazios artificiais.
8. Datas e horas usam UTC e representação compatível com RFC 3339.
9. Durações usam representação compatível com ISO 8601.
10. Identificadores são strings opacas; consumidores não devem extrair significado de sua forma.

## 3. Envelope normativo de request

### 3.1 Estrutura

```text
CanonicalExecutionRequest
├── contract: ContractDescriptor
├── execution: ExecutionIdentity
├── contextRef: ContextReference
├── origin: OriginDescriptor
├── trace: TraceDescriptor
├── target: TargetDescriptor
├── payload: CanonicalPayload
├── executionPolicy: ExecutionPolicyReference
└── callbackRef: VersionedReference?
```

### 3.2 ContractDescriptor

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `schemaVersion` | string | Sim | Versão do schema que valida o envelope |
| `contractVersion` | string | Sim | Versão semântica do contrato canônico |

Os dois campos devem ser conhecidos e compatíveis com a versão da Engine antes de qualquer resolução de rota. Versão desconhecida ou incompatível produz `CONTRACT_UNSUPPORTED_VERSION`.

### 3.3 ExecutionIdentity

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `executionId` | string | Sim | Único e imutável para a instância |
| `timestamp` | date-time | Sim | Instante de criação do request em UTC |
| `idempotencyKey` | string | Condicional | Obrigatório para operações classificadas como idempotentes ou com efeito |

`executionId` não substitui `idempotencyKey`. Uma repetição lógica pode receber nova tentativa técnica, mas deve preservar a chave idempotente dentro do escopo governado.

### 3.4 ContextReference

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `contextId` | string | Sim | Ocorrência contextual de origem |
| `intentId` | string | Sim | Referência versionada à intenção resolvida |
| `capabilityId` | string | Sim | Referência versionada à capacidade principal |
| `productServiceId` | string | Sim | Referência versionada ao produto ou serviço |
| `journeyId` | string | Sim | Referência versionada à jornada selecionada |

As referências não carregam a definição completa. Antes da execução, devem resolver para versões publicadas, compatíveis e imutáveis.

### 3.5 OriginDescriptor

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `channel` | string | Sim | Valor pertencente a catálogo governado |
| `originatorId` | string | Sim | Identidade lógica autenticada do originador |
| `interactionRef` | string | Condicional | Referência opaca à interação de origem |

O envelope não deve confiar em `originatorId` apenas por estar presente. O valor deve ser coerente com a identidade autenticada e a autorização efetiva.

### 3.6 TraceDescriptor

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `correlationId` | string | Sim | Correlação funcional ponta a ponta |
| `traceparent` | string | Sim em fronteira distribuída | Sintaxe e semântica W3C Trace Context |
| `tracestate` | string | Não | Aceito somente quando válido e autorizado |

Contexto de trace inválido não deve ser propagado. A política de confiança entre zonas pode rejeitá-lo ou iniciar novo trace, preservando evidência da decisão.

### 3.7 TargetDescriptor

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `capability` | string | Sim | Código estável da capacidade técnica solicitada |
| `operation` | string | Sim | Operação publicada dentro da capacidade |

`target` não contém endpoint, protocolo, host, fila, tópico, WSDL, layout de arquivo ou nome físico de sistema.

### 3.8 CanonicalPayload

```text
payload
└── canonicalData: object | array | scalar | null
```

`canonicalData` é validado pelo schema de entrada da operação. O schema deve definir explicitamente:

- tipos e campos obrigatórios;
- limites de tamanho e cardinalidade;
- formatos e unidades;
- classificação de dados;
- campos sensíveis e regras de mascaramento;
- referências permitidas;
- compatibilidade entre versões.

O payload não pode ser usado como depósito de metadados técnicos já existentes no envelope nem como réplica indiscriminada do Contexto ou dos sistemas de registro.

### 3.9 ExecutionPolicyReference

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `timeout` | duration | Condicional | Não pode ampliar o máximo definido pela política governada |
| `retryPolicyRef` | string | Condicional | Referência versionada a política publicada |
| `resiliencePolicyRef` | string | Condicional | Referência versionada a política publicada |

Políticas inline são proibidas. Quando o originador omitir um valor opcional, a definição publicada determina o valor efetivo. O resultado deve registrar as políticas realmente usadas.

### 3.10 CallbackRef

`callbackRef` é uma referência versionada e governada. Não é URL livre. A definição referenciada deve conter contrato, identidade do destino, perfil de segurança, política de entrega e configuração por ambiente fora do payload.

## 4. Validação do request

A validação ocorre em camadas e falha de modo explícito:

```text
1. Limites de transporte e tamanho
2. Sintaxe e desserialização
3. Versão do envelope
4. Schema estrutural
5. Formatos e constraints
6. Identidade autenticada e origem
7. Autorização
8. Referências e versões publicadas
9. Schema de canonicalData
10. Idempotência
11. Compatibilidade de target, jornada e rota
```

Falha em uma camada não autoriza tentativa de execução parcial. A resposta deve ser segura e incluir correlação suficiente para suporte e auditoria.

## 5. Envelope normativo de resultado

### 5.1 Estrutura

```text
CanonicalExecutionResult
├── contract: ContractDescriptor
├── execution: ExecutionSummary
├── contextRef: ResultContextReference
├── trace: ResultTraceDescriptor
├── resolution: ResolutionSummary?
├── outcome: CanonicalOutcome?
├── errors: CanonicalError[]
├── callback: CallbackDeliverySummary?
└── evidenceRefs: EvidenceReference[]
```

### 5.2 ExecutionSummary

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `executionId` | string | Sim | Mesmo identificador aceito no request |
| `state` | enum | Sim | Estado técnico atual ou terminal |
| `startedAt` | date-time | Condicional | Presente quando a execução começou |
| `completedAt` | date-time | Condicional | Presente somente em estado terminal |
| `lastUpdatedAt` | date-time | Sim | Última transição persistida |

### 5.3 ResolutionSummary

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `routeId` | string | Após resolução | Identificador estável da rota |
| `routeVersion` | string | Após resolução | Versão exata fixada |
| `executionPlanRef` | string | Após planejamento | Referência protegida ao plano materializado |

O resultado não precisa expor publicamente candidatos e critérios completos. Esses dados devem permanecer acessíveis como evidência autorizada.

### 5.4 CanonicalOutcome

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `technicalStatus` | enum | Sim quando há outcome | `SUCCESS`, `PARTIAL`, `FAILURE`, `PENDING` ou `REJECTED` |
| `businessOutcome` | object | Condicional | Resultado delegado, tipado por schema e sem reinterpretação |
| `canonicalData` | qualquer tipo permitido pelo schema | Condicional | Dados mínimos de saída |

`technicalStatus` e `execution.state` devem ser coerentes. `businessOutcome` deve identificar seu tipo e versão de schema quando presente. Um resultado bancário negativo pode coexistir com `technicalStatus: SUCCESS` quando a chamada e o processamento técnico forem bem-sucedidos.

### 5.5 Regras do array errors

- `errors` é sempre um array, inclusive quando vazio;
- em `SUCCEEDED`, erros fatais são proibidos;
- warnings não devem ser modelados como falhas fatais;
- `FAILED`, `REJECTED` ou `TIMED_OUT` exigem ao menos um erro explicativo;
- múltiplos erros devem preservar ordem causal ou temporal por campos explícitos;
- detalhes sensíveis permanecem em evidência protegida, não no envelope público.

## 6. CanonicalError

### 6.1 Estrutura

```text
CanonicalError
├── errorId
├── code
├── category
├── severity
├── message
├── retryable
├── occurredAt
├── source
│   ├── component
│   ├── stepId?
│   ├── adapterId?
│   └── targetRef?
├── causeRef?
├── detailsRef?
└── fieldViolations[]?
```

### 6.2 Campos

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `errorId` | string | Sim | Identidade única desta ocorrência de erro |
| `code` | string | Sim | Código estável e documentado |
| `category` | enum | Sim | Categoria canônica governada |
| `severity` | enum | Sim | `INFO`, `WARNING`, `ERROR` ou `FATAL` |
| `message` | string | Sim | Mensagem segura, sem segredo ou detalhe interno indevido |
| `retryable` | boolean | Sim | Avaliação canônica para a ocorrência, não autorização isolada de retry |
| `occurredAt` | date-time | Sim | Instante observado pelo Spider |
| `source.component` | string | Sim | Componente lógico que normalizou o erro |
| `source.stepId` | string | Condicional | Step relacionado |
| `source.adapterId` | string | Condicional | Adapter relacionado |
| `source.targetRef` | string | Condicional | Destino lógico relacionado |
| `causeRef` | string | Condicional | Relação com erro causal anterior |
| `detailsRef` | string | Condicional | Referência protegida a evidência técnica |
| `fieldViolations` | array | Condicional | Violações seguras de campos do request |

`retryable: true` informa que a falha pode admitir nova tentativa. A Engine somente tenta novamente quando a política publicada, a idempotência e o orçamento de execução também permitirem.

### 6.3 Categorias iniciais

| Categoria | Prefixo sugerido | Exemplos |
|---|---|---|
| Validação | `VAL` | campo ausente, formato inválido, limite excedido |
| Autenticação | `AUTN` | credencial ausente ou inválida |
| Autorização | `AUTZ` | originador sem permissão |
| Resolução | `RES` | rota ausente ou ambígua |
| Contrato | `CON` | versão incompatível, resposta inválida |
| Idempotência | `IDEM` | chave reutilizada com conteúdo divergente |
| Timeout | `TIME` | deadline da execução ou step excedido |
| Disponibilidade | `UNAV` | conexão, circuito aberto ou dependência indisponível |
| Limite operacional | `RATE` | rate limit, bulkhead ou capacidade excedida |
| Negócio delegado | `BIZ` | outcome negativo devolvido pelo domínio |
| Interna | `INT` | erro técnico não classificado |

Códigos definitivos pertencem a catálogo versionado. Mensagens podem evoluir sem mudar o código, desde que a semântica permaneça estável.

## 7. Resultado imediato e aceitação assíncrona

### 7.1 Conclusão imediata

Quando a execução terminar dentro da interação, o resultado deve conter estado terminal, `completedAt`, outcome e erros aplicáveis.

### 7.2 Aceitação assíncrona

Quando a execução continuar após a interação inicial, o retorno deve informar:

- `executionId`;
- estado `RUNNING` ou `WAITING_EXTERNAL`;
- correlação;
- versão do contrato de acompanhamento;
- referência governada para consulta, quando disponível;
- expectativa de callback, quando configurada;
- prazo ou expiração aplicável, sem prometer tempo não garantido.

Aceitação significa que o pedido foi validado e assumido para processamento; não significa sucesso do negócio nem conclusão técnica.

## 8. Callback canônico

O callback transporta um `CanonicalExecutionResult` ou uma projeção versionada e explicitamente compatível. Deve incluir:

```text
CallbackDelivery
├── deliveryId
├── callbackRef
├── executionId
├── correlationId
├── attempt
├── idempotencyKey
├── dispatchedAt
└── result
```

Regras:

- `deliveryId` identifica uma tentativa de entrega;
- `idempotencyKey` identifica a notificação lógica e permanece estável entre retries;
- o consumidor deve poder deduplicar entregas;
- a política de callback define timeout, retry e destino de mensagens não entregues;
- toda tentativa gera evidência;
- callback não entregue não altera retrospectivamente o resultado da execução principal;
- falha definitiva de callback deve produzir estado operacional observável e possibilidade de reconciliação.

## 9. Evidências

`evidenceRefs` contém referências, não blobs arbitrários. Uma evidência deve declarar, em registro protegido:

| Campo | Semântica |
|---|---|
| `evidenceId` | Identidade única |
| `type` | Resolução, step, interação externa, callback, estado, erro ou segurança |
| `createdAt` | Instante de criação |
| `classification` | Classificação de acesso e sensibilidade |
| `integrity` | Mecanismo ou referência de integridade |
| `retentionPolicyRef` | Política governada de retenção |
| `subjectRefs` | Referências correlacionáveis permitidas |

O conteúdo de evidência deve ser minimizado e mascarado. A referência não concede acesso por si só; autorização é verificada no momento da consulta.

## 10. Invariantes entre request e result

1. `executionId`, `contextId` e `correlationId` permanecem estáveis.
2. O resultado declara versão de contrato compatível com a interação.
3. A rota e sua versão aparecem somente após resolução bem-sucedida.
4. Estado terminal exige `completedAt`.
5. Estado não terminal proíbe declaração enganosa de conclusão.
6. Falha terminal possui ao menos um `CanonicalError` fatal ou de erro.
7. `canonicalData` de saída obedece ao schema da operação e versão resolvida.
8. Resultado bancário é transportado como outcome delegado, não convertido arbitrariamente em estado técnico.
9. Erros externos são normalizados antes de compor o resultado.
10. Toda referência exposta é opaca e sujeita a autorização.

## 11. Compatibilidade e evolução

### 11.1 Mudanças compatíveis

Podem ser compatíveis, quando documentadas e testadas:

- adicionar campo opcional;
- adicionar novo código de erro que consumidores tratem por categoria;
- ampliar enum somente se consumidores aceitarem valores desconhecidos de forma segura;
- relaxar restrição sem alterar significado;
- adicionar nova representação de serialização por perfil.

### 11.2 Mudanças incompatíveis

Exigem versão principal:

- remover ou tornar obrigatório um campo antes opcional;
- alterar tipo, unidade, formato ou significado;
- reutilizar código de erro com nova semântica;
- mudar identidade ou escopo de idempotência;
- fundir estado técnico com estado de negócio;
- alterar regra de autorização ou exposição de dados de modo incompatível;
- modificar a semântica de sucesso, aceitação ou callback.

## 12. Testes de conformidade

Todo produtor ou consumidor do contrato canônico deve passar por testes automatizáveis de:

- exemplos válidos e inválidos por versão;
- campos obrigatórios, formatos, limites e valores desconhecidos;
- compatibilidade retroativa declarada;
- correlação e propagação de trace;
- deduplicação e conflito de idempotência;
- distinção entre falha técnica e outcome de negócio;
- mapeamento de erro externo para `CanonicalError`;
- estados terminais e não terminais;
- aceitação assíncrona, retomada e callback;
- minimização e não exposição de dados sensíveis;
- equivalência contratual entre Mock Endpoint e destino real.

Nesta fase, esses testes serão executados somente contra Mocks, stubs e simuladores. A mesma suíte aplicável deverá certificar cada integração real na fase final.

## 13. Decisões arquiteturais consolidadas

1. Os envelopes possuem núcleo fechado e versionado.
2. JSON e JSON Schema 2020-12 são referências iniciais, não dependências conceituais eternas.
3. `executionId`, `contextId` e `correlationId` têm papéis distintos e obrigatórios.
4. `canonicalData` é mínimo, tipado e validado por operação.
5. Políticas técnicas são referenciadas, nunca definidas livremente no request.
6. Callback usa referência governada, nunca URL arbitrária.
7. Resultado técnico e outcome de negócio delegado são independentes.
8. Todo erro possui código estável, categoria, origem, severidade e avaliação de retry.
9. `retryable` não substitui política de retry nem garantia de idempotência.
10. Evidências são expostas por referências autorizadas.
11. Aceitação assíncrona não equivale a conclusão.
12. Mock e legado devem cumprir o mesmo contrato aplicável.

## 14. Pontos ainda abertos

| Tema | Questão a decidir |
|---|---|
| Arquivos de schema | Organização física, IDs canônicos e resolução entre schemas |
| Registry | Produto, governança, assinatura, promoção e cache |
| IDs | UUID, ULID ou outro formato e regras de geração |
| Enums | Estratégia formal para evolução e valores desconhecidos |
| Business outcome | Envelope mínimo comum e schemas específicos por domínio |
| Paginação e streaming | Padrões para resultados grandes sem inflar `canonicalData` |
| Eventos | Envelope canônico e relação com CloudEvents ou AsyncAPI |
| Segurança de mensagem | Assinatura, criptografia seletiva e não repúdio |
| Callback | Confirmação, dead-letter, reconciliação e expiração definitivas |
| Evidências | Armazenamento, integridade, retenção e trilha de acesso |
| Catálogo de erros | Códigos definitivos, owners e tradução por Adapter |
| Status HTTP ou transporte | Mapeamento entre resultado canônico e cada modalidade de transporte |
| Baggage | Uso, limites, classificação e confiança no trace distribuído |

## 15. Critérios de aceite

O SPIDER-ARCH-004 é considerado apto a orientar a próxima etapa quando:

1. campos, tipos e obrigatoriedade dos envelopes estiverem aceitos;
2. validação em camadas e rejeição segura estiverem claras;
3. resultado imediato e aceitação assíncrona estiverem separados;
4. taxonomia estrutural de erros estiver aprovada;
5. callbacks forem governados, rastreáveis e idempotentes;
6. compatibilidade e mudanças incompatíveis estiverem definidas;
7. a suíte mínima de conformidade puder ser derivada deste documento;
8. nenhuma decisão exigir alteração prematura do código de produção.

## 16. Próxima etapa recomendada

Antes de implementar, recomenda-se criar:

> **SPIDER-ARCH-005 — Definição de Rotas, Execution Plan e Máquina de Estados**

Esse documento deverá formalizar o grafo executável, dependências, paralelismo, condições técnicas, estados de execução e steps, espera externa, retomada, falha parcial e compensação delegada.

Somente depois da sequência arquitetural aprovada devem ser produzidos schemas físicos e documentos `SPIDER-PROMPT-NNN` para implementação. Legados reais permanecem fora de escopo até a fase final.
