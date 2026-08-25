# SPIDER-ARCH-010 — Observabilidade, SLOs, Operação e Resposta a Falhas

| Campo | Valor |
|---|---|
| Identificador | SPIDER-ARCH-010 |
| Título | Observabilidade, SLOs, Operação e Resposta a Falhas |
| Status | Proposta arquitetural inicial |
| Predecessor | SPIDER-ARCH-009 — Segurança, Identidade, Autorização e Proteção de Dados |
| Escopo | Especificação lógica normativa, sem implementação |

## 1. Objetivo

Formalizar o modelo operacional e de observabilidade do Spider, definindo sinais, correlação, SLIs, SLOs, error budgets, saúde, alertas, dashboards, capacidade, backpressure, diagnóstico, processos longos, reconciliação, incidentes, runbooks, continuidade e critérios de prontidão.

Este documento estabelece como o Spider deve demonstrar que está funcionando, degradando ou falhando sem depender de conhecimento do protocolo dos sistemas integrados e sem misturar estados técnicos com resultados de negócio delegados.

Este documento não escolhe plataforma de logs, métricas, traces, APM, SIEM, alertas, ITSM, pager, dashboard, storage ou fornecedor. Não define deploy, quantidade de instâncias ou SLOs numéricos definitivos. Não autoriza implementação nem conexão com legados reais.

## 2. Vocabulário normativo

Os termos “deve”, “não deve” e “somente” expressam requisitos arquiteturais. “Pode” expressa possibilidade admitida.

- **Observabilidade**: capacidade de compreender o estado interno a partir de sinais e evidências produzidos.
- **SLI**: indicador quantitativo de um comportamento relevante ao usuário ou consumidor.
- **SLO**: objetivo mensurável para um SLI durante uma janela definida.
- **Error Budget**: tolerância de falha derivada do SLO.
- **Golden Signal**: sinal fundamental de latência, tráfego, erro ou saturação.
- **Health**: condição observada de componente, dependência, binding ou fluxo.
- **Degradação**: operação com capacidade, qualidade ou garantia reduzida de modo explícito.
- **Backpressure**: mecanismo que limita aceitação ou propagação de trabalho quando a capacidade é insuficiente.
- **Runbook**: procedimento operacional versionado, testado e associado a um alerta ou condição.
- **Operational Event**: fato técnico relevante para operação, distinto de log textual arbitrário.
- **Incident**: degradação ou risco que exige coordenação e resposta formal.

## 3. Decisões centrais

1. Observabilidade é parte do contrato operacional, não recurso opcional adicionado após implementação.
2. Logs, métricas, traces, auditoria e evidências têm papéis distintos e correlacionáveis.
3. Todo sinal utiliza identidades opacas de execução, step, attempt, interação, release e binding.
4. Resultado técnico e outcome de negócio delegado permanecem separados em métricas e alertas.
5. SLIs são medidos na fronteira relevante ao consumidor e definidos por classe de serviço.
6. SLOs e error budgets orientam operação e mudança; não substituem requisitos regulatórios ou de segurança.
7. Alertas devem ser acionáveis, possuir owner e estar vinculados a runbook.
8. Saúde de componente, dependência, rota e jornada são dimensões distintas.
9. Backpressure e load shedding são explícitos, governados e falham de modo seguro.
10. Nesta fase, sinais, falhas e incidentes são validados somente com Mocks e fault injection controlado.

## 4. Modelo de sinais

```text
Execução e operação
      ├── Logs estruturados
      ├── Métricas
      ├── Traces distribuídos
      ├── Operational Events
      ├── Auditoria
      └── Evidence References
             ↓ correlação
        Camada de observação
             ├── Dashboards
             ├── Alertas
             ├── Análise de SLO
             ├── Diagnóstico
             └── Resposta a incidentes
```

Nenhum sinal isolado deve ser considerado fonte completa de verdade para todas as finalidades.

## 5. Identidades de correlação

| Identidade | Finalidade operacional |
|---|---|
| `executionId` | Localizar uma execução específica |
| `contextId` | Relacionar execução à ocorrência contextual autorizada |
| `correlationId` | Relacionar interações de um fluxo funcional |
| `traceId` | Navegar pela causalidade distribuída |
| `spanId` | Identificar unidade observada no trace |
| `stepId` | Localizar nó do Execution Plan |
| `attemptId` | Distinguir retries técnicos |
| `invocationId` | Relacionar chamada à Porta Universal |
| `interactionId` | Identificar interação do Adapter |
| `releaseId` | Identificar configuração publicada ativa |
| `bindingRef` | Agrupar comportamento de uma integração lógica |
| `incidentId` | Relacionar sinais e ações a um incidente |

Identificadores não são intercambiáveis. Labels de métricas devem evitar valores de alta cardinalidade, como `executionId`, enquanto logs, traces e evidências podem carregá-los conforme acesso e retenção.

## 6. Logs estruturados

### 6.1 Estrutura mínima

```text
StructuredLogEvent
├── timestamp
├── severity
├── eventCode
├── component
├── environment
├── releaseId
├── executionId?
├── correlationId?
├── traceId?
├── stepId?
├── attemptId?
├── bindingRef?
├── state?
├── reasonCode?
├── safeAttributes
└── evidenceRef?
```

### 6.2 Regras

- eventos possuem código estável e mensagem legível;
- atributos são estruturados, tipados e permitidos por allowlist;
- payload integral, token, secret e credencial são proibidos;
- campos sensíveis são removidos ou mascarados antes da emissão;
- stack trace é restrita a falha interna e acesso autorizado;
- severidade representa impacto técnico, não preferência do desenvolvedor;
- repetição de alta frequência deve ser agregada ou limitada;
- log não substitui transição de estado, auditoria ou evidência.

### 6.3 Severidades

| Severidade | Uso |
|---|---|
| `DEBUG` | Diagnóstico temporário e controlado, desabilitado por padrão em operação |
| `INFO` | Evento normal relevante ao ciclo técnico |
| `WARN` | Degradação ou condição recuperável que merece observação |
| `ERROR` | Falha de operação ou step sem colapso do componente |
| `FATAL` | Perda de capacidade essencial ou risco de integridade |

Outcome de negócio negativo processado corretamente não deve gerar `ERROR` técnico por padrão.

## 7. Métricas

### 7.1 Famílias mínimas

| Família | Exemplos lógicos |
|---|---|
| Tráfego | requests, executions, steps, callbacks e mensagens |
| Latência | validação, resolução, planning, step, Adapter e end-to-end |
| Erro | rejeições, falhas, timeout, unknown, compensation e callback failure |
| Saturação | filas, workers, pools, memória, CPU, storage e conexões |
| Resiliência | retries, circuit state, rate limit, bulkhead e backpressure |
| Estado | executions por state, waits, outbox e reconciliation cases |
| Control Plane | validação, publicação, distribuição e convergência de snapshot |
| Segurança | auth failures, denies, replay, secret e integrity violations |

### 7.2 Cardinalidade

São labels adequados quando governados: ambiente, component, capability, operation, routeCode, adapterCode, bindingCode, state, errorCategory e releaseId com cardinalidade controlada.

São proibidos como labels por padrão: executionId, contextId, actorRef, accountRef, payload value, mensagem livre e stack trace.

### 7.3 Histogramas e agregação

Latência deve ser observada por distribuição, não apenas média. Buckets ou quantis devem refletir budgets relevantes. Agregação não pode ocultar cauda longa, timeout ou comportamento por classe crítica.

## 8. Traces distribuídos

### 8.1 Modelo

```text
Ingress span
 ├── validation span
 ├── authorization span
 ├── route resolution span
 ├── planning span
 └── execution span
      ├── step span
      │    └── adapter span
      │         └── external interaction span
      ├── wait/signal span links
      ├── compensation span
      └── callback delivery span
```

### 8.2 Regras

- W3C Trace Context é a referência definida no SPIDER-ARCH-003;
- contexto inválido ou não confiável é rejeitado ou reiniciado conforme policy;
- causalidade assíncrona usa links quando relação parent-child não for adequada;
- retry produz span distinto por attempt;
- atributos seguem classificação e allowlist;
- sampling não pode impedir evidência obrigatória;
- baggage é limitado, classificado e nunca transporta secret ou payload;
- trace não altera comportamento funcional da execução.

## 9. Operational Events

Operational Events representam fatos com semântica estável, como:

- execution accepted, completed ou timed out;
- step entered wait ou compensation;
- circuit opened ou recovered;
- binding degraded;
- snapshot activated ou diverged;
- reconciliation case opened;
- error budget threshold crossed;
- security barrier violated;
- capacity threshold reached;
- incident declared ou resolved.

Eles podem alimentar automação, dashboards e alertas, mas não são comandos implícitos para alterar estado de execução.

### 9.1 Implementação canônica (SPIDER-PROMPT-016)

A implementação Mock entrega o contrato `OperationalEvent` (`schemaVersion = 1`) com categorias
`EXECUTION | INTERACTION | TRANSPORT | CALLBACK | SIGNAL | SECURITY | SYSTEM` e outcomes
`SUCCESS | FAILURE | WAITING | REJECTED | INFO`.

Decisões vinculadas ao 016:

1. **Telemetria observa; não controla** — falha ao publicar não altera o resultado funcional da engine.
2. **Não é event sourcing** — o estado persistido da execução permanece a fonte de verdade; eventos não o substituem.
3. **Sem broker** nesta etapa — persistência técnica em PostgreSQL (`tb_operational_event`) / store em memória nos testes.
4. **Metadata allowlist + redaction** — reutiliza a política do console 015; sem secrets, tokens, HMAC completo ou payloads.
5. **Correlação** — `executionId` obrigatório; `interactionId` / `correlationId` / `eventId` quando disponíveis.
6. **Consulta** — timeline operacional read-only via Console (`GET /v1/console/executions/{id}/events`).
7. **017 / 018** — SLOs, health analytics e Failure Lab consomem estes fatos depois; não fazem parte do 016.

Diferença preservada: **logs** diagnosticam a aplicação; **Operational Events** registram acontecimentos canônicos da execução.

## 10. Auditoria e evidências operacionais

Auditoria responde quem fez o quê, quando, sobre qual objeto e com qual autorização. Evidência comprova fato técnico específico. Operação deve poder navegar de alerta e trace até essas referências sem acesso indiscriminado ao conteúdo.

São auditáveis:

- ativação, rollback e revogação;
- intervenção, cancelamento e replay;
- mudança de policy operacional;
- acesso e exportação de evidência;
- abertura e fechamento de reconciliação;
- uso de break-glass;
- reconhecimento e resolução de incidentes críticos.

## 11. Classes de serviço

Uma classe de serviço agrupa operações com expectativa operacional semelhante.

```text
ServiceClass
├── serviceClassCode
├── supportedInteractionModes[]
├── availabilityObjectiveRef
├── latencyObjectiveRef
├── durabilityObjectiveRef
├── recoveryObjectiveRef
├── capacityPolicyRef
├── supportWindowRef
├── criticality
└── ownerRef
```

Uma capability pode ter classes distintas por operation ou canal. A classe não incorpora regra bancária.

## 12. Health (implementação SPIDER-PROMPT-017)

A saúde operacional do Spider é um **snapshot read-only** calculado a partir de stores e Operational Events.
Não substitui `/actuator/health` (prontidão de processo). Não emite comandos à Engine.

### 12.1 SLIs provisórios Mock

Indicadores mínimos: confiabilidade técnica, latência p95, waits envelhecidos, callback, signal ingress e cobertura de telemetria.
Objetivos são **PROVISÓRIOS · MOCK_ONLY · NÃO CONTRATUAIS**. Amostra insuficiente não vira falso verde.

### 12.2 Error budget

Para SLIs de sucesso: consumo = falha observada / falha permitida pelo alvo provisório. Exibido no Cockpit como “tolerância técnica provisória”.

### 12.3 Cockpit

Console: `GET /v1/console/operational-health` → superfície **Cockpit Operacional** (distinta do Cockpit de Implementação e do Failure Lab 018).

## 13. SLIs

### 13.1 Disponibilidade

Proporção de solicitações elegíveis que recebem resposta tecnicamente correta dentro do contrato da classe. Rejeição válida por autenticação, autorização ou contrato pode ser excluída do denominador conforme definição explícita; falha interna não pode.

### 12.2 Latência

Distribuição do tempo desde a aceitação na fronteira definida até resposta terminal ou aceitação assíncrona válida. Processos longos possuem SLI separado para tempo de aceitação e tempo de conclusão.

### 12.3 Correção técnica

Proporção de execuções sem erro interno, contrato inválido produzido pelo Spider, duplicidade indevida ou transição inconsistente.

### 13.4 Durabilidade

Proporção de estados e eventos duráveis recuperáveis após confirmação.

### 13.5 Atualidade

Idade de backlog, wait vencido, outbox pendente, snapshot não convergido ou reconciliação aberta.

### 13.6 SLI de Adapter

Mede disponibilidade, latência, contrato, certainty e resultado técnico na Porta Universal, separado do SLI end-to-end.

## 14. SLOs

Todo SLO deve declarar:

```text
SLODefinition
├── sloCode
├── version
├── serviceClassRef
├── sliRef
├── objective
├── measurementWindow
├── eligibleEvents
├── excludedEvents
├── dataSourceRefs[]
├── ownerRef
├── reviewPeriod
└── errorBudgetPolicyRef
```

SLO numérico somente deve ser aprovado após baseline com simuladores representativos e requisitos reais. Meta arbitrária não deve virar contrato arquitetural.

SLO de Spider não pode incluir indiscriminadamente tempo de decisão humana ou processamento externo fora da responsabilidade definida.

## 15. Error budgets

Error budget é calculado a partir do SLO e da janela. Sua política pode:

- limitar ritmo de mudança;
- exigir revisão de risco;
- bloquear ativação gradual;
- priorizar trabalho de confiabilidade;
- aumentar observação ou sampling;
- acionar contenção de capability degradada.

Error budget não autoriza violar segurança, integridade ou obrigação regulatória. Uma única falha crítica de integridade pode exigir contenção independentemente do budget restante.

## 15. Indicadores de processos assíncronos

Processos longos devem medir separadamente:

- tempo até aceitação;
- tempo até entrar em espera;
- idade da espera;
- tempo entre sinal e retomada;
- tempo total até terminalização;
- callbacks entregues, atrasados e dead-lettered;
- sinais duplicados, inválidos e tardios;
- timers vencidos não processados;
- reconciliações abertas por tempo.

Uma execução em `WAITING_EXTERNAL` dentro do prazo não é falha de disponibilidade.

## 16. Saúde

### 16.1 Dimensões

| Dimensão | Pergunta |
|---|---|
| Liveness | O componente está executando e pode progredir? |
| Readiness | Pode aceitar novo trabalho com segurança? |
| Dependency | Qual condição observada de uma dependência? |
| Binding | O binding está configurado, certificado e operacional? |
| Snapshot | A release ativa é íntegra e compatível? |
| Capacity | Há recursos suficientes para a carga atual? |
| Security | Identidades, secrets e certificados estão válidos? |

### 16.2 Regras

- health check deve ser barato, limitado e não produzir efeito;
- liveness não depende de todas as dependências externas;
- readiness deve impedir aceitação que não possa ser processada com segurança;
- dependency health não seleciona rota fora do Control Plane;
- falha de health check isolada não prova falha de todas as operações;
- resultado e razão devem ser observáveis sem revelar segredo.

## 17. Estado de bindings e dependências

```text
BindingOperationalState
├── bindingRef
├── state
├── observedAt
├── certainty
├── reasonCode
├── circuitState
├── capacityState
├── securityState
├── contractState
└── evidenceRefs[]
```

Estados iniciais: `HEALTHY`, `DEGRADED`, `UNAVAILABLE`, `UNKNOWN`, `DISABLED` e `REVOKED`.

`UNKNOWN` não deve ser convertido automaticamente em `HEALTHY`. Estado operacional não altera binding ou rota publicada.

## 18. Alertas

### 18.1 Alert Definition

```text
AlertDefinition
├── alertCode
├── version
├── signalRef
├── condition
├── evaluationWindow
├── severity
├── ownerRef
├── routingPolicyRef
├── deduplicationKey
├── runbookRef
├── autoResolutionRule?
└── suppressionPolicyRef?
```

### 18.2 Qualidade

Um alerta deve ser:

- acionável;
- específico quanto ao impacto;
- associado a owner e runbook;
- deduplicável;
- resistente a flapping;
- testado;
- baseado em sintoma quando possível;
- separado de evento informativo.

Alerta sem ação possível deve ser dashboard, relatório ou tarefa, não pager.

## 19. Severidade operacional

| Severidade | Impacto geral |
|---|---|
| `SEV-1` | Indisponibilidade ampla, integridade ou segurança crítica |
| `SEV-2` | Degradação significativa ou fluxo crítico afetado |
| `SEV-3` | Impacto limitado com workaround ou risco crescente |
| `SEV-4` | Defeito menor, tendência ou necessidade de manutenção |

Critérios definitivos dependem da organização. Outcome negativo de negócio não é incidente do Spider quando o processamento técnico foi correto.

## 20. Burn rate

Alertas de SLO devem considerar consumo de error budget em múltiplas janelas. Janela curta detecta falha rápida; janela longa detecta degradação persistente.

Thresholds numéricos serão definidos com os SLOs. O modelo deve evitar alertar a cada erro isolado quando o impacto é adequadamente capturado por budget, sem ocultar violações críticas de segurança ou integridade.

## 21. Dashboards

### 21.1 Visões mínimas

- visão executiva de SLO e error budget;
- visão operacional do Data Plane;
- visão do Control Plane e convergência de releases;
- visão de executions por estado;
- visão de processos longos, waits e callbacks;
- visão de Adapters e bindings;
- visão de capacidade e saturação;
- visão de segurança;
- visão de reconciliação e dead letters;
- visão por capability e service class.

### 21.2 Regras

- cada painel declara público, owner, fonte e janela;
- unidades, denominadores e exclusões são explícitos;
- cores não são único meio de comunicar estado;
- drill-down preserva autorização e classificação;
- dashboards não expõem payload ou identificador sensível;
- release markers permitem correlacionar mudança e comportamento.

## 22. Capacidade

Capacity Planning deve considerar:

- taxa média, pico e burst;
- distribuição de duração;
- fan-out de steps;
- retries e amplificação;
- paralelismo por rota;
- waits e timers;
- callbacks e mensagens;
- tamanho de payload e evidência;
- limites de Adapter e destino;
- crescimento de stores e retenção;
- recuperação após backlog.

Capacidade nominal não deve assumir que todos os destinos respondem imediatamente.

## 23. Saturação

São indicadores potenciais:

- backlog e idade da fila;
- utilização de worker e pool;
- conexões ocupadas;
- latência de persistência;
- throttling;
- memória e garbage collection;
- CPU;
- storage, IOPS e crescimento;
- timers atrasados;
- circuit breakers abertos;
- outbox e inbox pendentes.

Thresholds devem se relacionar a impacto e tempo de recuperação, não apenas percentual de recurso.

## 24. Backpressure

Backpressure deve ser propagada de forma explícita das dependências para o ingress quando necessário.

Mecanismos lógicos possíveis:

- limitar concorrência;
- reduzir prefetch;
- pausar consumo;
- rejeitar novas solicitações com erro canônico retryable ou não;
- enfileirar dentro de limite governado;
- priorizar classes críticas;
- reduzir paralelismo;
- aplicar rate limit por originador ou capability.

Backpressure não pode criar espera ilimitada nem esconder saturação.

## 25. Load shedding

Quando capacidade segura for excedida, o Spider pode rejeitar trabalho antes de iniciar efeitos. A política deve declarar:

- classe protegida;
- critérios determinísticos;
- ordem de descarte;
- resposta canônica;
- retry-after ou orientação segura quando aplicável;
- métricas e alertas;
- proibição de discriminação por atributo não autorizado.

Execução aceita não deve ser descartada silenciosamente.

## 26. Rate limits e quotas

Limites possuem escopo, janela, burst, owner e comportamento de excedente. Podem ser aplicados por originador, capability, operation, Adapter ou classe.

Quota não implementa política bancária. Ela protege capacidade técnica.

Distribuição deve preservar consistência suficiente para não permitir abuso significativo nem bloquear indevidamente fluxo crítico.

## 27. Resiliência observável

Retry, circuit breaker, timeout, bulkhead e fallback técnico devem produzir sinais:

- policy e versão efetivas;
- decisão tomada;
- tentativa e budget restante;
- fase da falha;
- impacto no estado;
- resultado ou certainty;
- binding e capability afetados.

Fallback não pode fabricar outcome de negócio ou trocar destino fora das rotas publicadas.

## 28. Circuit breaker

Estados `CLOSED`, `OPEN` e `HALF_OPEN` devem ser observáveis por binding e operation. Transição deve registrar razão, amostra, janela, policy e instante.

Circuit aberto evita chamadas previstas pela policy, mas não prova indisponibilidade absoluta do destino. Reset manual é ação governada e auditada.

## 29. Timeouts e deadlines

Devem ser medidos:

- budget end-to-end;
- tempo em fila;
- tempo de execução do step;
- tempo do Adapter;
- tempo externo;
- backoff e retry;
- espera assíncrona;
- callback.

Timeout local após possível envio deve aumentar métrica de estado `UNKNOWN` e abrir reconciliação quando aplicável. Não deve ser agrupado apenas como indisponibilidade simples.

## 30. Filas, inbox, outbox e dead letters

Operação deve observar:

- profundidade e idade;
- taxa de entrada e saída;
- redelivery e duplicidade;
- processamento e falhas;
- itens bloqueados;
- dead letters por categoria;
- expiração;
- capacidade de recuperação;
- divergência entre estado e entrega.

Dead letter é estado operacional que exige owner, retenção e ação. Não é descarte definitivo automático.

## 31. Processos longos

Devem existir visões para:

- executions ativas por idade e estado;
- waits próximos do deadline;
- sinais esperados e recebidos;
- timers atrasados;
- callbacks pendentes;
- compensations ativas;
- reconciliações abertas;
- versões de release em uso por processos longos.

Depreciação de release deve considerar processos ainda vinculados a ela.

## 32. Reconciliação operacional

Cada `Reconciliation Case` possui categoria, severidade, owner, idade, evidências e ações permitidas.

Categorias iniciais:

- efeito externo desconhecido;
- callback ausente ou divergente;
- mensagem órfã;
- compensação falha;
- estado inconsistente;
- outbox inconclusiva;
- evidência ausente;
- snapshot divergente.

A ferramenta operacional não pode oferecer edição livre de estado. Toda ação é command governado, idempotente e auditado.

## 33. Runbooks

```text
Runbook
├── runbookCode
├── version
├── alertRefs[]
├── ownerRef
├── prerequisites
├── diagnosticSteps[]
├── safeActions[]
├── escalationPath
├── stopConditions[]
├── evidenceRequirements[]
├── rollbackOrRecoveryRefs[]
└── lastTestedAt
```

Runbook deve ser executável por operador autorizado, conter comandos seguros e declarar quando parar e escalar. Passo destrutivo ou irreversível exige controle reforçado.

## 34. Automação operacional

Automação pode:

- reiniciar worker sem estado local crítico;
- renovar lease expirado com fencing;
- escalar capacidade dentro de limites;
- pausar consumo;
- abrir incidente ou reconciliação;
- executar rollback previamente autorizado;
- rotacionar secret conforme policy;
- reprocessar entrega idempotente prevista.

Automação não pode:

- editar resultado ou estado histórico;
- selecionar rota não publicada;
- repetir operação com efeito sem garantia;
- ignorar autorização;
- desativar controles de segurança permanentemente;
- conectar legado real nesta fase.

## 35. Gestão de incidentes

### 35.1 Incident Record

```text
OperationalIncident
├── incidentId
├── severity
├── state
├── declaredAt
├── commanderRef
├── affectedCapabilities[]
├── affectedServiceClasses[]
├── affectedReleases[]
├── timelineRefs[]
├── actionRefs[]
├── communicationRefs[]
├── evidenceRefs[]
└── resolvedAt?
```

### 35.2 Estados

`DETECTED → DECLARED → MITIGATING → MONITORING → RESOLVED → REVIEWED`.

### 35.3 Papéis

Papéis lógicos podem incluir incident commander, operations lead, communications lead, subject matter expert e scribe. Uma pessoa pode acumular papéis em incidente pequeno, preservando atribuição.

## 36. Resposta

```text
Detectar → Qualificar impacto → Declarar
→ Conter → Mitigar → Recuperar
→ Monitorar → Encerrar → Aprender
```

Prioridade inicial é reduzir impacto sem destruir evidência ou criar efeito duplicado. Mudança emergencial continua versionada, autorizada e reversível.

## 37. Comunicação de incidente

Comunicações devem ser factuais, temporais e distinguir:

- fato confirmado;
- hipótese;
- impacto conhecido;
- escopo ainda investigado;
- ação em andamento;
- próximo update.

Dados sensíveis, topologia explorável e identidade indevida não devem ser expostos. Comunicação a clientes, parceiros ou autoridades segue owner e obrigação aplicáveis.

## 38. Post-incident review

A revisão deve ser sem culpabilização individual e orientada a controles. Deve registrar:

- linha do tempo;
- impacto e detecção;
- condições contribuintes;
- por que proteções não evitaram ou reduziram o evento;
- decisões e tradeoffs;
- eficácia de runbooks e comunicação;
- ações corretivas com owner e prazo;
- atualização de testes, alertas, policies e documentação.

“Erro humano” não é causa raiz suficiente.

## 39. Continuidade operacional

O modelo deve definir por classe:

- objetivo de recuperação;
- perda de dados tolerável;
- dependências críticas;
- modo degradado permitido;
- ordem de recuperação;
- capacidade mínima;
- comunicação e owners;
- testes periódicos.

Continuidade do Data Plane não depende da disponibilidade contínua do Control Plane, conforme SPIDER-ARCH-007.

## 40. Backup e restore operacional

Operação deve observar sucesso, idade, integridade e cobertura de backups. Restore deve ser testado e incluir prevenção de:

- reenvio indevido de outbox;
- reativação de lease antigo;
- execução duplicada de timer;
- perda de tombstone idempotente;
- ativação de release revogada;
- divergência entre estado e evidência.

Backup não é estratégia completa de alta disponibilidade.

## 41. Disaster recovery

Plano de DR deve declarar:

- evento de ativação;
- autoridade;
- região ou ambiente alternativo;
- dados e configurações necessários;
- sequência de failover;
- verificação de integridade;
- prevenção de split-brain;
- reconciliação após retorno;
- critérios de failback;
- evidências do exercício.

Escolha de regiões e tecnologia permanece para SPIDER-ARCH-011.

## 42. Critérios de prontidão operacional

Uma capability somente é elegível quando possuir:

- owner técnico e operacional;
- service class;
- SLIs e SLOs provisórios ou aprovados;
- métricas, logs e traces essenciais;
- dashboards e alertas acionáveis;
- runbooks testados;
- capacity model;
- policies de resiliência;
- reconciliação e suporte a incidentes;
- segurança e retenção aplicáveis;
- testes com Mocks e falhas simuladas.

## 43. Readiness review

Antes de ativar release relevante, revisar:

1. compatibilidade e integridade;
2. SLO e capacidade;
3. novos modos de falha;
4. alertas e runbooks;
5. dashboards e release markers;
6. rollback;
7. retenção e evidências;
8. segurança;
9. processos longos em versões anteriores;
10. cenários de fault injection aprovados.

Nesta fase, a revisão somente ativa simulação.

## 44. Fault injection

Mocks e infraestrutura de teste devem permitir injetar:

- latência e jitter;
- timeout antes e depois do envio;
- resposta inválida;
- indisponibilidade parcial e total;
- rate limit e saturação;
- duplicidade e reorder;
- callback ausente ou tardio;
- perda temporária de store;
- worker crash;
- snapshot inválido;
- secret ou certificado expirado;
- circuit breaker e retry storm;
- falha de compensação;
- divergência para reconciliação.

Injeção deve possuir escopo, owner, janela e kill switch. Não pode alcançar ambiente real nesta fase.

## 45. Testes de observabilidade

Devem comprovar:

- correlação do ingress ao Adapter;
- trace assíncrono e retry;
- ausência de dados sensíveis;
- métricas com cardinalidade controlada;
- cálculo de SLI e SLO;
- alertas de burn rate;
- dashboard e drill-down autorizados;
- health e readiness corretos;
- backpressure e load shedding;
- circuit, timeout e unknown;
- waits, callbacks e dead letters;
- reconciliação;
- declaração e timeline de incidente;
- runbook executável;
- restore e DR simulado;
- barreira Mock-first.

## 46. Governança da observabilidade

Schemas de logs, métricas, spans, alertas, dashboards, SLOs e runbooks são artefatos versionados. Mudanças incompatíveis devem preservar consumidores e histórico.

Novos atributos exigem owner, finalidade, classificação, cardinalidade e retenção. Dashboard sem owner ou alerta sem runbook deve ser rejeitado no gate aplicável.

## 47. Retenção dos sinais

Cada tipo possui política própria:

- métricas agregadas podem ter retenção diferente de séries granulares;
- logs de debug possuem retenção curta;
- traces podem usar sampling;
- auditoria e evidências seguem obrigações específicas;
- incidentes e postmortems seguem política organizacional;
- dados sensíveis permanecem minimizados em qualquer prazo.

Retenção longa não deve compensar ausência de agregação ou governança.

## 48. Neutralidade tecnológica

O modelo pode ser implementado por diferentes combinações de padrões e produtos. Formatos abertos e interoperáveis devem ser preferidos quando adequados, mas nenhum fornecedor integra o modelo conceitual.

OpenTelemetry, W3C Trace Context e formatos equivalentes podem ser referências técnicas; sua adoção física e perfis serão decididos posteriormente.

## 49. Estratégia Mock-first

Até a fase final:

- todos os destinos observados são Mocks;
- SLIs e SLOs são provisórios e calibrados por simulação;
- fault injection ocorre apenas em ambientes isolados;
- dashboards não contêm dado real;
- runbooks operam sobre componentes e bindings simulados;
- alertas e incidentes são exercitados em jogos de falha;
- capacity tests usam carga sintética;
- nenhum sinal depende de aplicação legada real.

Integração final deve adicionar observabilidade específica do binding sem alterar identidades, estados, Porta Universal ou sinais centrais.

## 50. Decisões arquiteturais consolidadas

1. Observabilidade é requisito arquitetural e operacional.
2. Logs, métricas, traces, eventos, auditoria e evidências são complementares.
3. Identidades de correlação possuem papéis distintos.
4. Telemetria é estruturada, minimizada e classificada.
5. Métricas evitam alta cardinalidade sensível.
6. Traces preservam causalidade síncrona e assíncrona.
7. Outcome de negócio não é falha técnica automaticamente.
8. Service classes organizam expectativas operacionais.
9. SLIs medem fronteiras explicitamente definidas.
10. SLOs numéricos dependem de baseline e aprovação.
11. Error budgets orientam mudança, não segurança ou integridade.
12. Health possui dimensões distintas.
13. Alertas são acionáveis, possuem owner e runbook.
14. Capacidade, backpressure e load shedding são governados.
15. Resiliência produz sinais e não cria fallback de negócio.
16. Processos longos e reconciliação possuem operação própria.
17. Incidentes preservam evidência e geram aprendizado.
18. Nesta fase, toda observabilidade é validada com Mocks e falhas simuladas.

## 51. Invariantes arquiteturais

1. Toda execução aceita é correlacionável ponta a ponta.
2. Nenhum sinal expõe secret ou credencial.
3. Nenhum payload integral é registrado por padrão.
4. Nenhum log substitui estado, auditoria ou evidência.
5. Nenhuma métrica usa identificador sensível de alta cardinalidade sem aprovação.
6. Nenhum outcome negativo delegado é contado automaticamente como erro técnico.
7. Nenhum SLO omite denominador, janela ou exclusões.
8. Nenhum error budget autoriza violação de segurança.
9. Nenhum alerta crítico existe sem owner e runbook.
10. Nenhum health check produz efeito de negócio.
11. Nenhum estado `UNKNOWN` é mascarado como sucesso ou falha simples.
12. Nenhuma backpressure cria espera ilimitada.
13. Nenhuma execução aceita é descartada silenciosamente.
14. Nenhum fallback seleciona destino fora da rota publicada.
15. Nenhuma reconciliação edita estado histórico livremente.
16. Nenhuma automação operacional ignora autorização.
17. Nenhum restore reenvia efeito sem idempotência.
18. Nenhum teste de falha alcança legado real nesta fase.
19. Nenhum dashboard desta fase contém dado real.
20. Trocar Mock por legado não altera o modelo central de observabilidade.

## 52. Pontos ainda abertos

| Tema | Questão a decidir |
|---|---|
| Telemetria | Stack de logs, métricas, traces e eventos |
| Collector | Agentes, gateways, buffering e backpressure |
| Sampling | Estratégia por criticidade, erro e volume |
| Métricas | Convenções, buckets, labels e retenção |
| Logs | Schema, indexação, tiers e acesso |
| Traces | Storage, links assíncronos e custo |
| SLOs | Valores, janelas e service classes definitivas |
| Alertas | Plataforma, roteamento, escalonamento e horários |
| Dashboards | Ferramenta, templates e ownership |
| Health | Contratos físicos de probes e agregação |
| Capacidade | Modelo, testes e autoscaling |
| Filas | Produtos, prioridades e quotas |
| Runbooks | Repositório, execução e testes |
| Incidentes | Integração com ITSM e comunicação |
| DR | RPO, RTO, regiões e autoridade de failover |
| Game days | Frequência, escopo e governança |
| Fase final | SLO e sinais adicionais de cada legado real |

## 53. Critérios de aceite

O SPIDER-ARCH-010 é considerado apto a orientar a próxima etapa quando:

1. sinais e identidades de correlação estiverem definidos;
2. logs, métricas, traces, auditoria e evidências estiverem separados;
3. classes, SLIs, SLOs e error budgets estiverem formalizados;
4. processos síncronos e assíncronos tiverem indicadores próprios;
5. health, alertas e dashboards estiverem especificados;
6. capacidade, saturação, backpressure e load shedding estiverem limitados;
7. retry, circuit breaker, timeout e dead letters forem observáveis;
8. processos longos e reconciliação estiverem operáveis;
9. runbooks, automação e incidentes estiverem governados;
10. continuidade, restore, DR e readiness review estiverem cobertos;
11. fault injection e testes puderem ser derivados;
12. Mocks e carga sintética permanecerem exclusivos nesta fase.

## 54. Próxima etapa recomendada

Antes de implementar, recomenda-se criar:

> **SPIDER-ARCH-011 — Topologia, Implantação, Escalabilidade e Alta Disponibilidade**

Esse documento deverá formalizar limites de implantação, monólito modular versus serviços, componentes lógicos, distribuição, isolamento, balanceamento, particionamento, autoscaling, alta disponibilidade, multi-zona, disaster recovery, configuração, deploy, rollback de runtime e critérios objetivos de decomposição.

A especificação continuará neutra a nuvem, orquestrador e fornecedor, usando somente ambientes isolados, Mocks e carga sintética nesta fase. Prompts de implementação permanecem separados em `SPIDER-PROMPT-NNN`. Legados reais continuam fora de escopo até a fase final.

---

## Apêndice — Alinhamento com SPIDER-ARCH-013 (não altera decisões históricas)

O **SPIDER-ARCH-013 — Console Operacional e Visualização** complementa este documento: o console operacional consome sinais/estados persistidos do Data Plane para observação humana, **sem** substituir a plataforma de métricas/SLO/alertas definida aqui. Observabilidade de produto (SLI/SLO) permanece fora do console 015; o console exibe apenas read models autorizados e redigidos. Ver `docs/architecture/SPIDER-ARCH-013-console-operacional-e-visualizacao.md`.
