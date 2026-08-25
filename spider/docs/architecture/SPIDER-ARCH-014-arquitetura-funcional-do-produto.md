# SPIDER-ARCH-014 — Arquitetura Funcional do Produto

| Campo | Valor |
|---|---|
| Identificador | SPIDER-ARCH-014 |
| Título | Arquitetura Funcional do Produto |
| Natureza | Espelho documental vivo do Spider |
| Baseline funcional | Spider 0.16.0 — SPIDER-PROMPT-016 VERIFIED |
| Boundary ativo | MOCK_ONLY |
| Estado documental | BASELINE 016 — espelho sincronizado com CAP-016 (Operational Events) |
| Fontes autoritativas | SPIDER-ARCH-001–013, SPIDER-PROMPT-001–016, manifesto de capabilities, contrato anti-drift e roadmap 016–026 |

> **Razão da numeração:** o número `SPIDER-ARCH-005` já está ocupado por “Definição de Rotas, Execution Plan e Máquina de Estados”. Como a série existente prossegue até `SPIDER-ARCH-013`, este documento recebe o próximo identificador coerente: `SPIDER-ARCH-014`.

## 1. Propósito e papel deste documento

O Spider é uma plataforma de orquestração contextual que recebe uma intenção operacional de um canal ou produto, resolve de forma determinística uma rota governada, materializa um plano imutável, coordena interações com sistemas de destino por uma porta universal e devolve um resultado canônico, preservando estado, correlação, idempotência e evidências técnicas.

Este documento é o **espelho funcional do produto real**. Ele descreve o que o Spider efetivamente oferece no baseline 0.16.0, como suas capacidades colaboram, por quais superfícies são acessadas e como aparecem no produto. Não substitui especificações normativas detalhadas nem prompts de implementação; oferece a visão integrada que permite compreender o Spider como produto.

### 1.1 Público e linguagem

O documento se destina conjuntamente a:

- analistas de negócio bancário e responsáveis por jornadas/produtos;
- arquitetos, engenheiros, profissionais de segurança e operação;
- gestores, governança, risco, auditoria e demais interlocutores técnicos.

A linguagem adotada deve permitir leitura por um bom interlocutor de negócio sem perder precisão. Por isso:

- cada termo técnico relevante é ligado à finalidade funcional que resolve;
- nomes de classes, packages e tabelas só aparecem quando ajudam a localizar a implementação;
- siglas e expressões em inglês são explicadas no primeiro uso ou no glossário;
- capacidades planejadas são claramente separadas das capacidades disponíveis;
- diagramas mostram a jornada e as responsabilidades, não apenas componentes de software.

### 1.2 Leitura executiva: o Spider em uma jornada

Em linguagem de produto, o Spider funciona assim:

1. um canal ou produto solicita uma operação, informando o contexto e o resultado desejado;
2. o Spider verifica se a solicitação é válida, autorizada e se já foi processada;
3. escolhe uma rota previamente publicada e fixa o plano exato que será seguido;
4. executa, em ordem, as interações necessárias com simuladores de sistemas de destino;
5. se a resposta não for imediata, registra a espera e retoma do ponto correto quando chega um sinal confiável;
6. ao concluir, grava o resultado e, quando configurado, tenta comunicá-lo ao originador;
7. operadores autorizados podem acompanhar a jornada pelo Console, sem acessar segredos ou alterar a execução;
8. no escopo atual, todo esse percurso é demonstrado com mocks e simuladores — nenhum legado bancário real está conectado.

Para negócio, a proposta de valor é separar a jornada do canal das particularidades de cada sistema de destino, mantendo previsibilidade, rastreabilidade e evolução governada. O Spider coordena a interação; ele não toma a decisão bancária que pertence aos sistemas de negócio.

São objetivos permanentes deste artefato:

1. representar capacidades entregues sem confundi-las com arquitetura-alvo;
2. ligar experiência, funções, fluxos, módulos, interfaces e evidências;
3. manter visível a fronteira `MOCK_ONLY`;
4. registrar dependências e rastreabilidade entre prompts;
5. mostrar como cada evolução operacional significativa ganha representação visual progressiva na interface;
6. servir de ponto de sincronização a cada incremento verificado.

## 2. Regra de verdade e leitura de status

Este documento separa quatro categorias:

| Categoria | Significado neste documento |
|---|---|
| Atual e verificada | Entregue por SPIDER-PROMPT-001–016 e declarada VERIFIED no manifesto do baseline 0.16.0 |
| Atual, mas opt-in | Implementada, porém protegida por flag, modo, autorização ou profile; não se presume ativa |
| Preservada por compatibilidade | Existe no produto, mas não integra a jornada canônica principal |
| Planejada | Pertence ao roadmap 016–026; não é descrita como funcionalidade atual |

O estado oficial do baseline é:

- `productVersion = 0.16.0`;
- `currentPrompt = SPIDER-PROMPT-016`;
- `currentGroup = GROUP_A_VISIBILITY_OBSERVABILITY`;
- `activeBoundary = MOCK_ONLY`;
- 001–015 `VERIFIED`;
- 016–026 `PLANNED` no manifesto vigente;
- Console 015 `OFF_BY_DEFAULT`;
- integrações corporativas, sandbox corporativo, piloto real e produção não estão ativos.

Alterações de implementação do 016 ainda não verificadas não integram esta baseline. A seção 18 define como incorporá-las após o aceite formal.

## 3. Princípios funcionais do produto

### 3.1 Orquestração contextual sem regra bancária

O Spider decide **como executar uma interação governada**, não o resultado de negócio que pertence aos sistemas de domínio. A Engine valida, resolve, planeja, executa, espera, retoma, persiste e correlaciona. Regras bancárias, decisões de crédito, cadastro ou negócio não devem migrar para rotas, mappings, policies, console ou telemetria.

### 3.2 Determinismo e fixação

Uma execução usa referências e versões exatas. O plano materializado é imutável e possui integridade verificável. Em modo `CONTROL_PLANE`, a execução fixa também o snapshot governado, permitindo que submit, resume, callback e recovery usem o mesmo contexto histórico mesmo após ativações posteriores.

### 3.3 Comunicação universal não significa “uma API para tudo”

A universalidade está no contrato Engine–Adapter e na semântica canônica, não na imposição de REST/HTTP. HTTP é um perfil inbound opcional já implementado; os documentos arquiteturais admitem perfis futuros como SOAP/XML, mensageria/eventos, arquivo/batch, dados controlados ou protocolos proprietários. Nenhum desses perfis futuros é considerado implementado apenas por estar arquiteturalmente previsto.

### 3.4 Mock-first até a fase final

O produto atual usa mocks, adapters simulados, catálogos controlados e dados sintéticos. Destinos físicos reais, IdP corporativo, KMS/Vault/HSM, mTLS corporativo e legado real permanecem fora do boundary ativo. O primeiro binding corporativo só está planejado para o 025 e o primeiro legado real para o 026, condicionado a gates e aprovação formal.

### 3.5 Segurança fechada por padrão

Ingress canônico, signal ingress, console e operações sensíveis usam portas de autenticação/autorização com `DenyAll` por default. Modo local permissivo exige profile e flags explícitas. HMAC não substitui identidade nem autorização; AES at-rest não substitui KMS corporativo.

### 3.6 Observabilidade não controla a execução

Estado persistido é a fonte da execução. Timeline, projeções e futuros Operational Events observam o que aconteceu; não substituem a máquina de estados, não comandam a Engine e não constituem event sourcing.

### 3.7 Evolução com evidência visual progressiva

Capacidades operacionalmente relevantes devem deixar evidência compreensível no próprio produto quando isso for apropriado. A cadeia de governança é:

```text
Implementação → evidência operacional → representação visual → documentação ARCH → readiness de apresentação
```

Isso não exige uma tela artificial para cada classe ou endpoint. Exige que estados, eventos e consequências relevantes possam ser demonstrados com origem real, redaction, autorização e rótulo de boundary.

## 4. Atores e perfis funcionais

| Ator/perfil | Interesse funcional | Superfície atual | Restrições atuais |
|---|---|---|---|
| Canal ou produto originador | Solicitar uma execução e, opcionalmente, receber callback | Perfil HTTP canônico opt-in; endpoint legado preservado | Identidade do body não é autoridade; sem originador corporativo real |
| Sistema chamador de status | Consultar execução própria | Status query canônica opt-in | Ownership e authz; sem enumeração |
| Emissor de sinal externo | Concluir ou atualizar uma espera | Signal ingress HTTP opt-in ou porta interna | HMAC/replay/authz quando habilitados; no baseline, somente cenários Mock |
| Adapter de destino | Traduzir contrato universal para o destino | `UniversalAdapterPort` e resolvers de binding | Apenas bindings/adapters Mock ativos |
| Destino de callback | Receber resultado e responder a confirmação/status | Porta de entrega e porta de status query | Apenas adapters Mock; sem rede real |
| Operador | Observar execução, timeline, waits, callbacks e referências de governança | Console operacional opt-in | Read-only, DenyAll por default, redaction |
| Apresentador/demonstrador | Executar cenários controlados e mostrar evolução | Modo Apresentação e laboratório Mock do Console | `DEMONSTRAÇÃO MOCK`, preflight e profile local-demo |
| Governador/publicador | Registrar, validar, publicar e ativar artefatos governados | Use cases internos do Control Plane | Sem UI/admin HTTP; authz deny-by-default; modo STATIC é default |
| Revisor/auditor técnico | Conferir manifesto, readiness, integridade e rastreabilidade | Cockpit, documentos, manifesto e testes | Não recebe dados sensíveis nem controle operacional implícito |
| Worker/processador lógico | Processar outbox, reconciliação, expiry ou aplicação de sinal | Processors invocáveis | Sem scheduler/worker deployment durável no baseline 015 |

### 4.1 O que cada público deve conseguir responder

Após a leitura, um analista de negócio deve conseguir responder:

- qual jornada o Spider coordena e onde termina sua responsabilidade;
- como uma solicitação é protegida contra duplicidade;
- o que acontece quando um sistema não responde imediatamente;
- como o resultado retorna ao originador;
- o que pode ser acompanhado visualmente;
- quais integrações são simuladas e quando uma integração real poderá começar.

Um interlocutor técnico deve, adicionalmente, localizar:

- contratos, estados, portas e componentes responsáveis;
- fronteiras de segurança e persistência;
- dependências entre módulos;
- flags, interfaces e limitações do runtime;
- evidências e prompts que comprovam cada capacidade.

## 5. Capacidades funcionais atuais

### 5.1 Núcleo canônico e execução

- contratos canônicos versionados de request, result e erro;
- validação estrutural e semântica fechada;
- resolução determinística de rota publicada;
- materialização de Execution Plan imutável com digest;
- execução sequencial de até o limite configurado de steps;
- mappings fechados, sem scripts ou expressão arbitrária;
- attempts persistidos e retry governado por policy, safety, budget e deadline;
- estados canônicos de execução e step;
- resultado técnico separado de outcome de negócio;
- porta universal neutra a transporte, atendida hoje por Mock Adapter.

### 5.2 Persistência, idempotência e recuperação consultiva

- controle corrente, plano, transições, resultado e registros idempotentes;
- stores em memória por default e adapters JPA selecionáveis por configuração;
- chave idempotente armazenada por hash, não em claro;
- reuse de execução sem novo efeito externo;
- conflito determinístico por fingerprint divergente;
- histórico append-only de transições e attempts;
- consulta de execuções recuperáveis e verificação de integridade do plano;
- sem retomada automática universal ou scheduler distribuído no baseline.

### 5.3 Multi-step, espera e retomada

- fluxo linear de múltiplos steps;
- `WAITING_EXTERNAL` para aceite assíncrono ou resultado desconhecido;
- wait record persistente ligado a execution/step/attempt;
- Inbox para deduplicação de sinais;
- retomada idempotente do mesmo plano a partir do ponto de espera;
- tratamento de sinal duplicado, conflitante, tardio ou órfão;
- processor de expiração invocável, sem scheduler distribuído.

### 5.4 Callback, outbox e reconciliação

- callback definido e autorizado por referência governada;
- contexto de callback fixado para a execução;
- criação de outbox na terminalização sem alterar o outcome da execução;
- entrega por porta neutra a transporte usando Mock Callback Adapter;
- attempts, retry governado, lease, expiração, dead-letter e estado desconhecido;
- distinção entre dispatch, ACK técnico, aceite e confirmação;
- consulta Mock de status e reconciliação persistida;
- redelivery somente quando a safety e a policy permitem;
- operações internas de requeue/reconcile/recovery deny-by-default;
- sem callback HTTP ou mensageria real.

### 5.5 Integridade HMAC e prevenção de replay

- Integrity Profiles governados para callback, status query, signal e fingerprint sensível;
- HMAC-SHA-256 com canonicalização e separadores de domínio;
- key material por porta dedicada e provider Mock opt-in;
- rotação com versão ativa e allowlist de versões aceitas;
- Replay Guard com nonce/fingerprint protegidos por hash;
- decisões `RESERVED`, duplicata equivalente, conflito e prova expirada;
- HMAC como integridade e conhecimento de segredo, separado de authn/authz.

### 5.6 Control Plane e governança histórica

- artefatos tipados, lifecycle, validação, bundle, snapshot, publicação e ativação;
- separação `publicar ≠ ativar`;
- referências exatas, proibição de `latest`, digest e snapshot imutável;
- rollback por reativação de snapshot anterior;
- catálogos snapshot-backed para rotas, retry, wait, callback, integrity e bindings Mock;
- fixação de governança na execução em modo `CONTROL_PLANE`;
- carregamento do snapshot histórico em resume, signal, wait expiry, outbox, reconciliation e recovery;
- revogação in-flight com modo seguro antes do próximo efeito externo;
- `STATIC` e Control Plane desabilitado são os defaults;
- sem painel administrativo nem API HTTP de administração.

### 5.7 Signal ingress governado e durável

- definição governada do sinal e vínculo a wait/policy;
- lookup seguro de wait e contexto histórico fixado;
- pipeline ordenado de estrutura, contexto, integridade/replay, revogação, authz e Inbox;
- estado `APPLY_PENDING`, claim/lease e aplicação idempotente posterior quando o modo durável é ativado;
- fallback de compatibilidade para aplicação inline quando o modo durável está desativado;
- processor e recovery invocáveis;
- HTTP de signal opt-in;
- sem autenticação corporativa e sem scheduler.

### 5.8 Token opaco e envelope protegido

- continuation token aleatório e opaco, com fingerprint persistido;
- lookup por fingerprint sem scan;
- proteção do envelope verificado com AES-256-GCM, IV aleatório e AAD canônica;
- Data Protection Profile governado e resolução histórica;
- store protegido em memória ou JPA sem coluna plaintext;
- lifecycle de envelope, decrypt no processor e consumo seguro;
- rotação por versões aceitas, sem reencrypt automático;
- provider de chave Mock opt-in; sem KMS/Vault/HSM real;
- token e material criptográfico excluídos de logs, métricas e Console.

### 5.9 Console, cockpit e apresentação

- lista e detalhe de execuções canônicas persistidas;
- journey map derivado do plano e dos steps reais;
- timeline derivada de transitions, steps, attempts, waits e callback outbox;
- safe projections opt-in e redaction centralizada;
- cockpit de implementação derivado do manifesto, sem sequência hardcoded no React;
- Presentation Readiness com checks do boundary Mock;
- Modo Apresentação e laboratório de cenários canônicos Mock;
- polling cancelável e interrompido em estado terminal;
- evidências visuais desktop e mobile do 015;
- console e APIs do console off-by-default e protegidos por DenyAll.

## 6. Macrocomponentes funcionais

| Macrocomponente | Responsabilidade funcional | Fonte de verdade / saída | Dependências principais |
|---|---|---|---|
| Ingress e perfis de interface | Receber submit, status ou signal; autenticar, autorizar e normalizar | Request canônico ou decisão de rejeição | Contratos, authn/authz, Engine/Signal Ingress |
| Canonical Engine | Validar, resolver, planejar e coordenar a execução | Estado e resultado canônicos | Route/Policy catalogs, persistence, adapter binding |
| Route/Plan/State | Definir sequência e fixar o plano; controlar transições | Execution Plan e estados persistidos | Governança, integridade, clock/IDs |
| Universal Adapter Boundary | Isolar transporte/protocolo e normalizar resultado externo | Universal Adapter Result | Binding resolver e Mock Adapters atuais |
| Persistence/Idempotency | Guardar controle, histórico, attempts, resultado e deduplicação | Registros técnicos persistidos | Stores memory/JPA |
| Wait/Inbox/Resume | Suspender com segurança e retomar a mesma execução | Wait, Inbox e novas transições | Contexto histórico, Signal Ingress, Engine |
| Callback/Outbox/Reconciliation | Entregar e confirmar resultado sem contaminar outcome | Outbox, attempts e reconciliação | Contexto fixado, Mock delivery/status adapters |
| Security/Integrity/Data Protection | Proteger identidade, mensagem, replay, fingerprints e envelope | Decisões de segurança e ciphertext | Profiles governados e providers Mock opt-in |
| Control Plane | Governar artefatos e fornecer snapshots imutáveis | Snapshot ativo e fixation histórica | Stores de governança e autorização |
| Operational Read Model | Projetar estado persistido para consumo seguro | Summaries, detalhe, timeline e projections | Stores e redaction |
| Console/Cockpit/Presentation | Tornar execução e evolução do produto compreensíveis | UI operacional read-only e demo Mock | Console API, manifesto e readiness |
| Manifesto/Roadmap/Quality | Declarar capability status e impedir drift documental | Manifesto e contrato 015–026 | Testes, docs e Console cockpit |

## 7. Fluxos ponta a ponta

### 7.1 Orquestração canônica síncrona

```text
Originador autenticado
  → ingress opcional (HTTP é um perfil, não o núcleo)
  → CanonicalExecutionRequest
  → validação + authz + ownership/idempotência
  → resolução de rota publicada
  → materialização e persistência do Execution Plan
  → fixação do contexto governado quando CONTROL_PLANE
  → execução sequencial de step/attempt
  → UniversalAdapterPort
  → Mock Universal Adapter
  → normalização do resultado
  → persistência de transições/resultado
  → CanonicalExecutionResult
  → projeção segura no Console
```

Se uma chave idempotente já representar o mesmo request, o resultado ou estado existente é reutilizado sem nova chamada ao Adapter. Se o fingerprint divergir, a execução é rejeitada por conflito.

### 7.2 Retry e multi-step

```text
Step RUNNING → Attempt
  → resultado retryable?
  → policy + categoria/código + retry safety + budget + maxAttempts
     → sim: backoff limitado → novo Attempt
     → não: step terminal
  → sucesso: mapping fechado para o próximo step
  → falha terminal: steps restantes SKIPPED
```

Não há fork/join, DAG genérico, script, compensation automática ou regra de negócio no baseline.

### 7.3 Wait e resume

```text
Adapter retorna ACCEPTED_ASYNC ou UNKNOWN
  → cria Wait persistente
  → step e execução = WAITING_EXTERNAL
  → chega sinal autorizado
  → Inbox deduplica/reserva
  → wait é validada e claimada
  → attempt é concluído
  → Engine retoma os steps restantes do mesmo plano fixado
  → terminaliza ou cria nova espera
```

No modo governado, a retomada carrega a fixation e o snapshot histórico da execução; nunca migra silenciosamente para o snapshot atualmente ativo.

### 7.4 Callback e outbox

```text
Execução terminaliza
  → persiste resultado + Outbox lógica
  → processor invocável faz claim/lease
  → aplica assinatura quando configurada
  → Mock Callback Delivery Port
  → confirmed / accepted / retry / unknown / dead-letter / expired
  → se necessário, abre reconciliação
  → Mock Status Query
  → confirmação, nova espera, redelivery governado ou manual review
```

Falha, atraso ou incerteza do callback não altera o outcome da execução. `UNKNOWN` não vira sucesso por tempo e não provoca reenvio cego.

### 7.5 Signal ingress, HMAC e replay

```text
Peer autenticado + sinal
  → lookup seguro por continuation token/fingerprint ou compatibilidade configurada
  → contexto histórico do wait
  → validação estrutural e contratual
  → verificação HMAC pelo Integrity Profile histórico
  → Replay Guard
  → revocation check + authz
  → Inbox APPLY_PENDING
  → resposta de aceitação sem executar Adapter
  → processor posterior aplica o resume idempotente
```

O modo durável, token, protection e HTTP permanecem opt-in. Com durable desabilitado, o caminho de compatibilidade pode aplicar inline conforme as flags do baseline.

### 7.6 Token e envelope AES

```text
Continuation token opaco
  → fingerprint keyed para lookup
  → sinal verificado
  → serialização versionada do envelope
  → AES-256-GCM com AAD canônica
  → ciphertext persistido + Inbox
  → worker lógico faz claim
  → resolve Data Protection Profile histórico
  → decrypt
  → mapeia e retoma idempotentemente
  → envelope CONSUMED ou estado seguro de falha
```

Token puro, key bytes, IV, MAC e ciphertext não são expostos no Console. O provider atual é Mock e opt-in; não representa KMS corporativo.

### 7.7 Control Plane

```text
Artifact tipado DRAFT
  → validação estrutural/referencial/compatibilidade/segurança/operabilidade
  → VALIDATED
  → autorização e publicação → PUBLISHED
  → composição em bundle e snapshot imutável
  → ativação atômica por scope/sequence
  → catálogos snapshot-backed
  → nova execução fixa snapshot/bundle/digests
  → fluxos assíncronos recarregam esse contexto histórico
```

O Control Plane não participa de cada step e não possui superfície administrativa HTTP/UI no baseline. `STATIC` é o modo default.

### 7.8 Console e cockpit

```text
Persistência técnica ──→ Operational Query Service ──→ Console API ──→ UI
Manifesto classpath ───→ Implementation Use Case ────→ Cockpit
Flags + manifesto ─────→ Presentation Readiness ─────→ Modo Apresentação
```

A UI não inventa eventos nem lê JSON local para hardcodar a evolução. Execução e implementação são dimensões distintas. O laboratório de apresentação submete cenários canônicos Mock; não usa o endpoint legado como jornada principal.

## 8. Interfaces e superfícies do produto

### 8.1 Superfícies HTTP atuais

| Método e path | Função | Disponibilidade / boundary |
|---|---|---|
| `POST /v1/products/orchestrate` | Endpoint legado preservado | Compatibilidade; fora da jornada canônica do Console |
| `POST /v1/canonical/executions` | Submeter execução canônica | Flag opt-in; DenyAll por default; laboratório Mock no local-demo |
| `GET /v1/canonical/executions/{id}` | Consultar status próprio | Flags de HTTP + status query; ownership/authz |
| `POST /v1/canonical/signals` | Receber sinal externo | Flag opt-in; inline ou durable conforme configuração |
| `GET /v1/console/executions` | Listar execuções seguras | Console/HTTP opt-in; DenyAll por default |
| `GET /v1/console/executions/{id}` | Detalhe, journey e timeline | Read-only, redacted, no-enumeration |
| `GET /v1/console/implementation` | Cockpit de capabilities | Derivado do manifesto e flags redigidas |
| `GET /v1/console/presentation/readiness` | Preflight da demonstração | Boundary `MOCK_ONLY` explícito |

Paths existem como perfis controlados por configuração; a tabela não implica que estejam habilitados no runtime default.

### 8.2 Portas não HTTP

- `UniversalAdapterPort` para interação com destinos;
- `CallbackDeliveryPort` e `CallbackDeliveryStatusQueryPort`;
- portas de catálogo, binding, persistência e key material;
- portas de autenticação e autorização;
- processors invocáveis de expiry, outbox, reconciliation, signal application e recovery.

Essas portas preservam a neutralidade de protocolo. Uma implementação futura pode usar mensageria, SOAP, arquivo ou tecnologia proprietária sem alterar o contrato funcional do núcleo, desde que certificada.

### 8.3 Superfícies visuais

- Console de execuções;
- detalhe com journey map e timeline persistida/derivada;
- Cockpit de Implementação;
- Presentation Readiness;
- Modo Apresentação / laboratório Mock;
- evidências visuais versionadas em `docs/technical/screenshots`.

Não há no baseline UI de administração do Control Plane, workbench de requeue, dashboards de SLO ou Failure Lab.

## 9. Modelo de execução e correlação

### 9.1 Identidades funcionais

| Identidade | Escopo |
|---|---|
| `executionId` | Identidade estável da execução |
| `correlationId` | Correlação funcional entre a solicitação e seus acontecimentos |
| W3C `traceparent` / `tracestate` | Correlação técnica quando fornecida/propagada |
| route code/version | Rota exata resolvida |
| plan identity/digest | Plano imutável usado |
| stepId / attempt | Unidade e tentativa dentro da execução |
| wait / inbox record | Espera e sinal deduplicado |
| callback outbox / reconciliation | Entrega e confirmação do resultado |
| governance snapshot/fixation | Contexto governado histórico da execução |
| idempotency scope/key hash/fingerprint | Reuse e detecção de conflito sem chave em claro |
| continuation token fingerprint | Resolução segura de wait sem persistir token puro |

### 9.2 Regras de correlação

1. Uma execução fixa rota, plano e, quando aplicável, snapshot governado.
2. Steps, attempts, waits, Inbox, outbox e reconciliação pertencem inequivocamente à execução.
3. Resume e processadores assíncronos recuperam contexto pelo `executionId` e fixation histórica.
4. Reuse idempotente preserva o resultado/correlação histórica; uma projeção in-progress pode refletir a correlação do request atual sem alterar o controle persistido.
5. O Console apresenta apenas identificadores e projeções autorizados e redigidos.
6. A telemetria 016 deverá reutilizar essas identidades, sem criar uma segunda identidade concorrente.

### 9.3 Estados funcionais essenciais

O ciclo observado inclui recebimento, validação, resolução, planejamento, execução, espera externa e estados terminais como sucesso, falha, timeout ou rejeição. Steps possuem seus próprios estados e attempts append-only. O estado corrente e o histórico persistido governam a execução; elementos visuais são projeções.

## 10. Visibilidade operacional e representação visual progressiva

### 10.1 Estado visual entregue no 015

O Console 015 transforma dados reais do Data Plane em:

- lista filtrável de execuções;
- detalhe agregado;
- journey map do plano e steps;
- timeline ordenada por ocorrência e sequência;
- indicação de waits e callbacks;
- referências seguras de governança;
- cockpit de capabilities 001–026;
- readiness de demonstração;
- cenários Mock demonstráveis em desktop e mobile.

As fontes atuais da timeline são registros persistidos de transitions, steps, attempts, waits e callback outbox, com origem `PERSISTED` ou `DERIVED` explícita.

### 10.2 Política de evolução visual

Para cada incremento posterior:

1. identificar o acontecimento operacional que merece representação;
2. definir sua fonte autoritativa e semântica;
3. aplicar correlação, authz, redaction e limites de cardinalidade/exposição;
4. expor um read model seguro;
5. representar na UI apenas o que existe na fonte;
6. capturar evidência visual real da implementação;
7. atualizar manifesto, documentação e readiness sem antecipar status.

### 10.3 Operational Events no baseline 016

Com `SPIDER-PROMPT-016` VERIFIED, este documento registra:

- contrato `OperationalEvent` (`schemaVersion = 1`) com categorias e outcomes fechados;
- emissão fail-open via `OperationalEventPublisher` (engine, signal, callback);
- store memory/JPA (`tb_operational_event`) e consulta `GET /v1/console/executions/{id}/events`;
- metadata allowlist + redaction do console 015;
- seção **Operational Timeline** no Console (read-only), distinta da timeline projetada do estado;
- flag `spider.telemetry.enabled` (OFF_BY_DEFAULT);
- garantia testada de que falha de telemetria não altera a semântica da Engine.

Telemetria observa; não controla. Não há broker nem event sourcing neste baseline.

## 11. Limites de escopo atuais

### 11.1 Explicitamente dentro do baseline

- núcleo canônico, multi-step linear, retry e persistência;
- wait/resume, Inbox, signal ingress e modo durável opt-in;
- callback/outbox/reconciliation por adapters Mock;
- HMAC/replay e AES envelope com providers Mock opt-in;
- Control Plane e contexto histórico em modo opt-in;
- Console/cockpit/apresentação Mock read-only;
- endpoint legado preservado;
- memory/JPA conforme modos documentados;
- testes e manifesto do baseline 0.15.0.

### 11.2 Explicitamente fora do baseline

- legado real, binding real ou tráfego corporativo;
- IdP/OAuth/OIDC corporativo, mTLS corporativo e KMS/Vault/HSM;
- callback/status query em transporte real;
- broker, Kafka, RabbitMQ ou mensageria produtiva;
- scheduler e runtime de workers duráveis implantado;
- paralelismo/fork-join, DAG genérico ou compensation automática;
- WebSocket/SSE;
- operações administrativas via UI/API;
- SLOs, error budgets e dashboards operacionais implementados;
- Failure Lab, runbooks operacionais e fault injection visual;
- HA, multi-instância, DR e restore comprovados;
- SDK/certificação externa de Adapter;
- produção em qualquer ponto do roadmap 016–026.

### 11.3 Preservado, mas não promovido como jornada canônica

`POST /v1/products/orchestrate` continua disponível por compatibilidade e possui regressão protegida. Ele não foi migrado, não é usado pelo Modo Apresentação e não deve ser interpretado como Porta Universal nem como integração real.

## 12. Integrações simuladas e futuras integrações reais

| Classe | Estado no baseline | Exemplos |
|---|---|---|
| Mock de domínio/destino | Ativo/permitido | Mock Universal Adapter, cadastro/crédito simulados |
| Mock assíncrono | Ativo/permitido | callback delivery, status query, signals e cenários determinísticos |
| Mock de segurança | Opt-in/test/local-demo | HMAC key provider e AES key provider Mock |
| Infraestrutura simulada | Planejada para 019/020/022/024 | workers, backpressure, HA, DR, gates de piloto |
| Sandbox corporativo | Planejada apenas para 025 | IdP, mTLS, KMS e primeiro binding não produtivo |
| Piloto real | Planejado apenas para 026 | primeiro legado real com canary e rollback |
| Produção | Fora do roadmap atual | Não autorizada nem inferível |

A substituição de Mock por integração real deve ocorrer atrás das portas existentes, após certificação, inventário, segurança, rede, observabilidade, rollback e aprovação. Não deve exigir regra bancária na Engine nem tornar REST obrigatório.

## 13. Dependências funcionais entre módulos

```text
Contratos canônicos
  └─→ Engine + Route Resolution + Execution Plan
       ├─→ Persistência + Idempotência
       │    ├─→ Multi-step + Attempts + Retry
       │    ├─→ Wait + Inbox + Resume
       │    └─→ Operational Read Model
       ├─→ Universal Adapter Boundary → Mock Adapters
       ├─→ Callback Context → Outbox → Reconciliation
       └─→ Governance Fixation ← Control Plane Snapshot

Security/Authn/Authz ──→ todos os ingressos e operações sensíveis
Integrity/HMAC/Replay ─→ callback, status query, signal e fingerprints
Token/AES Protection ─→ signal ingress durável e protected envelope store

Operational Read Model + Manifest + Readiness
  └─→ Console / Cockpit / Presentation Mode
```

Regras críticas de dependência:

- o Console depende do estado persistido, mas a Engine não depende do Console;
- callback depende da terminalização, mas seu resultado não altera o outcome;
- resume depende do plano e contexto históricos, não do snapshot ativo atual;
- Control Plane governa novas resoluções, mas não participa de cada step;
- segurança e redaction atravessam todas as superfícies;
- adapters dependem da porta universal, e a porta universal não depende de HTTP;
- manifesto e contrato anti-drift governam o cockpit, sem governar a execução.

## 14. Mapa visual textual da arquitetura funcional

```text
┌──────────────────────────── ATORES E SUPERFÍCIES ────────────────────────────┐
│ Originador │ Emissor de sinal │ Operador │ Apresentador │ Governador         │
└──────┬──────────────┬──────────────┬──────────────┬──────────────┬────────────┘
       │              │              │              │              │
       ▼              ▼              ▼              ▼              ▼
┌────────────────────────── CAMADA DE INTERAÇÃO ───────────────────────────────┐
│ HTTP canônico opt-in │ Signal HTTP │ Console API │ UI/Cockpit │ Use cases CP │
│ Endpoint legado preservado (fora da jornada canônica principal)              │
└──────────────────────────────────┬────────────────────────────────────────────┘
                                   ▼
┌────────────────────────── NÚCLEO FUNCIONAL ──────────────────────────────────┐
│ Authn/Authz → Validação → Route Resolver → Execution Plan → State Machine    │
│                                      │                                       │
│                           Multi-step / Retry / Wait / Resume                  │
└──────────────────────┬───────────────┼───────────────────────┬───────────────┘
                       │               │                       │
                       ▼               ▼                       ▼
            ┌─────────────────┐ ┌──────────────────┐ ┌────────────────────────┐
            │ Porta Universal │ │ Persistência e   │ │ Callback / Outbox /    │
            │ + Mock Adapters │ │ Idempotência     │ │ Reconciliation Mock    │
            └─────────────────┘ └─────────┬────────┘ └────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
          ┌─────────────────┐  ┌──────────────────┐  ┌───────────────────────┐
          │ Wait / Inbox /  │  │ Control Plane +  │  │ HMAC / Replay / Token │
          │ Protected Env.  │  │ Historical Fix.  │  │ + AES Protection      │
          └─────────────────┘  └──────────────────┘  └───────────────────────┘
                    │                    │                    │
                    └────────────────────┼────────────────────┘
                                         ▼
┌──────────────────────── VISIBILIDADE DO PRODUTO ─────────────────────────────┐
│ Operational Read Model → Lista/Detalhe/Journey/Timeline                      │
│ Manifesto + contrato anti-drift → Cockpit de Implementação                   │
│ Readiness + cenários Mock → Modo Apresentação                                │
└───────────────────────────────────────────────────────────────────────────────┘

BOUNDARY ATIVO: MOCK_ONLY
REAL: somente planejado para sandbox 025 e piloto 026; PRODUÇÃO fora do roadmap.
```

## 15. Rastreabilidade entre capacidades e prompts 001–015

| Prompt | Capacidade entregue e verificada | Dependência funcional principal | Evidência/superfície |
|---|---|---|---|
| 001 | Fundação de contratos canônicos e Porta Universal Mock | Baseline legado preservado | Schemas, contratos e testes |
| 002 | Engine canônica mínima, rota, plano e estados | 001 | Fluxo interno e testes |
| 003 | Persistência, idempotência e recovery consultiva | 002 | Stores memory/JPA, migrations |
| 004 | Multi-step linear, attempts e retry | 003 | Steps/attempts persistidos |
| 005 | WAITING_EXTERNAL, Inbox, sinais e resume | 004 | Wait/Inbox e processor invocável |
| 006 | Perfil HTTP canônico opt-in e ownership | 005 | Endpoints canônicos protegidos |
| 007 | Callback governado e Outbox | 006 | Mock delivery e delivery summary |
| 008 | Confirmação e reconciliação de callback | 007 | Mock status query e recovery |
| 009 | HMAC, anti-replay e rotação | 008 | Integrity Profiles e Replay Guard |
| 010 | Control Plane, bundle, snapshot e ativação | 009 | Use cases internos e stores |
| 011 | Wiring JPA, catálogos snapshot-backed e fixation | 010 | Runtime CONTROL_PLANE opt-in |
| 012 | Governança histórica dos fluxos assíncronos | 011 | Loader histórico em resume/outbox/recovery |
| 013 | Signal ingress governado e aplicação durável | 012 | Inbox APPLY_PENDING e processor |
| 014 | Token opaco, envelope AES e HTTP durável | 013 | Protected store e continuation token |
| 015 | Console, cockpit e representação visual | 014 | UI, Console API, manifesto, readiness e screenshots |

Todos permanecem `MOCK_ONLY`. “VERIFIED” indica entrega/testes no baseline, não ativação automática nem prontidão para legado real.

## 16. Relação com 016–018

| Prompt | Papel no Grupo A | Relação com o baseline atual | Atualização esperada deste ARCH |
|---|---|---|---|
| 016 | Telemetria Canônica e Operational Events | VERIFIED no manifesto 0.16.0; OFF_BY_DEFAULT | Eventos reais, store, API console e Operational Timeline |
| 017 | Saúde, SLIs, SLOs provisórios e cockpit operacional | Depende do 016; PLANNED | Registrar SLIs/SLOs simulados, health e dashboards somente após implementação |
| 018 | Laboratório de Falhas e Jornadas Operacionais | Depende do 017; fecha o Grupo A | Registrar fault injection visual, evidências e runbooks Mock somente após implementação |

O 016 não deve alterar semântica da Engine. O 017 não deve transformar SLO provisório em compromisso produtivo. O 018 não deve conectar infraestrutura ou legado real.

## 17. Roadmap funcional 016–026

```text
Grupo A — Visibilidade e observabilidade
015 VERIFIED → 016 Telemetria → 017 Saúde/SLOs → 018 Failure Lab
                                                   │ gate
                                                   ▼
Grupo B — Operações de runtime
019 Workers duráveis → 020 Backpressure/resiliência → 021 Ops/workbench
                                                   │ gate
                                                   ▼
Grupo C — Prontidão de plataforma
022 HA/continuidade simulada → 023 SDK/certificação → 024 READY_FOR_PILOT
                                                   │ gate formal
                                                   ▼
Grupo D — Integração real
025 Fundações corporativas em sandbox → 026 primeiro legado real/piloto
```

Interpretação funcional:

- 016–018 completam observabilidade e demonstração operacional ainda em `MOCK_ONLY`;
- 019–021 introduzem runtime e operações, principalmente com infraestrutura simulada;
- 022–024 demonstram prontidão, certificação e continuidade antes de qualquer integração corporativa;
- 025 é o primeiro passo em `CORPORATE_SANDBOX`, não produção;
- 026 é `REAL_PILOT`, condicionado a aprovação, canary, reconciliação e rollback;
- nenhum prompt 016–026 autoriza produção.

## 18. Critérios de atualização contínua

### 18.1 Gatilhos obrigatórios

Atualizar este documento quando ocorrer qualquer um dos seguintes eventos:

- prompt passa a `VERIFIED`, `BLOCKED` ou `DEPRECATED`;
- capability, endpoint, flag, modo, ator ou superfície visual muda;
- novo store, processor, binding ou perfil altera o fluxo funcional;
- boundary de integração muda sob aprovação formal;
- manifesto/roadmap muda grupo, dependência, status ou objetivo;
- nova evidência visual se torna parte do aceite;
- uma limitação deixa de existir ou surge uma nova restrição material.

### 18.2 Gate de sincronização pós-prompt

Uma atualização só pode promover algo de “planejado” para “atual” após:

1. implementação concluída;
2. testes e regressões aprovados;
3. manifesto e contrato de roadmap coerentes;
4. documentação técnica do prompt gravada;
5. boundary e defaults confirmados;
6. Console/read model ajustados quando aplicável;
7. evidências visuais reais capturadas quando a capacidade tiver expressão operacional;
8. ausência de funcionalidades inventadas ou antecipadas do prompt seguinte.

### 18.3 Checklist específico para o fechamento do 016

- [ ] `SPIDER-PROMPT-016` marcado `VERIFIED` no manifesto oficial;
- [ ] versão/baseline e totais de testes atualizados;
- [ ] modelo de Operational Event documentado conforme código final;
- [ ] catálogo de tipos/produtores reais registrado;
- [ ] correlação e ordenação descritas;
- [ ] persistência, retenção, limites e cleanup efetivos descritos;
- [ ] endpoints/queries/flags reais adicionados à seção 8;
- [ ] timeline do Console atualizada sem eventos inventados;
- [ ] redaction, DenyAll e no-enumeration confirmados;
- [ ] falha de telemetria comprovadamente não altera outcome/estado da Engine;
- [ ] screenshots reais desktop/mobile referenciadas;
- [ ] 017 e 018 mantidos como planejados;
- [ ] boundary `MOCK_ONLY` preservado.

### 18.4 Controle de drift

Em cada revisão, comparar ao menos:

- `backend/src/main/resources/implementation/spider-capability-manifest.json`;
- `backend/src/main/resources/implementation/spider-roadmap-015-026-contract.json`;
- `docs/roadmap/SPIDER-ROADMAP-IMPLEMENTACAO-016-026.md`;
- `docs/technical/SPIDER-PROMPT-NNN-*.md` do incremento;
- endpoints/controllers, flags/configuração e migrations entregues;
- testes de contrato, E2E e frontend;
- screenshots oficiais da versão.

Se houver divergência, o documento deve declarar o drift e permanecer no último baseline verificado, em vez de inferir estado a partir de código incompleto.

## 19. Invariantes do espelho funcional

1. O documento descreve produto real, não desejo arquitetural.
2. Capability planejada nunca é escrita como disponível.
3. Flag off-by-default nunca é descrita como ativa por default.
4. Mock nunca é rotulado como integração real.
5. HTTP nunca é apresentado como única comunicação universal.
6. O endpoint legado é preservado, mas não confundido com a jornada canônica.
7. Estado persistido permanece fonte da execução.
8. Console e telemetria observam; não controlam a Engine.
9. Falha de callback não altera outcome da execução.
10. Resume usa plano e governança fixados historicamente.
11. Secrets, tokens, MACs, IVs, ciphertext e payloads sensíveis não aparecem na UI/documentação de evidência.
12. Evidência visual vem da implementação real e conserva o rótulo `MOCK_ONLY`.
13. Legado real só entra na fase final, após os gates 024/025 e aprovação do 026.
14. Produção está fora do roadmap 016–026.

## 20. Glossário funcional acessível

| Termo | Significado no Spider | Por que importa para negócio |
|---|---|---|
| Adapter | Componente que traduz a linguagem comum do Spider para o protocolo de um sistema de destino | Evita que cada canal precise conhecer as particularidades de cada sistema |
| Binding | Referência governada que associa uma função a uma implementação de Adapter | Permite trocar a forma de integração sem mudar a jornada funcional |
| Boundary `MOCK_ONLY` | Limite que autoriza apenas mocks e simuladores | Deixa explícito que a solução atual não toca legados reais |
| Callback | Comunicação do resultado para quem iniciou a operação | Permite concluir jornadas que não precisam manter a chamada original aberta |
| Contrato canônico | Estrutura comum usada para pedidos, resultados e erros | Dá uma linguagem estável entre canais, Spider e integrações |
| Control Plane | Conjunto de funções que valida, publica e ativa configurações governadas | Impede alterações informais ou parciais nas regras técnicas de execução |
| Correlação | Vínculo entre uma execução e todos os seus passos, esperas e comunicações | Permite reconstruir e explicar o que aconteceu ponta a ponta |
| Data Plane | Parte que executa as jornadas usando configurações já publicadas | Separa operação do dia a dia das mudanças administrativas |
| DenyAll | Configuração que nega acesso quando nenhuma autorização explícita foi concedida | Reduz risco de exposição ou operação acidental |
| Envelope protegido | Conteúdo de um sinal guardado de forma criptografada | Evita persistir informação sensível em texto legível |
| Execution Plan | Plano imutável com a rota e as versões exatas usadas na execução | Garante que uma jornada em andamento não mude silenciosamente |
| Fingerprint | Resumo criptográfico usado para comparar dados sem armazenar o valor sensível em claro | Ajuda a detectar duplicidade ou conflito com menor exposição de dados |
| HMAC | Prova criptográfica de integridade baseada em segredo compartilhado | Ajuda a detectar mensagem alterada ou forjada; não substitui identidade/autorização |
| Idempotência | Garantia de que repetir a mesma solicitação não gera o mesmo efeito duas vezes | Evita duplicidade operacional e financeira causada por reenvios |
| Inbox | Registro de sinais recebidos e deduplicados antes da aplicação | Evita que o mesmo retorno externo conclua a jornada mais de uma vez |
| Mock / simulador | Implementação controlada que imita um sistema externo | Permite desenvolver, testar e demonstrar sem acessar legado real |
| Operational Event | Registro observacional canônico de algo ocorrido na operação | Após o 016, deverá enriquecer a explicação visual sem controlar a execução |
| Outbox | Registro persistente de uma comunicação que precisa ser enviada | Evita perder a intenção de comunicar um resultado após a conclusão |
| Porta Universal | Contrato estável entre a Engine e qualquer Adapter | Preserva a neutralidade de protocolo; não obriga todas as integrações a usar API HTTP |
| Read model / projeção | Visão preparada para consulta, sem expor diretamente os dados internos | Torna o Console compreensível e seguro sem alterar a fonte da execução |
| Reconciliação | Verificação posterior usada quando não se sabe se uma comunicação foi concluída | Evita assumir sucesso ou repetir uma ação de forma arriscada |
| Redaction | Remoção ou mascaramento de informações sensíveis antes da exibição | Permite observabilidade sem revelar tokens, segredos ou conteúdo protegido |
| Replay | Reutilização indevida de uma mensagem válida já apresentada | A proteção anti-replay reduz duplicidades e ataques por repetição |
| Retry | Nova tentativa controlada após uma falha elegível | Aumenta resiliência sem repetir indiscriminadamente operações inseguras |
| Snapshot | Conjunto imutável de configurações publicadas em uma versão conhecida | Permite reproduzir qual regra técnica governou cada execução |
| Step / attempt | Etapa do plano / tentativa concreta de executá-la | Distingue o que a jornada previa do que efetivamente ocorreu |
| Wait / resume | Pausa persistente / retomada da mesma jornada após um sinal | Suporta processos bancários assíncronos sem perder o ponto de execução |

O glossário descreve a semântica do produto, não uma obrigação tecnológica. Em particular, “Porta Universal” não significa “API universal”.

## 21. Referências documentais

- `SPIDER-ARCH-001` — baseline e princípios;
- `SPIDER-ARCH-002` — metamodelo contextual;
- `SPIDER-ARCH-003` — contrato canônico e execução;
- `SPIDER-ARCH-004` — schemas, resultados e erros;
- `SPIDER-ARCH-005` — rotas, plano e estados;
- `SPIDER-ARCH-006` — protocolo universal e perfis;
- `SPIDER-ARCH-007` — Control Plane e governança;
- `SPIDER-ARCH-008` — persistência e evidências;
- `SPIDER-ARCH-009` — segurança e proteção de dados;
- `SPIDER-ARCH-010` — observabilidade e operação;
- `SPIDER-ARCH-011` — topologia e disponibilidade;
- `SPIDER-ARCH-012` — testes e certificação;
- `SPIDER-ARCH-013` — Console e visualização;
- `SPIDER-PROMPT-001–016` — evidência técnica dos incrementos verificados;
- `SPIDER-ROADMAP-IMPLEMENTACAO-016-026` — sequência oficial futura;
- `spider-capability-manifest.json` — estado versionado de capabilities;
- `spider-roadmap-015-026-contract.json` — contrato anti-drift.

---

**Declaração de baseline:** este documento reflete o Spider 0.16.0 / SPIDER-PROMPT-016 VERIFIED, com `MOCK_ONLY` ativo. O 017 (SLOs/health) e o 018 (Failure Lab) permanecem planejados e fora deste espelho funcional.
