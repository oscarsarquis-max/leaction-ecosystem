# SPIDER-ARCH-008 — Persistência Técnica, Idempotência, Evidências e Retenção

| Campo | Valor |
|---|---|
| Identificador | SPIDER-ARCH-008 |
| Título | Persistência Técnica, Idempotência, Evidências e Retenção |
| Status | Proposta arquitetural inicial |
| Predecessor | SPIDER-ARCH-007 — Control Plane, Governança, Publicação e Rollback |
| Escopo | Especificação lógica normativa, sem implementação |

## 1. Objetivo

Formalizar a persistência técnica do Spider, definindo agregados de controle, identidade, estados, planos, tentativas, idempotência, inbox/outbox, evidências, auditoria, snapshots, consistência, retenção, descarte, recuperação e reconciliação.

Este documento preserva o Spider como plataforma de orquestração e não como System of Record de dados de negócio. A persistência aqui definida existe para garantir execução determinística, recuperação, rastreabilidade, segurança e operação.

Este documento não escolhe banco de dados, fornecedor, ORM, produto de streaming, storage de objetos ou topologia física. Não define tabelas, classes ou migrations. Não autoriza implementação, migração do banco atual nem integração com legados reais.

## 2. Vocabulário normativo

Os termos “deve”, “não deve” e “somente” expressam requisitos arquiteturais. “Pode” expressa possibilidade admitida.

- **Registro de controle**: estado técnico necessário para coordenar e recuperar uma execução.
- **Evidência**: registro íntegro ou referência protegida que comprova fato técnico relevante.
- **Auditoria**: sequência append-only de ações, decisões e transições relevantes.
- **Snapshot**: representação consistente do estado técnico em determinado ponto lógico.
- **Idempotency Record**: registro que associa uma operação lógica a fingerprint, estado e resultado reutilizável.
- **Inbox**: registro de recebimento e deduplicação de sinais ou mensagens.
- **Outbox**: registro durável de intenção de publicação ou entrega associado a uma transação de controle.
- **Tombstone**: marcador mínimo que impede reutilização indevida após descarte do conteúdo.
- **Reconciliation Case**: caso técnico aberto quando o estado interno e a evidência externa não podem ser conciliados automaticamente.

## 3. Decisões centrais

1. O Spider persiste somente definições técnicas, controle de execução e evidências necessárias.
2. Dados de negócio presentes em payloads são transitórios, mínimos, classificados e retidos pelo menor prazo aplicável.
3. Toda execução possui identidade estável, release fixada, plano íntegro e histórico de transições.
4. Estado corrente e histórico são complementares; o primeiro favorece operação, o segundo preserva explicabilidade.
5. Idempotência possui escopo, owner, fingerprint, janela, estado e semântica explícitos.
6. Inbox e outbox são padrões semânticos; sua implementação física permanece em aberto.
7. Auditoria e evidências são append-only em sua semântica e protegidas contra alteração indevida.
8. Retry, retomada, replay e reconciliação nunca apagam tentativas anteriores.
9. Retenção é definida por classe de dado e finalidade, não por conveniência tecnológica.
10. Nenhum legado real nem dado real é usado antes da fase final; testes utilizam Mocks e dados sintéticos.

## 4. Fronteira de dados

```text
Definições publicadas do Control Plane
        ↓ referências e versões
Persistência técnica do Data Plane
        ├── Execution Record
        ├── Execution Plan
        ├── Step e Attempt Records
        ├── Idempotency Records
        ├── Inbox / Outbox
        ├── Waits / Timers / Deliveries
        ├── Evidence References
        ├── Audit Events
        └── Reconciliation Cases

Dados mestres e resultados de negócio oficiais
        └── permanecem nos sistemas responsáveis
```

O Spider pode transportar outcome delegado e dados canônicos mínimos, mas não se torna proprietário da verdade de cliente, conta, contrato, limite, risco, preço, produto ou transação.

## 5. Classificação dos dados persistidos

| Classe | Exemplos | Regra principal |
|---|---|---|
| Definição governada | release, rota, contrato, policy e binding | Imutável após publicação |
| Controle operacional | estado, versão, deadline, tentativa e lock lógico | Retenção compatível com recuperação |
| Evidência técnica | decisão, hash, interação e erro normalizado | Integridade e acesso restrito |
| Referência contextual | contextId, intentId e subjectRefs | Opaca, minimizada e autorizada |
| Dado canônico transitório | input/output mínimo de step | Criptografado e retido pelo menor prazo |
| Auditoria administrativa | autoria, aprovação, ativação e rollback | Append-only e segregada |
| Telemetria | logs, métricas e traces | Política própria, sem substituir evidência |

Dados de negócio completos, cadastros mestres e cópias indiscriminadas de payload são proibidos.

## 6. Agregados técnicos

### 6.1 Execution Aggregate

É a fronteira lógica de consistência da máquina de estados de uma execução.

```text
ExecutionRecord
├── executionId
├── contextId
├── correlationId
├── idempotencyRef?
├── releaseId
├── routeRef
├── executionPlanRef
├── state
├── stateVersion
├── technicalStatus
├── deadlines
├── timestamps
├── terminalSummary?
├── activeWaitRefs[]
├── reconciliationRefs[]
└── retentionClassRef
```

O agregado não incorpora todas as tentativas, evidências ou payloads como documento ilimitado. Relações de alto volume usam registros próprios e referências.

### 6.2 Execution Plan Record

Armazena a representação canônica do plano definido no SPIDER-ARCH-005, digest, versões resolvidas e status de integridade. É imutável após a transição para `PLANNED`.

Retomada deve utilizar o mesmo plano. Recompilação automática sobre versões novas é proibida.

### 6.3 Step Record

```text
StepRecord
├── executionId
├── stepId
├── state
├── stateVersion
├── dependencyStatus
├── effectivePolicyRefs[]
├── inputEvidenceRef?
├── outputEvidenceRef?
├── activeAttemptRef?
├── compensationState?
├── timestamps
└── terminalErrorRefs[]
```

`executionId + stepId` identifica unicamente o step materializado dentro da execução.

### 6.4 Attempt Record

Cada tentativa é imutável após terminalização e registra Adapter, binding, contratos, budget, interação, resultado, certainty, erros e evidências. Retry cria novo `attemptId`; nunca sobrescreve a tentativa anterior.

### 6.5 External Interaction Record

Representa uma comunicação individual do Adapter com Mock nesta fase e, apenas na fase final, com destino real. Deve distinguir preparação, envio, aceitação, resposta, timeout e estado inconclusivo.

## 7. Identidades e chaves

| Identidade | Escopo |
|---|---|
| `executionId` | Instância de execução |
| `planId` | Plano materializado |
| `stepId` | Nó da rota dentro da execução |
| `attemptId` | Tentativa individual |
| `invocationId` | Invocação lógica pela Porta Universal |
| `interactionId` | Interação física do Adapter |
| `evidenceId` | Evidência protegida |
| `auditEventId` | Evento de auditoria |
| `deliveryId` | Tentativa de callback ou publicação |
| `reconciliationCaseId` | Caso de reconciliação |

Identificadores são strings opacas, não carregam dado sensível e não devem ser reutilizados. O formato físico definitivo permanece em aberto.

## 8. Estado corrente e histórico

O modelo lógico deve manter:

- projeção eficiente do estado corrente;
- sequência imutável de transições;
- versão monotônica para controle concorrente;
- ligação a motivo, ator, policy e evidência;
- instante observado e instante persistido;
- capacidade de reconstrução e diagnóstico.

O histórico não exige event sourcing como decisão tecnológica. Exige apenas que transições relevantes não sejam perdidas ou reescritas.

## 9. Atomicidade de transição

Uma transição de estado deve confirmar atomicamente, dentro da fronteira de controle aplicável:

1. estado anterior esperado e versão;
2. novo estado e nova versão;
3. evento de transição;
4. criação ou fechamento de tentativa;
5. intenção de publicação em outbox, quando aplicável;
6. referências de evidência mínimas;
7. atualização de deadline ou wait.

Falha parcial dessa gravação não pode deixar o scheduler concluir que o step está simultaneamente em dois estados.

## 10. Concorrência

O modelo deve suportar múltiplos workers sem dupla progressão incompatível.

São requisitos semânticos:

- compare-and-set por `stateVersion` ou mecanismo equivalente;
- lease com fencing token quando houver posse temporária;
- expiração e recuperação de posse abandonada;
- operação idempotente de transição;
- detecção de writer atrasado;
- ausência de lock distribuído indefinido;
- evidência de conflito e reavaliação segura.

A escolha entre optimistic locking, pessimistic locking, leases ou particionamento depende da topologia futura.

## 11. Idempotência

### 11.1 Idempotency Record

```text
IdempotencyRecord
├── idempotencyRecordId
├── scope
│   ├── originatorId
│   ├── capabilityCode
│   ├── operationCode
│   └── contractMajorVersion
├── idempotencyKeyHash
├── requestFingerprint
├── executionId
├── state
├── resultRef?
├── createdAt
├── expiresAt
├── ownerRef
└── retentionClassRef
```

Chaves em claro devem ser evitadas quando hash ou tokenização forem suficientes. O registro precisa permitir deduplicação sem criar índice pesquisável indevido sobre dado sensível.

### 11.2 Fingerprint

O fingerprint é calculado sobre representação canônica dos campos semanticamente relevantes. Deve excluir valores voláteis, como timestamp de tentativa e trace span, e incluir contrato, originador, operação e payload lógico necessário.

O algoritmo, canonicalização e versão fazem parte da evidência. Mudança de algoritmo não pode tornar registros antigos ambíguos.

### 11.3 Estados

| Estado | Semântica |
|---|---|
| `RESERVED` | Chave adquirida antes da execução |
| `IN_PROGRESS` | Execução associada está ativa |
| `COMPLETED` | Resultado terminal reutilizável disponível |
| `FAILED_REUSABLE` | Falha terminal que deve ser repetida consistentemente na janela |
| `UNKNOWN` | Efeito ou resultado inconclusivo exige reconciliação |
| `EXPIRED` | Janela encerrada; tombstone pode permanecer |
| `CONFLICT` | Mesma chave com fingerprint incompatível |

### 11.4 Concorrência de chave

A primeira reserva válida estabelece o fingerprint. Pedidos concorrentes com o mesmo fingerprint recebem a execução corrente ou resultado conhecido. Fingerprint diferente produz conflito explícito; não cria segunda execução sob a mesma chave.

### 11.5 Janela e expiração

A janela deve considerar duração máxima da operação, retries, callbacks, reconciliação e garantias do destino. Expirar registro enquanto efeito externo ainda pode surgir é proibido.

Após descarte, tombstone mínimo pode preservar hash, escopo e término da janela para impedir reutilização perigosa, conforme política de privacidade.

## 12. Inbox

A Inbox registra sinais, mensagens, callbacks e resultados batch recebidos.

```text
InboxRecord
├── messageId
├── sourceRef
├── contractRef
├── deduplicationKeyHash
├── correlationRefs
├── receivedAt
├── validationState
├── processingState
├── payloadEvidenceRef?
├── errorRefs[]
└── retentionClassRef
```

Regras:

- persistir recebimento antes de aplicar efeito de estado;
- autenticar, autorizar, validar e correlacionar;
- deduplicar por identidade estável e fonte;
- preservar mensagens inválidas como evidência mínima segura;
- não reabrir execução terminal por sinal tardio;
- processar novamente somente por ação idempotente e auditada.

## 13. Outbox

A Outbox representa intenção durável de publicar mensagem, callback ou evento após mudança de controle.

```text
OutboxRecord
├── outboxId
├── executionId
├── messageType
├── contractRef
├── destinationBindingRef
├── logicalIdempotencyKeyHash
├── payloadEvidenceRef
├── state
├── attemptCount
├── nextAttemptAt
├── expiresAt
└── deliveryRefs[]
```

Estados mínimos: `PENDING`, `DISPATCHING`, `DELIVERED`, `RETRY_SCHEDULED`, `DEAD_LETTERED`, `EXPIRED` e `CANCELLED`.

Outbox não garante consumo pelo destino. Confirma apenas a intenção e o ciclo de entrega conforme garantias declaradas.

## 14. Callbacks e entregas

Cada tentativa de callback gera `Delivery Record` com `deliveryId`, chave lógica estável, número da tentativa, timestamps, binding, resultado, erro e evidência.

Falha definitiva de callback não altera o resultado principal. Deve produzir condição operacional observável, dead letter lógico e possibilidade governada de reconciliação.

Payload de callback pode ser regenerado somente a partir de resultado canônico íntegro e versão do contrato aplicável. Regeneração não pode usar estado de negócio atual para reescrever resultado histórico.

## 15. Waits e timers

```text
WaitRecord
├── waitId
├── executionId
├── stepId
├── waitType
├── correlationRuleRef
├── signalContractRef
├── state
├── createdAt
├── earliestResumeAt?
├── expiresAt
├── receivedSignalRef?
└── expiryActionRef
```

Timers devem ser duráveis, particionáveis e recuperáveis. Disparo duplicado é esperado e tratado idempotentemente. A precisão temporal e o atraso máximo serão definidos por classe de serviço.

Estados mínimos: `WAITING`, `SIGNALLED`, `EXPIRING`, `EXPIRED`, `RESUMED` e `CANCELLED`.

## 16. Evidências

### 16.1 Evidence Descriptor

```text
EvidenceDescriptor
├── evidenceId
├── evidenceType
├── subjectRefs[]
├── createdAt
├── sourceComponent
├── classification
├── contentRef
├── contentDigest
├── canonicalizationVersion
├── encryptionRef?
├── retentionPolicyRef
├── legalHoldRef?
└── accessPolicyRef
```

O descriptor não concede acesso ao conteúdo. A autorização é verificada no momento da consulta.

### 16.2 Tipos iniciais

| Tipo | Finalidade |
|---|---|
| `RESOLUTION` | Candidatos, critérios e rota selecionada |
| `PLAN` | Versões, integridade e materialização |
| `STATE_TRANSITION` | Mudança da execução ou step |
| `ATTEMPT` | Tentativa, policies e resultado |
| `EXTERNAL_INTERACTION` | Fase, certainty e resposta normalizada |
| `SECURITY` | Identidade, autorização e decisão de confiança |
| `CALLBACK_DELIVERY` | Tentativa e confirmação de entrega |
| `RECONCILIATION` | Investigação e resolução de inconsistência |
| `ADMINISTRATIVE` | Publicação, ativação, rollback e override |

### 16.3 Conteúdo

Conteúdo pode estar inline apenas quando pequeno, seguro e necessário. Conteúdo volumoso ou sensível usa storage protegido e referência. Payload integral não deve ser evidência padrão.

Preferir:

- digest da representação canônica;
- campos técnicos selecionados;
- códigos normalizados;
- referências opacas;
- amostra mascarada quando indispensável;
- localização autorizada de evidência externa.

## 17. Integridade e cadeia de custódia

Evidências devem permitir detectar alteração, substituição e perda. A estratégia pode combinar digest, assinatura, encadeamento, storage imutável e timestamp confiável conforme criticidade.

A cadeia de custódia registra criação, movimentação, acesso, exportação, retenção, legal hold e descarte. Cópia exportada deve manter digest e proveniência.

Integridade não equivale a veracidade do dado externo; prova apenas que o Spider preservou o conteúdo observado e sua origem declarada.

## 18. Auditoria

### 18.1 Audit Event

```text
AuditEvent
├── auditEventId
├── eventType
├── occurredAt
├── recordedAt
├── actorRef
├── action
├── objectRef
├── previousState?
├── newState?
├── reasonCode
├── correlationRefs[]
├── evidenceRefs[]
└── sequence
```

### 18.2 Regras

- semântica append-only;
- correção por novo evento vinculado;
- ordenação por sequence dentro do agregado;
- proteção contra alteração e exclusão indevidas;
- acesso auditado;
- separação entre auditoria técnica e log diagnóstico;
- mensagens sem secrets ou payloads sensíveis;
- retenção compatível com obrigação e finalidade.

Auditoria não deve ser usada como banco de consulta de negócio.

## 19. Logs, métricas e traces

Telemetria é complementar:

| Sinal | Papel |
|---|---|
| Log | Diagnóstico textual e eventos operacionais |
| Métrica | Agregação quantitativa e alerta |
| Trace | Relação causal e latência distribuída |
| Auditoria | Responsabilização e histórico governado |
| Evidência | Comprovação protegida de fato técnico |

Falha na telemetria não pode corromper estado de execução. Falha na persistência de evidência obrigatória pode impedir avanço, conforme criticidade.

## 20. Snapshots

Snapshots podem reduzir custo de reconstrução, mas não substituem histórico exigido.

Um snapshot deve declarar:

- agregado e versão cobertos;
- instante lógico e sequência final;
- schema e versão;
- digest;
- origem dos eventos ou registros;
- política de retenção;
- compatibilidade do runtime.

Snapshot corrompido é descartado e reconstruído a partir da fonte íntegra. Não deve ser corrigido manualmente.

## 21. Reconciliation Case

Um caso é aberto quando há estado externo `UNKNOWN`, divergência de callback, mensagem órfã, timeout após possível efeito, falha de compensação ou inconsistência detectada.

```text
ReconciliationCase
├── reconciliationCaseId
├── executionId
├── stepId?
├── category
├── state
├── severity
├── openedAt
├── ownerRef
├── evidenceRefs[]
├── allowedActions[]
├── resolution
└── closedAt?
```

Estados mínimos: `OPEN`, `INVESTIGATING`, `AWAITING_EXTERNAL`, `ACTION_REQUIRED`, `RESOLVED`, `CLOSED` e `EXPIRED`.

Ação manual deve ser autenticada, autorizada, limitada às opções publicadas e auditada. Alteração direta de registro para “corrigir” execução é proibida.

## 22. Consistência entre stores

A arquitetura pode usar stores diferentes para estado, payload transitório, evidência e telemetria. Nesse caso, deve declarar:

- fonte de autoridade de cada dado;
- ordem de escrita e falhas intermediárias;
- mecanismo de correlação;
- reconciliação;
- consistência esperada;
- tratamento de duplicidade;
- recuperação e retenção coordenadas.

Transação distribuída não é assumida. Consistência é obtida por transações locais, outbox/inbox, idempotência, compensação técnica e reconciliação.

## 23. Criptografia e gestão de chaves

- criptografia em trânsito e repouso conforme classificação;
- separação de chaves por ambiente e finalidade;
- rotação sem perda de acesso a evidência retida;
- envelope encryption ou mecanismo equivalente para conteúdo sensível;
- secrets fora dos registros;
- acesso à chave auditado;
- destruição criptográfica admitida quando compatível com retenção e legal hold.

Hash sem salt de identificador previsível pode permitir enumeração e deve ser evitado.

## 24. Autorização e acesso

Consultas devem aplicar menor privilégio, purpose limitation e escopo por função, domínio, ambiente e classificação.

São capacidades distintas:

- consultar estado operacional;
- visualizar outcome canônico;
- acessar evidência protegida;
- exportar dados;
- iniciar reconciliação;
- aplicar legal hold;
- autorizar descarte;
- administrar política de retenção.

Uma referência ou correlationId conhecido não concede acesso.

## 25. Retenção

### 25.1 Política

```text
RetentionPolicy
├── retentionPolicyCode
├── version
├── dataClass
├── purpose
├── triggerEvent
├── minimumPeriod
├── maximumPeriod
├── dispositionAction
├── legalHoldBehavior
├── ownerRef
└── evidenceRequirement
```

Períodos definitivos dependem de requisitos legais, regulatórios, contratuais, de segurança e operação. Este documento não fixa prazos numéricos sem essa análise.

### 25.2 Princípios

1. Reter somente pelo tempo necessário à finalidade declarada.
2. Diferenciar estado, payload, evidência, auditoria e telemetria.
3. Não usar “auditoria” como justificativa genérica para retenção ilimitada.
4. Proteger dado durante toda a retenção.
5. Suspender descarte sob legal hold válido.
6. Produzir evidência do descarte sem preservar o conteúdo descartado.
7. Coordenar cópias, backups, caches, réplicas e índices.

## 26. Descarte

O descarte pode ser exclusão física, anonimização irreversível, destruição criptográfica ou combinação, conforme storage e política.

O processo deve:

- verificar prazo e legal hold;
- identificar todas as cópias controladas;
- preservar tombstone mínimo quando necessário à idempotência;
- remover índices e caches derivados;
- registrar execução, escopo, método e resultado;
- detectar falhas parciais e repetir idempotentemente;
- comprovar conclusão por evidência protegida.

Descarte não pode quebrar integridade referencial de forma que torne auditoria enganosa. Referências podem permanecer com indicação explícita de conteúdo descartado.

## 27. Backups e recuperação

Backups devem cobrir estado, planos, idempotência, inbox/outbox, evidências e manifests necessários. Requisitos:

- criptografia e segregação;
- inventário e retenção próprios;
- teste periódico de restauração;
- ponto e tempo de recuperação definidos por classe;
- verificação de integridade após restore;
- prevenção de reenvio indevido de outbox;
- reconciliação de timers, leases e mensagens após recuperação;
- proteção contra restaurar artefato revogado como ativo.

Restauração não pode reutilizar fencing token antigo nem perder tombstone idempotente ainda válido.

## 28. Particionamento e escala

Particionamento físico permanece em aberto. A semântica deve permitir distribuição por `executionId`, tempo, tenant lógico ou domínio autorizado, preservando:

- afinidade das transições do agregado;
- unicidade do escopo idempotente;
- consultas operacionais essenciais;
- retenção e descarte por partição;
- ausência de hotspot previsível;
- movimentação com integridade;
- isolamento de carga e falha.

Particionamento não deve codificar significado bancário em identificador opaco.

## 29. Índices e consultas

Índices devem servir casos técnicos autorizados:

- localizar execução por `executionId`;
- resolver idempotência por escopo e hash;
- buscar waits e outbox vencidos;
- localizar mensagens inbox pendentes;
- monitorar reconciliações abertas;
- consultar evidências por subjectRef autorizado;
- operar retenção e descarte.

Busca livre sobre payload sensível é proibida por padrão. Novo índice exige finalidade, classificação, owner e impacto de retenção.

## 30. Evolução de schema

Mudanças físicas devem preservar leitura de registros existentes e execução longa.

Regras:

- schemaVersion em registros relevantes;
- migrations compatíveis e reversíveis quando possível;
- dual-read/write somente por janela governada;
- backfill idempotente e observável;
- proibição de reinterpretar estado histórico;
- evidência da transformação;
- rollback que não perca dados escritos na nova versão;
- testes com snapshots e registros antigos.

## 31. Falhas e modo seguro

| Falha | Comportamento esperado |
|---|---|
| Store de estado indisponível | Não iniciar efeito externo sem controle durável requerido |
| Store de evidência indisponível | Bloquear ou degradar somente conforme criticidade publicada |
| Telemetria indisponível | Preservar execução e emitir indicador de degradação |
| Outbox indisponível | Não confirmar transição que exige publicação atômica |
| Cache indisponível | Usar fonte íntegra ou falhar seguro; nunca inventar estado |
| Integridade inválida | Isolar registro e abrir reconciliação |
| Capacidade esgotada | Aplicar backpressure e rejeição explícita |

Queda de store não autoriza execução em memória de operação com efeito quando a recuperação depender de persistência.

## 32. Estratégia Mock-first e dados sintéticos

Nesta fase:

- External Interactions referenciam apenas simuladores;
- payloads usam dados sintéticos ou anonimizados aprovados;
- falhas de persistência, duplicidade e recuperação são injetáveis;
- relógio virtual pode testar expiração, retry e retenção;
- callbacks e mensagens duplicadas, tardias e fora de ordem são simulados;
- legal hold, descarte e restauração são exercitados em dados de teste;
- nenhuma credencial, endpoint ou dado de legado real é permitido.

Os simuladores não definem modelo físico nem prazo de retenção. Sua função é comprovar as invariantes.

## 33. Testes de conformidade

Devem ser automatizáveis, no mínimo:

- criação e transição atômica de execução;
- conflito concorrente e fencing de writer atrasado;
- imutabilidade do plano e attempts;
- reserva idempotente concorrente;
- fingerprint igual, divergente e mudança de algoritmo;
- expiração e tombstone;
- inbox duplicada, inválida, tardia e órfã;
- outbox com falha antes e depois do envio;
- callback deduplicado e dead letter;
- timers duplicados e retomada após reinício;
- evidência íntegra, alterada, ausente e sem autorização;
- reconstrução de estado e snapshots;
- caso de reconciliação e ação manual governada;
- perda parcial entre stores;
- rotação de chaves;
- retenção, legal hold, descarte e evidência de descarte;
- backup, restore e prevenção de reenvio;
- evolução de schema com execução longa;
- uso exclusivo de Mocks e dados sintéticos.

## 34. Decisões arquiteturais consolidadas

1. A persistência do Spider é técnica e de controle.
2. O Spider não é System of Record de dados bancários.
3. Execution, Plan, Step, Attempt e Interaction são registros distintos.
4. Estado corrente e histórico de transição são complementares.
5. Transições usam controle concorrente e evidência.
6. Idempotência possui escopo, fingerprint, janela, owner e estados explícitos.
7. Mesma chave com request incompatível produz conflito.
8. Inbox deduplica sinais antes de aplicar efeito.
9. Outbox preserva intenção durável de entrega.
10. Timeout inconclusivo abre reconciliação; não autoriza retry cego.
11. Evidências são minimizadas, íntegras, classificadas e autorizadas.
12. Auditoria é append-only na semântica e distinta de logs.
13. Snapshots aceleram leitura sem substituir histórico necessário.
14. Consistência entre stores usa padrões recuperáveis, não assume transação distribuída.
15. Retenção é específica por classe e finalidade.
16. Descarte alcança cópias, derivados, caches e backups conforme política.
17. Recuperação preserva idempotência e impede reenvio indevido.
18. Nesta fase, somente Mocks e dados sintéticos são permitidos.

## 35. Invariantes arquiteturais

1. Nenhum efeito externo crítico inicia sem registro durável requerido.
2. Toda execução referencia release e plano íntegros.
3. Toda transição incrementa versão monotônica.
4. Todo retry cria nova tentativa.
5. Nenhuma tentativa terminal é sobrescrita.
6. Nenhum sinal altera estado antes de deduplicação e validação.
7. Nenhuma outbox entregue é reenviada como nova operação lógica.
8. Nenhuma chave idempotente aceita fingerprint divergente.
9. Nenhum estado `UNKNOWN` é convertido em certeza sem evidência.
10. Nenhuma ação manual edita diretamente o passado.
11. Toda evidência possui classificação, integridade e retenção.
12. Referência de evidência não concede acesso.
13. Log não substitui auditoria ou evidência.
14. Payload de negócio não é retido por conveniência.
15. Nenhum índice novo existe sem finalidade autorizada.
16. Descarte não ocorre sob legal hold válido.
17. Restore não reativa lease, timer ou entrega de forma insegura.
18. Mudança de schema não reinterpreta estado histórico.
19. Nenhum dado ou destino de legado real é usado antes da fase final.
20. Troca futura de Mock por legado não altera os agregados centrais.

## 36. Pontos ainda abertos

| Tema | Questão a decidir |
|---|---|
| Stores | Relacional, chave-valor, log, objetos ou combinação |
| Modelo físico | Tabelas, documentos, eventos e normalização |
| Transações | Fronteiras locais e mecanismos outbox/inbox |
| Concorrência | Locking, leases, fencing e particionamento |
| Idempotência | Algoritmo de fingerprint, janela e tombstone por operação |
| Evidências | Storage, assinatura, canonicalização e acesso |
| Auditoria | Plataforma, imutabilidade e consulta |
| Payload | Limites inline, storage protegido e tokenização |
| Criptografia | KMS/HSM, envelope encryption e rotação |
| Retenção | Prazos definitivos por classe e obrigação |
| Legal hold | Autoridade, escopo e liberação |
| Descarte | Métodos verificáveis por tecnologia |
| Backup | RPO, RTO, imutabilidade e testes de restore |
| Schema | Ferramenta de migration e compatibilidade |
| Escala | Partições, hotspots, arquivamento e tiering |
| Operação | Ferramentas de reconciliação e segregação de funções |
| Fase final | Requisitos adicionais de evidência para cada legado real |

## 37. Critérios de aceite

O SPIDER-ARCH-008 é considerado apto a orientar a próxima etapa quando:

1. fronteira entre persistência técnica e dados de negócio estiver inequívoca;
2. agregados e identidades técnicas estiverem separados;
3. estado, histórico, atomicidade e concorrência estiverem definidos;
4. idempotency record, fingerprint, janela e conflito estiverem formalizados;
5. inbox, outbox, waits e deliveries possuírem semântica clara;
6. evidências, integridade, auditoria e telemetria estiverem diferenciadas;
7. snapshots e reconciliação estiverem especificados;
8. segurança, autorização e criptografia estiverem previstas;
9. retenção, legal hold, descarte e recuperação estiverem governados;
10. evolução de schema e falhas tiverem modo seguro;
11. Mocks e dados sintéticos permanecerem exclusivos nesta fase;
12. nenhuma decisão exigir banco, fornecedor ou implementação prematura.

## 38. Próxima etapa recomendada

Antes de implementar, recomenda-se criar:

> **SPIDER-ARCH-009 — Segurança, Identidade, Autorização e Proteção de Dados**

Esse documento deverá formalizar identidades de originador, ator, workload e operador; autenticação; delegação; autorização contextual; confiança entre zonas; mTLS e assinatura; gestão de secrets; proteção de mensagens; LGPD; minimização; mascaramento; prevenção de replay; não repúdio; resposta a incidentes e controles aplicáveis a todos os perfis de integração.

A especificação continuará tecnologicamente neutra, usando somente identidades de teste, Mocks e dados sintéticos nesta fase. Prompts de implementação permanecem separados em `SPIDER-PROMPT-NNN`. Legados reais continuam fora de escopo até a fase final.
