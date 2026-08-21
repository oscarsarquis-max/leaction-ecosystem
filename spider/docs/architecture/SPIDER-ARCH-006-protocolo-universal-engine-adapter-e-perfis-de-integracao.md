# SPIDER-ARCH-006 — Protocolo Universal Engine–Adapter e Perfis de Integração

| Campo | Valor |
|---|---|
| Identificador | SPIDER-ARCH-006 |
| Título | Protocolo Universal Engine–Adapter e Perfis de Integração |
| Status | Proposta arquitetural inicial |
| Predecessor | SPIDER-ARCH-005 — Definição de Rotas, Execution Plan e Máquina de Estados |
| Escopo | Especificação lógica normativa, sem implementação |

## 1. Objetivo

Formalizar a porta universal entre a Engine determinística do Spider e seus Adapters, definindo o protocolo lógico de invocação, as capacidades declaradas, os resultados imediatos e assíncronos, a normalização de erros, a idempotência, a segurança, as evidências e os perfis de integração.

Este documento estabelece uma fronteira estável para que o núcleo do Spider se comunique com diferentes tecnologias e gerações de sistemas sem conhecer endpoint, protocolo, formato físico, mecanismo de autenticação ou produto de integração.

Nesta fase, todos os perfis e Adapters devem operar exclusivamente contra Mock Endpoints, stubs ou simuladores contratuais. Nenhum legado real é autorizado antes da fase final.

Este documento não escolhe framework de integração, service mesh, API gateway, broker, banco de dados, produto de secrets, linguagem de programação ou topologia de implantação. Também não define endpoints físicos nem autoriza alteração do código de produção.

## 2. Vocabulário normativo

Os termos “deve”, “não deve” e “somente” expressam requisitos arquiteturais. “Pode” expressa uma possibilidade admitida.

- **Porta Universal**: contrato lógico e tecnologicamente neutro consumido pela Engine para invocar capacidades externas.
- **Adapter**: componente responsável por implementar a Porta Universal e traduzir entre semântica canônica e contrato físico do destino.
- **Perfil de Integração**: conjunto governado de requisitos aplicáveis a uma modalidade tecnológica, sem expor essa modalidade à Engine.
- **Binding**: referência versionada que associa capacidade e operação canônicas a um Adapter e a uma configuração lógica de ambiente.
- **Interaction**: ocorrência individual de comunicação do Adapter com um destino.
- **Capability Declaration**: declaração verificável das operações, contratos, modos, limites e garantias suportados pelo Adapter.
- **Mock Endpoint**: destino controlado que emula o contrato e os comportamentos exigidos, sem representar referência arquitetural.

## 3. Decisão central

A Engine se comunica com qualquer destino exclusivamente por uma Porta Universal. A Porta Universal expressa intenção técnica canônica, identidade de execução, políticas efetivas e semântica de resultado; não expressa tecnologia de transporte.

```text
Engine determinística
       ↓ UniversalAdapterRequest
Porta Universal Engine–Adapter
       ↓
Adapter selecionado por binding publicado
       ├── Perfil REST/HTTP
       ├── Perfil SOAP/XML
       ├── Perfil Mensageria/Eventos
       ├── Perfil Arquivo/Batch
       ├── Perfil Dados Controlados
       └── Perfil Específico/Proprietário
       ↓ nesta fase
Mock Endpoint / Stub / Simulador contratual
       ↓ somente na fase final
Legado real certificado
```

Universalidade significa contrato uniforme para o núcleo, não imposição de uma tecnologia universal aos destinos. API é uma possibilidade entre várias e não constitui decisão fechada.

## 4. Fronteiras de responsabilidade

### 4.1 Engine

A Engine deve:

- validar o `Execution Plan` e o binding fixado;
- construir o request universal somente com dados autorizados;
- aplicar políticas de agendamento, budget, retry e estado;
- invocar o Adapter por uma interface estável;
- interpretar apenas resultados universais;
- persistir estados e evidências canônicas;
- impedir retry incompatível com idempotência;
- manter separado resultado técnico e outcome de negócio delegado.

A Engine não deve:

- conhecer URL, host, porta, fila, tópico, WSDL, layout, driver ou credencial;
- serializar o contrato físico do destino;
- interpretar código proprietário;
- implementar autenticação específica do legado;
- descobrir dinamicamente destinos fora do Control Plane;
- executar regra bancária ou alterar outcome delegado.

### 4.2 Adapter

O Adapter deve:

- implementar uma versão publicada da Porta Universal;
- validar compatibilidade do binding e dos contratos;
- traduzir payloads, metadados e resultados;
- encapsular transporte, serialização, autenticação técnica e configuração física;
- aplicar limites e garantias próprias declaradas;
- normalizar erros e estados externos;
- preservar correlação e trace quando suportados;
- produzir evidências técnicas protegidas;
- declarar conclusão, aceitação ou incerteza sem fabricar certeza.

O Adapter não deve:

- decidir rota, jornada, produto ou intenção;
- alterar políticas do `Execution Plan`;
- executar retry invisível fora da política efetiva;
- incorporar regra bancária;
- devolver detalhes físicos como dependência lógica da Engine;
- manter dados de negócio como System of Record.

### 4.3 Destino

O destino executa sua responsabilidade de negócio ou técnica. Nesta fase ele é sempre um simulador controlado. Na fase final, continuará responsável pela verdade de negócio, por suas transações e por seus outcomes.

## 5. UniversalAdapterRequest

### 5.1 Estrutura lógica

```text
UniversalAdapterRequest
├── protocol
│   ├── schemaVersion
│   └── protocolVersion
├── invocation
│   ├── invocationId
│   ├── executionId
│   ├── stepId
│   ├── attemptId
│   └── invokedAt
├── target
│   ├── capabilityCode
│   ├── operationCode
│   └── bindingRef
├── contracts
│   ├── inputContractRef
│   ├── outputContractRef
│   └── errorContractRef
├── trace
│   ├── correlationId
│   ├── traceparent
│   └── tracestate?
├── security
│   ├── callerIdentityRef
│   ├── delegationRef?
│   └── securityProfileRef
├── policy
│   ├── deadline
│   ├── timeout
│   ├── idempotency
│   └── resilienceProfileRef
├── payload
│   └── canonicalData
└── reply
    ├── acceptedModes[]
    └── callbackBindingRef?
```

### 5.2 Identidades

| Campo | Regra |
|---|---|
| `invocationId` | Identifica a invocação lógica do step e permanece estável quando a mesma invocação for reconciliada |
| `executionId` | Identidade da execução definida no SPIDER-ARCH-003 |
| `stepId` | Step materializado no `Execution Plan` |
| `attemptId` | Tentativa individual; muda a cada retry |
| `correlationId` | Correlação funcional ponta a ponta |

`attemptId` não substitui a chave idempotente. O Adapter deve ser capaz de distinguir nova tentativa técnica da mesma operação lógica.

### 5.3 Target e binding

`capabilityCode` e `operationCode` expressam a operação canônica. `bindingRef` aponta para definição publicada e fixada no plano. O request não contém endereço físico nem permite que a Engine selecione transporte.

### 5.4 Payload

`payload.canonicalData` deve obedecer ao schema de entrada da operação. O Adapter somente recebe o menor conjunto necessário. Dados adicionais exigidos por particularidade externa devem ser derivados de configuração governada ou de mapping publicado; não podem ser improvisados nem copiados indiscriminadamente do Contexto.

### 5.5 Deadline e timeout

`deadline` é o limite absoluto da invocação. `timeout` é um limite derivado que não pode ultrapassar o budget restante. O Adapter deve rejeitar invocação já expirada e não pode estender unilateralmente o prazo.

## 6. UniversalAdapterResult

### 6.1 Estrutura lógica

```text
UniversalAdapterResult
├── protocol
│   ├── schemaVersion
│   └── protocolVersion
├── invocation
│   ├── invocationId
│   ├── executionId
│   ├── stepId
│   ├── attemptId
│   ├── startedAt?
│   └── completedAt?
├── disposition
│   ├── mode
│   ├── state
│   └── certainty
├── outcome?
│   ├── technicalStatus
│   ├── businessOutcome?
│   └── canonicalData?
├── continuation?
│   ├── externalOperationRef
│   ├── waitSignalContractRef
│   ├── earliestCheckAt?
│   └── expiresAt
├── errors[]
├── evidenceRefs[]
└── trace
    ├── correlationId
    └── traceparent?
```

### 6.2 Modos de disposição

| `mode` | Semântica |
|---|---|
| `COMPLETED` | A interação terminou e o resultado pode concluir a tentativa |
| `ACCEPTED_ASYNC` | O destino aceitou processamento e forneceu referência de continuidade |
| `REJECTED` | A invocação não foi aceita pelo Adapter ou destino |
| `UNKNOWN` | Não é possível afirmar se o destino aceitou ou produziu efeito |

### 6.3 Estados universais

| Estado | Semântica |
|---|---|
| `SUCCEEDED` | Processamento técnico concluído e resposta válida |
| `BUSINESS_OUTCOME` | Processamento técnico concluído com outcome delegado, positivo ou negativo |
| `WAITING_EXTERNAL` | Conclusão depende de sinal ou consulta futura |
| `FAILED` | Falha técnica conhecida |
| `TIMED_OUT` | Prazo observado expirou |
| `CANCELLED` | Cancelamento confirmado pela garantia declarada |
| `UNKNOWN` | Estado externo inconclusivo |

### 6.4 Certeza

`certainty` deve ser um dos valores:

- `CONFIRMED`: existe evidência contratual suficiente do estado informado;
- `INFERRED`: estado derivado por regra governada, com limitação registrada;
- `UNKNOWN`: o Adapter não pode afirmar resultado ou ausência de efeito.

A Engine não pode converter `UNKNOWN` em falha seguramente repetível. Deve aplicar reconciliação ou tratamento terminal previsto na rota.

## 7. Capability Declaration

Cada Adapter deve publicar declaração versionada e assinável contendo:

```text
AdapterCapabilityDeclaration
├── adapterCode
├── adapterVersion
├── universalProtocolVersions[]
├── operations[]
│   ├── capabilityCode
│   ├── operationCode
│   ├── inputContractRefs[]
│   ├── outputContractRefs[]
│   ├── interactionModes[]
│   ├── idempotencyGuarantee
│   ├── cancellationGuarantee
│   ├── orderingGuarantee
│   └── limits
├── integrationProfileRef
├── securityProfileRefs[]
├── observabilityCapabilities
├── healthCapabilities
└── governance
```

### 7.1 Garantias declaradas

| Garantia | Valores iniciais |
|---|---|
| Idempotência | `NONE`, `KEY_DEDUPLICATED`, `NATURALLY_IDEMPOTENT`, `DESTINATION_MANAGED` |
| Cancelamento | `NOT_SUPPORTED`, `BEST_EFFORT`, `CONFIRMED` |
| Ordenação | `NONE`, `PER_KEY`, `TOTAL_WITHIN_BINDING` |
| Resposta | `IMMEDIATE`, `ASYNC_CALLBACK`, `ASYNC_POLL`, `BATCH_RESULT` |

Declarações são capacidades verificáveis, não promessas informais. O plano somente pode usar comportamento suportado pela combinação Adapter, binding, perfil e destino simulado certificado.

## 8. Adapter Binding

### 8.1 Estrutura lógica

```text
AdapterBinding
├── bindingCode
├── version
├── environment
├── adapterRef
├── capabilityOperationRefs[]
├── externalContractRef
├── integrationProfileRef
├── securityProfileRef
├── mappingRefs[]
├── errorMappingRef
├── endpointConfigurationRef
├── secretRefs[]
├── policyLimits
├── mockCertificationRef
└── status
```

### 8.2 Regras

1. O binding é publicado, versionado e imutável.
2. Configuração física é referenciada, segregada por ambiente e não incluída na rota.
3. Secrets são apenas referenciados e resolvidos no limite autorizado.
4. O mesmo contrato lógico pode possuir bindings para tecnologias diferentes.
5. Nesta fase, todo binding ativo deve conter certificação de Mock e impedir configuração de legado real.
6. Mudança de endpoint, credencial ou rede pode ser configuração governada sem mudar contrato semântico, desde que compatibilidade seja preservada.
7. Mudança de semântica, garantia ou mapping exige nova versão aplicável.

## 9. Ciclo universal de invocação

```text
1. Engine valida plan, step, binding e budget
2. Engine persiste Attempt e intenção de invocação
3. Porta valida versão e compatibilidade
4. Adapter resolve configuração e credencial autorizadas
5. Adapter traduz request canônico para contrato físico
6. Adapter executa uma External Interaction
7. Adapter valida e traduz resposta, aceitação ou falha
8. Adapter normaliza erro e produz evidências
9. Porta devolve UniversalAdapterResult
10. Engine persiste resultado e avança máquina de estados
```

O protocolo deve admitir mecanismos de consistência equivalentes a outbox/inbox quando necessários. A escolha física permanece em aberto, mas uma falha entre persistência e envio não pode produzir retry cego de operação com efeito.

## 10. Interação imediata

Uma interação imediata retorna `COMPLETED` ou `REJECTED` dentro do budget. Resposta tecnicamente recebida somente é sucesso após:

- validação de integridade e identidade do peer;
- desserialização segura;
- validação do contrato externo;
- mapping para contrato canônico;
- classificação do outcome e dos erros;
- preservação de evidência suficiente.

Código de transporte bem-sucedido não implica sucesso técnico ou de negócio. Código de transporte de erro não determina sozinho retryability.

## 11. Interação assíncrona

### 11.1 Aceitação

`ACCEPTED_ASYNC` deve fornecer `externalOperationRef`, contrato de sinal ou consulta, deadline e modo de continuidade. A aceitação não é sucesso final.

### 11.2 Callback

Callbacks devem usar binding governado, identidade verificável, contrato versionado, correlação, deduplicação e prevenção de replay. O Adapter normaliza o callback antes de entregá-lo à Engine como sinal de retomada.

### 11.3 Polling

Polling somente é permitido por política publicada, com intervalo, backoff, deadline, rate limit e operação idempotente de consulta. A Engine não conhece URL ou mecanismo; o Adapter executa a consulta conforme perfil.

### 11.4 Eventos e mensagens

Eventos devem possuir identidade, origem, tipo, versão, tempo, correlação e dados tipados. CloudEvents e AsyncAPI são referências candidatas quando aplicáveis, não obrigações universais.

### 11.5 Batch e arquivo

Processos batch podem retornar aceitação e produzir resultado posterior por arquivo, manifesto, evento ou consulta governada. A unidade de correlação, integridade e reprocessamento deve ser explícita.

## 12. Idempotência

O request universal deve transportar chave, escopo, owner e janela efetivos. O Adapter deve mapear a chave para a capacidade disponível sem enfraquecer silenciosamente a garantia.

Regras:

1. `NATURALLY_IDEMPOTENT` exige demonstração por semântica da operação.
2. `KEY_DEDUPLICATED` exige chave estável e tratamento de payload divergente.
3. `DESTINATION_MANAGED` exige evidência da garantia do destino.
4. `NONE` proíbe retry automático após envio possivelmente realizado.
5. Timeout ou perda de conexão após envio deve resultar em `UNKNOWN` quando não houver confirmação.
6. Deduplicação no Spider não prova ausência de duplicidade no destino.
7. Exactly-once não deve ser declarado sem garantia demonstrável ponta a ponta.

## 13. Retry e resiliência

O Adapter executa no máximo uma External Interaction por chamada universal, salvo quando o perfil declarar operações técnicas internas sem possibilidade de efeito duplicado e a política explicitamente permitir. Retry de negócio ou de invocação pertence à Engine e cria novo `attemptId`.

O Adapter deve informar:

- categoria e código normalizados;
- fase da falha: antes do envio, durante envio, após envio ou resposta;
- certeza sobre aceitação externa;
- retryability técnica;
- limites sugeridos pelo destino, quando seguros;
- evidência protegida da causa.

Circuit breaker, rate limit e bulkhead podem existir na Porta ou Adapter, mas seus estados e decisões devem ser observáveis e coerentes com as políticas fixadas no plano.

## 14. Normalização de erros

### 14.1 Pipeline

```text
Erro físico ou resposta externa
       ↓ classificação pelo perfil
ExternalErrorDescriptor protegido
       ↓ errorMappingRef versionado
CanonicalError
       ↓ UniversalAdapterResult
Engine e CanonicalExecutionResult
```

### 14.2 Regras

- erro externo nunca atravessa a Porta sem normalização;
- código físico pode ser preservado somente em evidência protegida;
- mensagem pública deve ser segura e estável;
- `retryable` considera fase, idempotência e semântica, mas não autoriza retry isoladamente;
- resultado de negócio negativo não deve ser transformado em indisponibilidade ou falha interna;
- resposta inválida é erro de contrato;
- autenticação e autorização do Adapter devem ser distinguíveis sem revelar secrets;
- erro desconhecido é normalizado como interno ou inconclusivo, nunca inventado como sucesso.

## 15. Segurança

### 15.1 Princípios

1. A Engine referencia identidade e perfil; não manipula credenciais específicas do destino.
2. O Adapter resolve secrets somente no instante e ambiente autorizados.
3. Credenciais não entram em rota, plano, payload, log ou evidência aberta.
4. Identidade técnica do Spider e identidade delegada do ator permanecem separadas.
5. Cada binding aplica menor privilégio por capacidade e operação.
6. Toda comunicação deve aplicar proteção de integridade, confidencialidade e autenticidade compatível com o perfil.
7. Callback, evento e arquivo devem prevenir falsificação, replay e troca de destino.
8. Certificados, chaves e secrets possuem rotação sem mudança do contrato canônico.

### 15.2 Zonas de confiança

O binding deve declarar zona de origem e destino, política de trace, classificação de dados e controles necessários. `traceparent` inválido ou vindo de zona não confiável deve ser rejeitado ou reiniciado conforme política, preservando evidência da decisão.

### 15.3 Minimização

Mappings devem impedir envio de campos não requeridos. Logs e traces não podem registrar payload integral por padrão. Evidências usam hashes, metadados e referências quando suficientes.

## 16. Evidências e observabilidade

Cada invocação deve permitir reconstruir:

- Adapter, binding, perfil, contratos e mappings com versões exatas;
- identities da execução, step, tentativa, invocação e interação;
- deadlines, políticas e garantias declaradas;
- instante de resolução de configuração e versão lógica utilizada;
- fase da interação, latência e tamanho, sem dados sensíveis indevidos;
- resultado, certainty, outcome e erro normalizado;
- trace distribuído e correlação funcional;
- sinais assíncronos, duplicidade e reconciliação.

Métricas mínimas incluem volume, latência, sucesso técnico, outcomes, falhas por categoria, timeouts, `UNKNOWN`, retries, circuit state, saturação, callbacks e idade de esperas. Métricas não devem usar identificadores sensíveis ou cardinalidade não controlada.

## 17. Saúde e prontidão

Saúde do Adapter, acesso à configuração, validade de credenciais e disponibilidade do destino são dimensões distintas.

- liveness informa se o componente pode operar;
- readiness informa se aceita novas invocações compatíveis;
- dependency health informa condição observada do destino;
- circuit state informa decisão de proteção local;
- certification state informa validade do contrato e do Mock nesta fase.

Falha de health check não deve ser confundida automaticamente com falha de todas as operações. A política de roteamento não pode descobrir destino alternativo fora dos bindings publicados.

## 18. Perfil REST/HTTP

O perfil REST/HTTP pode usar HTTP como transporte e REST quando a semântica do destino for compatível. Deve governar:

- método, URI template e headers em configuração do Adapter;
- códigos de status e mapping para resultado canônico;
- content type, compressão, limites e charset;
- autenticação, mTLS, assinatura e tokens;
- timeout de conexão, escrita, resposta e pool;
- propagação de trace permitida;
- idempotency key quando suportada;
- redirects, proxies e allowlists;
- callbacks e polling, quando aplicáveis.

HTTP 2xx não equivale automaticamente a sucesso; HTTP 4xx/5xx não define sozinho outcome ou retry. A Engine não recebe status HTTP como regra de fluxo.

## 19. Perfil SOAP/XML

O perfil SOAP/XML deve governar:

- WSDL, XSD, operação e versão;
- SOAP version, action e namespaces;
- canonicalização e validação XML;
- WS-Security, assinatura, criptografia e timestamps;
- faults e mapping para erro canônico;
- limites contra expansão de entidades e payload malicioso;
- correlação e padrões assíncronos aplicáveis.

Elementos SOAP permanecem no Adapter. A Engine não conhece WSDL, XPath, namespace ou SOAP Fault.

## 20. Perfil Mensageria e Eventos

O perfil deve governar:

- destino lógico, tipo de mensagem e contrato;
- producer/consumer identity;
- partition key, ordering e deduplicação;
- acknowledgement, redelivery e dead-letter;
- retenção, expiração e backpressure;
- schema registry ou resolução equivalente;
- correlação request–reply ou evento–execução;
- transactional outbox/inbox quando necessário;
- segurança, classificação e criptografia.

Publicação confirmada pelo broker não prova processamento pelo consumidor. Semântica at-least-once deve ser assumida quando garantia superior não for demonstrada.

## 21. Perfil Arquivo e Batch

O perfil deve governar:

- layout, encoding, delimitadores, tamanho e versionamento;
- manifesto, contagem, checksum e assinatura;
- nomenclatura lógica sem acoplar a rota a path físico;
- staging, publicação atômica e detecção de completude;
- janela, lote, item e correlação;
- rejeições parciais e arquivo de retorno;
- reprocessamento, deduplicação e retenção;
- canal seguro de transferência e permissões.

Presença de arquivo não prova completude sem manifesto ou protocolo equivalente. Reprocessamento não pode duplicar efeito por ausência de identidade de lote e item.

## 22. Perfil de Dados Controlados

Integração por dados somente é admitida quando explicitamente aprovada e isolada por Adapter. Deve governar:

- operação permitida, preferencialmente por interface estável e mínima;
- schema, owner e compatibilidade;
- credencial de menor privilégio;
- consistência, transação, locking e timeout;
- volume, paginação, streaming e backpressure;
- classificação, mascaramento e auditoria;
- proibição de acoplamento da Engine a tabela ou query física.

O Spider não se torna owner dos dados consultados. Acesso direto a banco de legado, quando excepcionalmente autorizado na fase final, exige análise específica e não constitui padrão preferencial.

## 23. Perfil Específico ou Proprietário

Protocolos proprietários devem ser encapsulados por Adapter dedicado e possuir especificação contratual suficiente para certificação. O perfil deve declarar framing, sessão, ordenação, limites, autenticação, erro, timeout, reconexão, idempotência e evidências.

Ausência de padrão público não autoriza vazamento de detalhes para a Engine. Quando não houver garantia verificável, o Adapter deve declarar limitação e `UNKNOWN` nos cenários inconclusivos.

## 24. Perfis futuros

Novos perfis, como gRPC, EDI, terminal emulado ou protocolo de mainframe, podem ser adicionados por versão governada. A inclusão não altera a Porta Universal se sua semântica já estiver coberta. Necessidade de novo conceito universal exige evolução explícita e compatível do protocolo, nunca campo livre.

## 25. Estratégia Mock-first

### 25.1 Regra

Antes da fase final, todo binding ativo aponta exclusivamente para simulador. Controles de ambiente devem impedir por configuração e autorização que um Adapter alcance legado real.

### 25.2 Matriz mínima de simulação

Cada perfil deve simular:

- sucesso imediato;
- outcome de negócio positivo e negativo;
- rejeição de contrato, autenticação e autorização;
- indisponibilidade antes do envio;
- conexão perdida durante o envio;
- timeout após possível aceitação;
- resposta inválida ou incompatível;
- latência e rate limit;
- idempotência e payload divergente;
- aceitação assíncrona, callback, polling ou retorno batch;
- callback duplicado, tardio, falsificado e ausente;
- cancelamento suportado, best effort e indisponível;
- falha de compensação;
- rotação de configuração e credencial;
- propagação e rejeição de trace.

### 25.3 Substituibilidade

A futura substituição:

```text
Adapter + Binding de ambiente → Mock Endpoint
```

por:

```text
Mesmo contrato de Adapter + Binding final certificado → Legado real
```

não pode exigir alteração da Engine, do Contrato Canônico, da Route Definition, do Execution Plan ou das máquinas de estado. Diferenças ficam no Adapter, nos mappings e na configuração governada, desde que a semântica e as garantias publicadas sejam preservadas.

## 26. Certificação de Adapter e binding

Um Adapter somente pode ser publicado após testes automatizáveis de:

1. compatibilidade com versões da Porta Universal;
2. declaração de capabilities e garantias;
3. validação de request e result;
4. mapping bidirecional por contrato;
5. normalização completa de erros;
6. idempotência e conflito de chave;
7. deadline, timeout e estado inconclusivo;
8. retry sem interação duplicada invisível;
9. fluxo assíncrono e deduplicação;
10. segurança, secrets, rotação e menor privilégio;
11. minimização de dados e mascaramento;
12. trace, métricas e evidências;
13. resiliência e limites;
14. conformidade do perfil tecnológico;
15. cenários Mock-first aplicáveis.

Na fase final, o mesmo harness deve ser executado contra o binding real, acrescido de testes de rede, segurança, operação, volume e recuperação acordados com o owner do legado.

## 27. Governança e ciclo de vida

Adapters, declarations, bindings, perfis, mappings e error mappings seguem ciclo versionado de `DRAFT → VALIDATED → APPROVED → PUBLISHED → DEPRECATED → RETIRED`.

- publicação exige segregação de funções e evidência de certificação;
- versões publicadas são imutáveis;
- depreciação não interrompe execução em andamento;
- retirada preserva reprodutibilidade e evidências;
- promoção entre ambientes não altera semântica;
- rollback ativa versão previamente certificada, sem editar a versão defeituosa;
- configuração emergencial é temporária, autorizada, auditada e limitada ao binding.

## 28. Compatibilidade e evolução

Mudanças compatíveis podem adicionar campo opcional, capability opcional ou novo perfil sem alterar semântica existente. Mudanças incompatíveis incluem:

- alterar significado de estado, mode ou certainty;
- enfraquecer garantia de idempotência ou cancelamento;
- mudar schema obrigatório;
- alterar classificação de outcome e erro;
- exigir detalhe de transporte na Engine;
- mudar identidade ou escopo de invocação;
- permitir comportamento invisível ao `Execution Plan`.

Mudança incompatível exige nova versão principal do protocolo e estratégia explícita de convivência.

## 29. Decisões arquiteturais consolidadas

1. A Engine utiliza uma única Porta Universal e tecnologicamente neutra.
2. Adapter traduz, integra e normaliza; não decide negócio ou rota.
3. Binding publicado associa operação canônica a Adapter e configuração de ambiente.
4. Endpoints, credenciais e detalhes físicos nunca entram na rota ou no payload canônico.
5. O protocolo representa conclusão, aceitação assíncrona, rejeição e incerteza.
6. Estado `UNKNOWN` é obrigatório quando o efeito externo não puder ser confirmado.
7. Capability Declaration torna garantias explícitas e testáveis.
8. Retry de invocação é coordenado pela Engine; interação invisível duplicada é proibida.
9. Erros externos são normalizados por mapping versionado.
10. Resultado de negócio delegado permanece separado de falha técnica.
11. Segurança específica do destino fica no Adapter e em perfis governados.
12. REST/HTTP, SOAP/XML, mensageria, arquivo, dados e protocolos específicos são perfis equivalentes perante o núcleo.
13. API é possibilidade, não premissa universal.
14. Evidências e observabilidade são obrigatórias em todos os perfis.
15. Nesta fase, todos os bindings apontam exclusivamente para Mocks, stubs ou simuladores.
16. Legados reais somente entram na fase final mediante certificação individual.
17. A troca de Mock por legado não altera Engine, contratos canônicos, rota, plano ou estados.

## 30. Invariantes arquiteturais

1. Nenhuma interação externa ocorre sem binding publicado e fixado no plano.
2. Nenhum Adapter recebe instrução de endpoint livre da Engine.
3. Toda invocação possui execution, step, attempt, invocation e correlation IDs.
4. Toda invocação possui deadline finito.
5. Todo payload é validado e minimizado.
6. Toda resposta externa é validada e normalizada.
7. Todo erro físico é isolado atrás do Adapter.
8. Todo outcome de negócio é preservado sem reinterpretação.
9. Toda garantia utilizada foi declarada e certificada.
10. Timeout após possível envio não é convertido em retry seguro sem evidência.
11. Adapter não executa retry invisível de operação com efeito.
12. Estado inconclusivo é representado como `UNKNOWN`.
13. Secrets nunca integram contratos, rotas, planos ou evidências abertas.
14. Trace inválido não é propagado automaticamente.
15. Particularidades do perfil não contaminam a Engine.
16. API não é requisito para integração universal.
17. Antes da fase final, todo destino externo é simulado.
18. Nenhum legado real é alcançável por binding desta fase.
19. Mock e legado real devem passar pelos mesmos testes contratuais aplicáveis.
20. Substituição do destino não altera o núcleo do Spider.

## 31. Pontos ainda abertos

| Tema | Questão a decidir |
|---|---|
| Representação física | Schemas JSON, Protobuf, Avro ou combinação para a Porta Universal |
| Runtime de Adapter | Processo interno, plugin, sidecar, serviço ou combinação governada |
| Discovery | Resolução de instância, cache e failover sem seleção oportunista |
| Configuração | Store, promoção, criptografia, refresh e rollback |
| Secrets | Produto, identidade de workload, rotação e auditoria |
| Certificados | PKI, mTLS, pinning, validade e automação |
| Mappings | Linguagem, compilação, testes e isolamento seguro |
| Error catalog | Códigos definitivos, owners e governança de mappings |
| Async | Envelope de sinal, callback, polling, eventos e reconciliação |
| Mensageria | Garantias, brokers, schema registry e dead-letter |
| Arquivo | Canal de transferência, manifestos e volumes máximos |
| Dados | Critérios excepcionais para acesso controlado e proibições definitivas |
| Observabilidade | Convenções de spans, métricas e correlação entre perfis |
| Health | Contrato de liveness, readiness, dependency e certification health |
| Harness | Implementação do kit de certificação multi-perfil |
| Ambientes | Barreiras técnicas que impossibilitem acesso a legados nesta fase |
| Fase final | Inventário, priorização, owners e plano de certificação de cada legado |

## 32. Critérios de aceite

O SPIDER-ARCH-006 é considerado apto a orientar a próxima etapa quando:

1. responsabilidades de Engine, Porta, Adapter, binding e destino estiverem inequívocas;
2. request e result universais cobrirem modos imediato, assíncrono e inconclusivo;
3. capability declarations e garantias estiverem definidas;
4. idempotência, retry e `UNKNOWN` estiverem formalizados;
5. normalização de erros e separação de outcome estiverem preservadas;
6. segurança, secrets, trace e evidências estiverem especificados logicamente;
7. perfis REST/HTTP, SOAP/XML, mensageria, arquivo, dados e específico estiverem isolados do núcleo;
8. API permanecer uma opção entre tecnologias admitidas;
9. certificação contratual puder ser automatizada;
10. bindings desta fase impedirem integração com legados reais;
11. substituibilidade Mock–legado estiver assegurada;
12. nenhuma decisão exigir implementação ou produto prematuros.

## 33. Próxima etapa recomendada

Antes de implementar, recomenda-se criar:

> **SPIDER-ARCH-007 — Control Plane, Governança, Publicação e Rollback**

Esse documento deverá formalizar catálogos, autoria, validação, aprovação, segregação de funções, promoção entre ambientes, publicação de artefatos imutáveis, ativação, depreciação, rollback, integridade, compatibilidade e distribuição segura ao Data Plane.

O Control Plane deverá governar metamodelo, contratos, schemas, rotas, políticas, Adapters, bindings, mappings e perfis sem permitir mudanças administrativas durante uma execução já materializada.

Prompts de implementação permanecem em documentos separados `SPIDER-PROMPT-NNN` e somente devem ser produzidos após a aprovação da sequência arquitetural aplicável. Legados reais continuam fora de escopo até a fase final.
