# SPIDER-ARCH-002 — Metamodelo Contextual

| Campo | Valor |
|---|---|
| Identificador | SPIDER-ARCH-002 |
| Título | Metamodelo Contextual |
| Status | Proposta arquitetural inicial |
| Predecessor | SPIDER-ARCH-001 — Baseline e Princípios Arquiteturais |
| Escopo | Definição conceitual, sem implementação |

## 1. Objetivo

Definir o metamodelo contextual do Spider, estabelecendo a semântica, as responsabilidades, as relações, as cardinalidades, o ciclo de vida, o versionamento e as invariantes da cadeia:

```text
Contexto → Intenção → Capacidade → Produto/Serviço → Jornada → Rota → Adapter → Legado
```

Este documento descreve o modelo lógico e sua governança. Não define tabelas, classes Java, endpoints, telas, linguagem de execução ou produto tecnológico.

## 2. Princípios do metamodelo

1. Cada elemento possui responsabilidade semântica própria.
2. Elementos conceituais não incorporam detalhes de transporte ou de fornecedor.
3. Resolução e execução são separadas: primeiro se determina o que deve ser atendido; depois, como executar.
4. Toda execução usa versões publicadas e imutáveis.
5. Alterações são feitas por criação de nova versão, nunca por mutação retroativa.
6. O Spider mantém definições técnicas e evidências, não dados bancários como System of Record.
7. Regras bancárias permanecem nos domínios responsáveis.
8. Inferência probabilística, quando existir, termina antes da resolução determinística.
9. Adapter e Legado pertencem à fronteira de integração, não ao núcleo semântico contextual.
10. Toda resolução deve ser explicável e rastreável.

## 3. Visão geral

```text
Situação-problema
       │
       ▼
   [Contexto]
       │ evidencia
       ▼
   [Intenção]
       │ requer
       ▼
  [Capacidade]
       │ é realizada por
       ▼
[Produto/Serviço]
       │ disponibiliza
       ▼
    [Jornada]
       │ é executada por
       ▼
      [Rota]
       │ invoca
       ▼
    [Adapter]
       │ integra
       ▼
     [Legado]
```

A cadeia não significa necessariamente uma relação linear um-para-um. Ela representa camadas de decisão. Relações muitos-para-muitos são permitidas quando explicitamente modeladas e governadas.

## 4. Vocabulário normativo

Os termos “deve”, “não deve” e “somente” expressam requisitos arquiteturais. “Pode” expressa uma possibilidade admitida. “Versão publicada” é uma versão aprovada e disponível para resolução no Data Plane.

## 5. Entidades do núcleo contextual

### 5.1 Contexto

Representa uma ocorrência concreta de uma situação-problema percebida por um ator ou canal. É dado de execução, não uma definição permanente do catálogo.

Responsabilidades:

- reunir fatos, atores, canal, instante, localidade lógica e circunstâncias relevantes;
- referenciar informações de negócio sem assumir sua propriedade;
- fornecer evidências para identificação de intenção;
- transportar consentimentos, restrições e atributos autorizados quando aplicável;
- preservar proveniência e nível de confiança dos sinais.

Atributos conceituais mínimos:

| Atributo | Significado |
|---|---|
| `contextId` | Identificador único da ocorrência |
| `schemaVersion` | Versão do contrato contextual de entrada |
| `occurredAt` | Instante associado à situação |
| `receivedAt` | Instante de recepção pelo Spider |
| `channel` | Canal ou classe de originador |
| `actorRefs` | Referências autorizadas aos atores envolvidos |
| `facts` | Fatos estruturados relevantes |
| `constraints` | Restrições declaradas para atendimento |
| `provenance` | Origem de fatos e sinais |
| `correlationId` | Correlação ponta a ponta |
| `idempotencyKey` | Identificação de repetição lógica, quando aplicável |

Invariantes:

- fatos devem obedecer a um schema conhecido;
- referências devem ser preferidas a cópias de dados mestres;
- dados sensíveis devem ser minimizados e classificados;
- contexto não contém uma rota técnica escolhida pelo canal;
- a ocorrência recebida deve permanecer auditável, com mascaramento adequado.

### 5.2 Intenção

Expressa o resultado que o ator pretende alcançar, independente de produto, jornada, canal ou tecnologia específica.

Exemplos conceituais: regularizar uma pendência, contratar uma solução adequada, compreender uma cobrança. Os nomes definitivos pertencem ao catálogo governado.

Atributos conceituais:

| Atributo | Significado |
|---|---|
| `intentCode` | Identificador semântico estável |
| `version` | Versão da definição |
| `name` | Nome legível |
| `description` | Resultado desejado e limites |
| `inputSchemaRef` | Fatos aceitos ou exigidos |
| `qualifiers` | Qualificadores permitidos para desambiguação |
| `requiredEvidence` | Evidências mínimas para resolução |
| `status` | Estado de governança da versão |

Invariantes:

- intenção descreve “o quê”, não “como”;
- não referencia endpoint, protocolo ou sistema;
- não embute política bancária decisória;
- códigos possuem significado estável; mudança semântica incompatível exige novo código ou versão principal;
- uma resolução de intenção deve registrar evidências e, se aplicável, confiança.

### 5.3 Capacidade

Representa uma habilidade de negócio ou operacional necessária para atender uma intenção. Deve ser estável em relação a produtos e tecnologias específicas.

Atributos conceituais:

| Atributo | Significado |
|---|---|
| `capabilityCode` | Identificador estável |
| `version` | Versão da definição |
| `name` | Nome da habilidade |
| `description` | Responsabilidade e fronteiras |
| `preconditions` | Condições técnicas ou contextuais declarativas |
| `outcomeSchemaRef` | Estrutura do resultado esperado |
| `classification` | Domínio e criticidade |
| `status` | Estado de governança |

Invariantes:

- capacidade não é endpoint, microserviço, tela ou aplicação;
- não deve conter implementação de regra bancária;
- pré-condições do Spider são de seleção ou execução técnica; decisões bancárias são delegadas ao domínio responsável;
- uma capacidade deve possuir ao menos uma realização publicada para ser elegível no Data Plane.

### 5.4 Produto/Serviço

Representa uma oferta ou serviço organizacional que realiza capacidades. É uma referência governada ao domínio responsável, não uma réplica do cadastro mestre de produtos.

Atributos conceituais:

| Atributo | Significado |
|---|---|
| `offeringCode` | Identificador estável da oferta ou serviço |
| `version` | Versão da definição contextual |
| `type` | Produto ou serviço |
| `name` | Nome legível |
| `ownerDomain` | Domínio responsável |
| `capabilityBindings` | Capacidades realizadas e condições de aplicação |
| `journeyRefs` | Jornadas publicadas disponíveis |
| `status` | Estado de governança |

Invariantes:

- a fonte oficial do produto ou serviço permanece fora do Spider;
- o vínculo com capacidade deve ser explícito e versionado;
- elegibilidade e aprovação bancárias não são calculadas pelo Spider;
- a definição contextual pode referenciar regras mantidas pelo domínio, sem copiá-las para a Engine.

### 5.5 Jornada

Define uma progressão de etapas e estados para atender uma intenção por meio de um produto ou serviço. É orientada ao resultado e permanece acima dos detalhes de transporte.

Atributos conceituais:

| Atributo | Significado |
|---|---|
| `journeyCode` | Identificador estável |
| `version` | Versão imutável |
| `name` | Nome legível |
| `supportedIntentRefs` | Intenções atendidas |
| `offeringRef` | Produto ou serviço associado |
| `stateModel` | Estados e transições permitidas |
| `stageDefinitions` | Etapas lógicas e resultados esperados |
| `entryCriteria` | Critérios declarativos de entrada |
| `terminalOutcomes` | Resultados finais possíveis |
| `routeBindings` | Rotas que materializam a jornada |
| `status` | Estado de governança |

Invariantes:

- toda jornada possui entrada, ao menos um estado terminal e transições válidas;
- etapas lógicas referenciam capacidades, não endpoints;
- estados técnicos e estados bancários não devem ser confundidos;
- transições baseadas em decisão de negócio dependem de resultado produzido pelo domínio responsável;
- uma jornada publicada deve apontar para ao menos uma rota publicada e compatível.

### 5.6 Rota

É a definição executável e determinística que materializa uma jornada. Contém o grafo técnico de passos, dependências e políticas operacionais permitidas.

Atributos conceituais:

| Atributo | Significado |
|---|---|
| `routeCode` | Identificador estável |
| `version` | Versão imutável |
| `journeyRef` | Jornada e versão materializadas |
| `inputContractRef` | Contrato de entrada da execução |
| `steps` | Passos e dependências do grafo |
| `technicalPolicies` | Timeout, retry, circuit breaker, rate limit e bulkhead |
| `failurePolicy` | Tratamento técnico de falha parcial |
| `compensationRefs` | Compensações técnicas ou comandos delegados |
| `outputContractRef` | Contrato de saída |
| `status` | Estado de governança |

Cada passo deve declarar, no mínimo, identificador, capacidade acionada, binding de adapter, contratos de entrada e saída, dependências, política de execução e classificação de idempotência.

Invariantes:

- uma rota publicada é validada, imutável e determinística;
- o grafo deve ser válido e não conter ciclos não declarados;
- todo passo invocável possui contrato e adapter compatíveis publicados;
- políticas técnicas não podem alterar a decisão de negócio retornada pelo domínio;
- retries são permitidos somente quando compatíveis com a semântica de idempotência;
- compensação não significa desfazer negócio localmente; deve acionar uma capacidade explícita do domínio responsável;
- a rota registra a versão exata de todas as dependências resolvidas.

## 6. Entidades da fronteira de integração

### 6.1 Adapter

Representa uma implementação controlada de uma porta canônica do Spider para uma tecnologia e contrato externo.

Atributos conceituais:

| Atributo | Significado |
|---|---|
| `adapterCode` | Identificador estável |
| `version` | Versão da implementação/contrato |
| `capabilityRef` | Capacidade que o adapter disponibiliza |
| `canonicalContractRef` | Contrato visto pela Engine |
| `externalContractRef` | Contrato do destino |
| `transportType` | REST, SOAP, mensageria, arquivo, dados, RPC ou outro |
| `mappingRef` | Traduções de entrada, saída e erro |
| `securityProfileRef` | Perfil de segurança aplicável |
| `operationalProfileRef` | Parâmetros e restrições operacionais |
| `targetRef` | Referência lógica ao sistema de destino |
| `status` | Estado de governança |

Invariantes:

- a Engine não conhece detalhes internos do adapter;
- secrets e endereços por ambiente não pertencem à definição versionada em claro;
- mapeamentos devem ser testáveis e versionados;
- erros externos são normalizados para taxonomia técnica canônica, preservando detalhe auditável permitido;
- um adapter declara limites de idempotência e garantias de entrega;
- adapters reais e simulados devem satisfazer testes de contrato equivalentes.

### 6.2 Legado ou sistema de destino

É uma referência lógica a um sistema externo ao núcleo do Spider. “Legado” não pressupõe tecnologia antiga; identifica o destino que mantém responsabilidade de domínio.

Atributos conceituais:

| Atributo | Significado |
|---|---|
| `targetCode` | Identificador lógico estável |
| `name` | Nome legível |
| `ownerDomain` | Domínio e responsável |
| `environmentBindings` | Referências de configuração por ambiente |
| `supportedTransports` | Tecnologias suportadas |
| `dataClassification` | Classes de dados manipuladas |
| `operationalConstraints` | Janelas, limites e requisitos conhecidos |
| `status` | Estado cadastral da referência |

O Spider não replica o modelo interno nem as regras do destino. Configurações sensíveis e topologia física pertencem à gestão segura de ambientes.

## 7. Entidades de apoio

### 7.1 Contrato

Define schema, semântica, compatibilidade e política de evolução para entrada, saída, evento ou erro. Pode ser expresso por OpenAPI, AsyncAPI, JSON Schema, Protobuf, XSD ou outra especificação adequada.

### 7.2 Política técnica

Define comportamento operacional permitido: timeout, retry, circuit breaker, bulkhead, rate limit, cache técnico, idempotência e tratamento de indisponibilidade. Não contém política bancária.

### 7.3 Evidência de resolução

Registra os fatos e critérios que levaram à seleção de intenção, capacidade, produto/serviço, jornada e rota. Deve permitir explicação sem expor raciocínio interno de modelos probabilísticos ou dados sensíveis indevidos.

### 7.4 Execução contextual

Representa uma instância da jornada no Data Plane. Referencia versões imutáveis, mantém estado técnico, correlação e resultados, mas não se torna o registro mestre da transação bancária.

## 8. Relações e cardinalidades

| Origem | Relação | Destino | Cardinalidade lógica |
|---|---|---|---|
| Contexto | evidencia | Intenção | uma ocorrência resulta em zero, uma ou mais candidatas; somente uma resolução ativa por objetivo |
| Intenção | requer | Capacidade | muitos para muitos, com requisitos obrigatórios ou opcionais |
| Capacidade | é realizada por | Produto/Serviço | muitos para muitos |
| Produto/Serviço | disponibiliza | Jornada | um para muitos |
| Jornada | atende | Intenção | muitos para muitos, explicitamente vinculada |
| Jornada | é materializada por | Rota | um para muitos por versão/ambiente/variante |
| Rota | contém | Passo | um para muitos, mínimo um |
| Passo | aciona | Capacidade | um principal; dependências devem ser explícitas |
| Passo | vincula | Adapter | um binding selecionado deterministicamente entre candidatos compatíveis |
| Adapter | integra | Sistema de destino | muitos adapters para um destino; um adapter aponta para um destino lógico |
| Definição | referencia | Contrato | um ou mais conforme o tipo |
| Execução | fixa | Versões publicadas | exatamente uma versão de cada definição efetivamente usada |

Múltiplas intenções independentes no mesmo contexto devem originar objetivos ou execuções correlacionadas, sem produzir uma rota híbrida implícita.

## 9. Resolução determinística

A resolução no Data Plane ocorre conceitualmente em fases:

```text
1. Validar contexto e autorização
2. Identificar ou receber intenção candidata
3. Validar evidências e confiança
4. Resolver capacidades requeridas
5. Localizar produtos/serviços compatíveis
6. Selecionar jornada publicada
7. Selecionar rota publicada e compatível
8. Resolver bindings de adapters por ambiente
9. Fixar todas as versões
10. Executar e registrar evidências
```

Critérios de seleção devem ser declarativos, versionados, ordenados e auditáveis. Empates não resolvidos não podem ser decididos por ordem acidental de banco de dados ou coleção. Devem gerar ambiguidade explícita ou aplicar uma prioridade governada.

A resolução deve produzir um registro contendo:

- candidatos considerados;
- critérios aplicados;
- itens descartados e motivo normalizado;
- seleção final;
- versões fixadas;
- nível de confiança, quando houver etapa probabilística;
- identificador da política de resolução.

## 10. Estados de governança

Cada versão de definição segue o ciclo mínimo:

```text
DRAFT → IN_REVIEW → APPROVED → PUBLISHED → DEPRECATED → RETIRED
  │          │            │
  └──────────┴────────────┴──► REJECTED, quando aplicável
```

| Estado | Uso permitido |
|---|---|
| `DRAFT` | Edição no Control Plane; não elegível para execução |
| `IN_REVIEW` | Validação e revisão; edição controlada |
| `APPROVED` | Aprovado, ainda não disponível ao Data Plane |
| `PUBLISHED` | Elegível para novas execuções dentro da vigência |
| `DEPRECATED` | Ainda utilizável durante transição, não preferencial |
| `RETIRED` | Não elegível para novas execuções; preservado para histórico |
| `REJECTED` | Reprovado; preservado para auditoria, não publicável sem novo ciclo |

Execuções em andamento conservam as versões fixadas, mesmo que estas sejam posteriormente deprecadas ou retiradas, salvo interrupção emergencial governada e auditada.

## 11. Versionamento e compatibilidade

### 11.1 Identidade e versão

Cada definição possui código estável e versão imutável. Recomenda-se versionamento semântico lógico:

- `major`: mudança incompatível de significado ou contrato;
- `minor`: ampliação compatível;
- `patch`: correção compatível sem mudança de semântica observável.

A forma física poderá diferir, desde que preserve ordenação e compatibilidade explícitas.

### 11.2 Regras

- versão publicada não é editada;
- dependências publicadas são referenciadas por versão ou faixa compatível governada;
- antes da execução, faixas são resolvidas para versões exatas;
- rollback publica ou reativa versão conhecida conforme processo auditado; não reescreve histórico;
- contratos devem declarar compatibilidade de consumidor e produtor;
- remoção ou mudança de campo obrigatório é incompatível;
- mudança de significado de código exige versão incompatível ou novo identificador;
- vigência temporal e ambientes elegíveis devem ser explícitos.

## 12. Invariantes transversais

1. Toda rota publicada referencia uma jornada publicada e compatível.
2. Toda jornada publicada referencia produto/serviço e intenção conhecidos.
3. Todo passo executável referencia uma capacidade e um binding de adapter válido.
4. Todo adapter publicado referencia contratos canônico e externo versionados.
5. Nenhuma definição publicada contém secret em claro.
6. Nenhuma resolução depende de ordenação implícita.
7. Nenhuma política técnica produz decisão bancária.
8. Nenhuma saída probabilística entra na Engine sem validação e confiança tratada.
9. Toda execução fixa versões e registra correlação.
10. Dados contextuais são minimizados, classificados e sujeitos a retenção.
11. Falha parcial é explícita; sucesso técnico não mascara falha de etapa.
12. Retry sem idempotência comprovada é proibido.
13. Compensação é uma capacidade explícita, não manipulação local de estado bancário.
14. Simuladores e adapters reais obedecem aos mesmos contratos canônicos aplicáveis.
15. Particularidades do destino ficam atrás do adapter.

## 13. Estados de execução

O estado técnico mínimo de uma execução contextual é:

```text
RECEIVED → VALIDATED → RESOLVED → RUNNING → SUCCEEDED
    │          │           │          ├──► PARTIALLY_SUCCEEDED
    │          │           │          ├──► FAILED
    │          │           │          ├──► WAITING_EXTERNAL
    │          │           │          └──► COMPENSATING → COMPENSATED | FAILED
    └──────────┴───────────┴──────────────► REJECTED
```

Estados técnicos descrevem a execução no Spider. Estados de negócio retornados pelos domínios devem ser transportados em campos ou contratos próprios e não convertidos implicitamente em estados técnicos.

## 14. Falhas e resultados canônicos

Falhas devem ser normalizadas, preservando causa externa autorizada:

| Classe | Exemplo conceitual |
|---|---|
| Validação | Contexto incompatível com schema |
| Autorização | Ator ou canal sem permissão |
| Resolução | Intenção ambígua ou rota inexistente |
| Contrato | Resposta externa incompatível |
| Disponibilidade | Timeout, conexão ou circuito aberto |
| Limite | Rate limit ou capacidade operacional excedida |
| Negócio delegado | Resultado de negócio recusado pelo domínio responsável |
| Interna | Erro técnico não classificado |

Um resultado de negócio negativo não deve ser rotulado automaticamente como falha técnica. A taxonomia detalhada será definida no contrato canônico de erros.

## 15. Data Plane e Control Plane no metamodelo

| Control Plane | Data Plane |
|---|---|
| Cria e edita drafts | Recebe contextos |
| Valida relações e contratos | Valida entradas |
| Executa testes de compatibilidade | Resolve somente versões publicadas |
| Aprova e publica versões | Fixa versões por execução |
| Depreca e retira definições | Executa rotas determinísticas |
| Mantém responsáveis e auditoria | Produz trace, métricas e auditoria |

O Data Plane não cria nem corrige definições durante uma execução. Ausência ou inconsistência de definição gera erro explícito e ação posterior no Control Plane.

## 16. Exemplo conceitual não normativo

```text
Contexto:
  cliente, em canal autorizado, relata necessidade de resolver uma cobrança

Intenção candidata:
  COMPREENDER_COBRANCA

Capacidades requeridas:
  CONSULTAR_LANCAMENTO
  EXPLICAR_COMPOSICAO_COBRANCA

Produto/Serviço:
  SERVICO_ATENDIMENTO_FINANCEIRO

Jornada:
  JORNADA_ESCLARECIMENTO_COBRANCA v2

Rota:
  ROTA_ESCLARECIMENTO_COBRANCA v2.1

Adapters:
  ADAPTER_CONSULTA_LANCAMENTO_MQ
  ADAPTER_DETALHE_COBRANCA_SOAP

Destinos:
  sistemas responsáveis pelos lançamentos e pela composição da cobrança
```

O exemplo demonstra que uma jornada pode usar tecnologias distintas sem expô-las ao modelo de intenção ou capacidade. Não estabelece taxonomia bancária oficial.

## 17. Validações obrigatórias antes da publicação

Uma versão candidata deve passar por:

- validação de schema;
- integridade referencial do grafo;
- detecção de ciclos inválidos;
- compatibilidade entre contratos;
- completude de bindings por ambiente elegível;
- verificação de idempotência e política de retry;
- testes de adapter contra simuladores contratuais;
- análise de classificação e minimização de dados;
- verificação de responsáveis e aprovações;
- simulação de sucesso, falha, timeout e resposta inválida;
- geração de representação explicável da resolução e execução.

## 18. Correspondência com a baseline atual

O estado atual deve ser interpretado como protótipo técnico:

| Baseline atual | Papel no metamodelo futuro |
|---|---|
| `ProductOrchestrateRequest` | Embrião de um contrato de contexto/execução, ainda não definitivo |
| `tb_product_routes` | Armazenamento inicial de rota, ainda sem todas as entidades e relações |
| `tb_audit_trace` | Embrião de evidência de execução e rastreabilidade |
| `OrchestrationService` | Embrião da Engine determinística |
| `LegacyPayloadTranslator` | Embrião de tradução que deverá pertencer à fronteira de adapter |
| WebClient e Resilience4j | Implementação atual de uma modalidade de integração e políticas técnicas |
| Mocks em 8081/8082/8091/8092 | Instrumentos de teste, sem valor normativo para o metamodelo |

Esta correspondência não autoriza refatoração. O desenho de implementação será tratado em artefato posterior.

## 19. Decisões ainda abertas

O metamodelo estabelece as fronteiras, mas mantém abertas decisões que exigem documentos específicos:

- taxonomia inicial de intenções e capacidades;
- formato definitivo do envelope contextual;
- linguagem de expressão de critérios e políticas técnicas;
- linguagem ou formato de jornadas e rotas;
- contrato canônico de comandos, consultas, eventos, resultados e erros;
- regra de composição quando um contexto contém múltiplos objetivos;
- estratégia de processos longos e persistência de estado;
- modelo de autorização contextual e delegação de identidade;
- arquitetura física do Control Plane e do Data Plane;
- modelo físico de persistência e migração da baseline atual;
- estratégia de publicação, cache, rollback e continuidade;
- padrão de testes de conformidade dos adapters.

## 20. Critérios de aceite do metamodelo

O SPIDER-ARCH-002 é considerado apto a orientar a próxima etapa quando:

1. as oito entidades principais possuem responsabilidade não sobreposta;
2. relações e cardinalidades são compreendidas e aceitas;
3. a separação entre regra bancária e política técnica está preservada;
4. a fronteira probabilística/determinística está explícita;
5. versionamento e estados de governança são suficientes para publicação segura;
6. invariantes impedem rotas inválidas e acoplamento tecnológico indevido;
7. a correspondência com a baseline não é confundida com desenho de implementação.

## 21. Próxima etapa recomendada

Antes de alterar código, recomenda-se criar:

> **SPIDER-ARCH-003 — Contrato Canônico e Modelo de Execução**

Esse documento deverá definir envelopes de contexto, comandos, consultas, eventos, resultados, erros, correlação, idempotência e compatibilidade, além da semântica de execução síncrona e assíncrona.

Somente após a sequência arquitetural necessária e sua aprovação deverão ser produzidos documentos `SPIDER-PROMPT-NNN` para orientar implementações no Cursor.
