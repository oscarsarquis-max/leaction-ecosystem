# SPIDER-ARCH-005 — Definição de Rotas, Execution Plan e Máquina de Estados

| Campo | Valor |
|---|---|
| Identificador | SPIDER-ARCH-005 |
| Título | Definição de Rotas, Execution Plan e Máquina de Estados |
| Status | Proposta arquitetural inicial |
| Predecessor | SPIDER-ARCH-004 — Schemas Canônicos, Resultados e Erros |
| Escopo | Especificação lógica normativa, sem implementação |

## 1. Objetivo

Formalizar a definição executável e determinística de rotas do Spider, a materialização de cada rota em um `Execution Plan` e as máquinas de estados da execução, dos steps e das interações externas.

Este documento estabelece:

- estrutura lógica, validação, publicação e imutabilidade de `Route Definition`;
- regras de compilação e fixação de versões no `Execution Plan`;
- dependências, sequência, paralelismo, joins e condições técnicas;
- estados, transições, tentativas e retomada segura;
- espera externa, expiração e reconciliação;
- falha parcial e compensação delegada;
- evidências mínimas e conformidade Mock-first.

Este documento não define classes, tabelas, endpoints, linguagem física de DSL, motor de workflow, produto de mensageria, protocolo de integração ou topologia de implantação. Não autoriza alteração do código de produção nem integração com legados reais.

### 1.1 Alinhamento CTX-003

Neste documento, `Execution Plan` significa o **plano técnico do Data Plane**, materializado depois
da resolução da route para uma execução específica. CTX-003 acrescenta antes dele o
`ContextExecutionPlan`, plano empresarial composto por Business Capabilities e normatizado em
SPIDER-ARCH-016.

```text
Intent → ContextExecutionPlan → Business Capabilities → Route
       → Execution Plan técnico deste documento → Engine
```

Os dois contratos não são sinônimos. Intent não seleciona diretamente a Route, e o plano
empresarial não contém adapter, endpoint ou protocolo.

## 2. Vocabulário normativo

Os termos “deve”, “não deve” e “somente” expressam requisitos arquiteturais. “Pode” expressa uma possibilidade admitida.

- **Route Definition**: definição governada, versionada e declarativa de um grafo técnico que materializa uma jornada.
- **Execution Plan**: materialização imutável de uma versão de rota para uma execução específica, com todas as versões e políticas efetivas fixadas.
- **Step**: unidade técnica de coordenação que aciona uma capacidade por uma porta de Adapter ou executa uma função técnica permitida.
- **Attempt**: tentativa individual de execução de um step; retries criam novas tentativas e não apagam as anteriores.
- **External Interaction**: interação de uma tentativa com um Mock Endpoint nesta fase e, somente na fase final, com um destino real.
- **Wait Condition**: condição governada que suspende o avanço até sinal autorizado, deadline ou ação operacional prevista.
- **Compensação delegada**: execução explícita de capacidade compensatória pertencente ao domínio responsável; não é rollback arbitrário produzido pela Engine.

## 3. Decisões centrais

1. Uma rota publicada é um grafo declarativo, versionado, validado, aprovado e imutável.
2. O `Execution Plan` é produzido deterministicamente a partir de uma única versão publicada de rota e do request validado.
3. Todas as referências necessárias à execução são resolvidas e fixadas antes do primeiro step.
4. A Engine pode sequenciar, paralelizar, aguardar e retomar somente comportamentos expressos na rota publicada.
5. Condições da rota avaliam dados canônicos e resultados delegados tipados; não implementam decisão bancária.
6. Toda mudança de estado é válida, persistida de forma atômica no controle técnico, temporalmente ordenável e auditável.
7. Retry cria nova tentativa; retomada continua a mesma execução; replay cria nova execução correlacionada, salvo reutilização idempotente de resultado já conhecido.
8. Falha parcial é representada explicitamente e nunca convertida silenciosamente em sucesso.
9. Compensação é explícita, limitada e delegada por capacidades governadas; não implica atomicidade distribuída.
10. Nesta fase, toda interação externa termina em Mock Endpoint, stub ou simulador contratual. Legados reais permanecem exclusivos da fase final.

## 4. Posição na arquitetura

```text
CanonicalExecutionRequest validado
        ↓
Route Resolver
        ↓ rota e versão exatas + justificativa
Route Definition publicada e imutável
        ↓ validação e materialização determinística
Execution Plan da execução
        ↓
Scheduler determinístico de steps
        ├── sequência
        ├── paralelismo e join
        ├── condições técnicas declaradas
        ├── espera e retomada
        └── falha e compensação delegada
        ↓ porta universal
Adapters → Mock Endpoints nesta fase
        ↓
CanonicalExecutionResult + evidências
```

O Route Resolver seleciona uma rota elegível; não executa steps. A `Route Definition` descreve possibilidades aprovadas; o `Execution Plan` fixa o caminho executável e as versões aplicáveis à ocorrência. O scheduler avança somente por transições válidas e dependências satisfeitas.

## 5. Route Definition

### 5.1 Estrutura lógica mínima

```text
RouteDefinition
├── identity
│   ├── routeCode
│   ├── version
│   ├── journeyRef
│   └── status
├── contracts
│   ├── inputContractRef
│   └── outputContractRef
├── applicability
│   ├── targetRef
│   ├── criteria[]
│   └── priority
├── graph
│   ├── entryStepRefs[]
│   ├── steps[]
│   ├── transitions[]
│   └── terminalDefinitions[]
├── policies
│   ├── executionPolicyRefs[]
│   ├── failurePolicyRef
│   └── retentionPolicyRef
└── governance
    ├── createdAt
    ├── approvedAt
    ├── publishedAt
    └── integrityRef
```

### 5.2 Identidade e ciclo de vida

| Campo | Obrigatório | Regra |
|---|---:|---|
| `routeCode` | Sim | Identificador semântico estável, sem localização física do destino |
| `version` | Sim | Versão imutável e compatível com o modelo definido no SPIDER-ARCH-002 |
| `journeyRef` | Sim | Referência exata à jornada materializada |
| `status` | Sim | Estado de governança, separado do estado de execução |

Uma versão de rota pode evoluir por `DRAFT → VALIDATED → APPROVED → PUBLISHED → DEPRECATED → RETIRED`. Apenas `PUBLISHED` é elegível para novas execuções. Depreciação impede seleção futura conforme política, mas não invalida planos já iniciados. Retirada não apaga definições nem evidências necessárias à reprodução e auditoria.

### 5.3 Aplicabilidade e resolução

`applicability` deve declarar target canônico, versões compatíveis, critérios determinísticos e prioridade explícita. Critérios podem consultar apenas fatos autorizados e tipados disponíveis no request, nas referências resolvidas ou em resultados de steps previstos.

São proibidos:

- seleção por ordem acidental de armazenamento;
- descoberta oportunista de endpoint ou destino;
- execução de código ou expressão não governada;
- inferência probabilística dentro da Engine;
- critérios que reproduzam elegibilidade, risco, preço, limite ou aprovação bancária;
- referência direta a host, URL, fila, tópico, WSDL, arquivo físico ou tecnologia do destino.

Ausência de rota produz erro canônico de resolução. Empate sem regra publicada produz resolução ambígua e rejeição segura; a Engine não escolhe arbitrariamente.

## 6. Step Definition

### 6.1 Estrutura lógica mínima

```text
StepDefinition
├── stepId
├── type
├── capabilityRef
├── operationRef
├── adapterBindingRef
├── inputMappingRef
├── inputContractRef
├── outputContractRef
├── dependencies[]
├── activationConditionRef?
├── completionConditionRef?
├── policyRefs
│   ├── timeoutPolicyRef
│   ├── retryPolicyRef
│   ├── resiliencePolicyRef
│   └── idempotencyPolicyRef
├── waitDefinitionRef?
├── compensationStepRef?
└── evidencePolicyRef
```

### 6.2 Tipos lógicos iniciais

| Tipo | Responsabilidade |
|---|---|
| `INVOKE` | Invocar operação canônica por Adapter |
| `TRANSFORM` | Aplicar mapeamento canônico publicado, sem regra bancária |
| `FORK` | Liberar ramos paralelos declarados |
| `JOIN` | Consolidar o estado técnico de dependências conforme política explícita |
| `WAIT` | Suspender até sinal autorizado, deadline ou reconciliação |
| `CALLBACK` | Entregar projeção governada de resultado |
| `COMPENSATE` | Invocar capacidade compensatória delegada |
| `TERMINATE` | Materializar resultado terminal permitido |

Os tipos são semânticos e não implicam componentes físicos separados. Novos tipos exigem versão compatível do metamodelo de rota e testes de conformidade.

### 6.3 Invariantes de step

1. `stepId` é único dentro da versão de rota.
2. Todo step alcançável possui caminho a um terminal ou a uma espera com expiração definida.
3. Step `INVOKE` e `COMPENSATE` usam binding de Adapter publicado; não chamam destino diretamente.
4. Entradas e saídas obedecem a contratos versionados.
5. Mapeamentos são explícitos, validados e não acessam dados fora do escopo autorizado.
6. Retry é proibido sem política publicada e sem semântica idempotente compatível.
7. Timeout do step não pode exceder o budget restante da execução.
8. Uma compensação referencia capacidade própria e contrato próprio; não é uma inversão automática.
9. Um step não cria dinamicamente outro step fora do grafo publicado.
10. Nesta fase, bindings externos apontam exclusivamente para Mocks, stubs ou simuladores.

## 7. Grafo, dependências e ordem

### 7.1 Modelo do grafo

A rota é um grafo direcionado. Ciclos são proibidos por padrão. Repetição controlada somente pode existir por construção específica, com limite de iterações, condição de saída, budget temporal e evidência; não pode ser obtida por aresta cíclica genérica.

Uma transição deve declarar:

| Campo | Semântica |
|---|---|
| `fromStepRef` | Origem da transição |
| `toStepRef` | Destino da transição |
| `onState` | Estado técnico que habilita avaliação |
| `conditionRef` | Condição publicada, quando necessária |
| `priority` | Ordem explícita quando mais de uma transição puder ser avaliada |
| `reasonCode` | Motivo normalizado registrado na decisão |

Se duas transições exclusivas permanecerem verdadeiras após prioridade e regras publicadas, a execução deve falhar de modo seguro por ambiguidade de definição.

### 7.2 Sequência

Um step torna-se `READY` somente quando todas as dependências exigidas atingirem os estados previstos e sua condição de ativação for verdadeira. A Engine não antecipa execução com base em provável sucesso de dependência.

### 7.3 Paralelismo

Ramos independentes podem executar em paralelo quando a rota os declarar. O paralelismo deve respeitar:

- limites de concorrência e bulkhead publicados;
- budget temporal da execução;
- isolamento de falhas;
- ordenação somente onde semanticamente necessária;
- ausência de escrita concorrente não coordenada sobre o mesmo dado técnico;
- idempotência individual de cada step.

A ordem física de conclusão de steps paralelos não pode alterar o significado do resultado. Quando a ordem for relevante, ela deve ser modelada como dependência.

### 7.4 Join

O join declara uma das políticas iniciais:

| Política | Liberação |
|---|---|
| `ALL_SUCCESS` | Todas as dependências terminam com sucesso |
| `ALL_TERMINAL` | Todas atingem estado terminal; resultados parciais são avaliados depois |
| `ANY_SUCCESS` | Ao menos uma conclui com sucesso; demais seguem política explícita de cancelamento ou conclusão |
| `QUORUM` | Quantidade publicada de sucessos é atingida |

`QUORUM` somente se aplica a responsabilidades tecnicamente equivalentes e não pode ser usado para votar ou fabricar decisão bancária. Cancelamento de ramo não implica reversão de efeito já produzido.

## 8. Condições e decisões

Condições são expressões declarativas, versionadas e livres de efeitos colaterais. Devem operar sobre valores tipados, possuir resultado booleano determinístico e registrar entradas referenciadas, versão e resultado da avaliação.

Uma condição pode:

- verificar estado técnico de dependências;
- inspecionar presença ou validade de dado canônico;
- comparar outcome delegado com valores previstos no schema do domínio;
- selecionar transição já aprovada;
- verificar deadline, tentativa ou budget operacional.

Uma condição não pode:

- calcular ou substituir regra bancária;
- alterar outcome recebido;
- consultar diretamente um legado;
- usar relógio, aleatoriedade ou estado externo não capturado no plano de modo não governado;
- executar script arbitrário;
- produzir novo caminho ausente da rota.

Quando um outcome de negócio determina o ramo, a decisão pertence ao sistema responsável; a Engine apenas reconhece o valor tipado e aplica a transição previamente definida.

## 9. Materialização do Execution Plan

### 9.1 Estrutura lógica

```text
ExecutionPlan
├── planId
├── executionId
├── createdAt
├── routeRef
├── journeyRef
├── contractRefs[]
├── adapterBindingRefs[]
├── effectivePolicyRefs[]
├── nodes[]
│   ├── stepId
│   ├── resolvedVersions
│   ├── effectiveInputs
│   ├── dependencies
│   ├── effectivePolicies
│   └── allowedTransitions
├── terminalDefinitions[]
├── integrityRef
└── planStatus
```

### 9.2 Processo determinístico

```text
1. Validar request, identidade, autorização e idempotência
2. Resolver rota publicada e registrar justificativa
3. Resolver versões exatas de contratos, mappings, policies e bindings
4. Validar compatibilidade Engine–Adapter e schemas
5. Validar grafo, alcançabilidade, joins, waits e terminais
6. Calcular policies efetivas dentro dos limites governados
7. Materializar nodes e transições permitidas
8. Calcular integridade e persistir o plano
9. Transicionar PLANNED → RUNNING
```

Falha em qualquer etapa anterior à persistência integral do plano impede o início dos steps. A materialização não chama Adapter nem destino externo.

### 9.3 Fixação de versões

O plano fixa, no mínimo:

- rota e jornada;
- schemas de request, inputs, outputs, outcome e erros;
- mappings e condições;
- bindings e contrato da porta de Adapter;
- políticas de timeout, retry, resiliência, idempotência, espera, callback e retenção;
- definições de compensação;
- versão do interpretador da definição, quando relevante à reprodução.

Mudança ou publicação posterior não altera um plano materializado. Retomada usa o mesmo plano. Se uma vulnerabilidade ou risco exigir bloqueio, a execução é interrompida por ação governada e auditada; o plano não é reescrito silenciosamente.

### 9.4 Integridade

O plano deve possuir referência de integridade sobre sua representação canônica e dependências relevantes. A Engine deve detectar divergência antes da retomada. Detecção de plano corrompido produz falha técnica segura e intervenção operacional; não autoriza recompilação automática sobre versões novas.

## 10. Máquina de estados da execução

### 10.1 Estados

| Estado | Semântica |
|---|---|
| `RECEIVED` | Request recebido e identificado, ainda não aceito para execução |
| `VALIDATED` | Estrutura, identidade, autorização, referências e idempotência validadas |
| `RESOLVED` | Rota publicada e versão exata selecionadas |
| `PLANNED` | Plano íntegro e persistido antes de qualquer step |
| `RUNNING` | Um ou mais steps podem avançar ou estão em execução |
| `WAITING_EXTERNAL` | Progresso suspenso aguardando sinal externo governado |
| `COMPENSATING` | Compensações delegadas aprovadas estão em andamento |
| `SUCCEEDED` | Resultado técnico terminal de sucesso |
| `PARTIALLY_SUCCEEDED` | Efeitos ou resultados válidos coexistem com falhas não revertidas |
| `COMPENSATED` | Falha ocorreu e todas as compensações exigidas terminaram conforme contrato |
| `FAILED` | Falha terminal técnica sem condição de continuação automática |
| `TIMED_OUT` | Deadline terminal da execução expirou |
| `REJECTED` | Request não aceito antes da execução de steps |
| `CANCELLED` | Interrupção autorizada concluiu segundo política, sem alegar reversão automática |

Todos os estados terminais são imutáveis: `SUCCEEDED`, `PARTIALLY_SUCCEEDED`, `COMPENSATED`, `FAILED`, `TIMED_OUT`, `REJECTED` e `CANCELLED`.

### 10.2 Transições principais

```text
RECEIVED → VALIDATED → RESOLVED → PLANNED → RUNNING → SUCCEEDED
    │           │          │          │          ├── WAITING_EXTERNAL
    │           │          │          │          ├── COMPENSATING
    │           │          │          │          ├── PARTIALLY_SUCCEEDED
    │           │          │          │          ├── FAILED
    │           │          │          │          ├── TIMED_OUT
    └───────────┴──────────┴──────────┴──────────→ REJECTED

WAITING_EXTERNAL → RUNNING | COMPENSATING | FAILED | TIMED_OUT | CANCELLED
COMPENSATING → COMPENSATED | PARTIALLY_SUCCEEDED | FAILED | TIMED_OUT
RUNNING → CANCELLED somente por política e autorização explícitas
```

`REJECTED` somente ocorre antes do primeiro efeito externo. Depois de iniciados steps, invalidação técnica produz `FAILED`, `TIMED_OUT`, `CANCELLED`, compensação ou sucesso parcial, conforme evidências reais.

### 10.3 Invariantes de transição

1. Toda transição declara estado anterior, novo estado, instante, versão, motivo, ator lógico e evidência.
2. Escritas concorrentes usam controle que impeça dupla transição incompatível.
3. Estado terminal não retorna a estado ativo.
4. `SUCCEEDED` exige todos os critérios de sucesso terminal da rota.
5. `PARTIALLY_SUCCEEDED` exige evidência dos resultados preservados e das falhas ou compensações incompletas.
6. `COMPENSATED` não significa que o mundo externo voltou exatamente ao estado anterior; significa que as capacidades compensatórias previstas concluíram.
7. `TIMED_OUT` não presume cancelamento do trabalho externo; interações inconclusivas exigem reconciliação.
8. Resultado bancário negativo pode terminar tecnicamente em `SUCCEEDED`.
9. Falha de callback não altera retrospectivamente o resultado principal, mas permanece como condição operacional observável.

## 11. Máquina de estados do step

### 11.1 Estados

| Estado | Semântica |
|---|---|
| `PENDING` | Dependências ainda não satisfeitas |
| `READY` | Dependências e condição satisfeitas; apto ao agendamento |
| `RUNNING` | Tentativa em execução |
| `WAITING_EXTERNAL` | Operação aceita, aguardando conclusão ou sinal externo |
| `SUCCEEDED` | Resultado técnico do step aceito e validado |
| `FAILED` | Falha terminal do step segundo sua política |
| `SKIPPED` | Step não aplicável por condição publicada |
| `TIMED_OUT` | Deadline do step expirou |
| `CANCELLING` | Cancelamento solicitado e ainda inconclusivo |
| `CANCELLED` | Cancelamento concluído segundo a garantia disponível |
| `COMPENSATING` | Capacidade compensatória associada em execução |
| `COMPENSATED` | Compensação prevista concluída |
| `COMPENSATION_FAILED` | Compensação prevista falhou definitivamente |

### 11.2 Transições

```text
PENDING → READY → RUNNING → SUCCEEDED
    │        │         ├── WAITING_EXTERNAL → RUNNING | SUCCEEDED | FAILED | TIMED_OUT
    │        │         ├── FAILED
    │        │         ├── TIMED_OUT
    │        │         └── CANCELLING → CANCELLED | FAILED
    │        └────────→ SKIPPED
    └────────────────→ SKIPPED

SUCCEEDED → COMPENSATING → COMPENSATED | COMPENSATION_FAILED
```

Retry não move `FAILED` de volta a `RUNNING`. Enquanto a política permitir retry, a tentativa falha e o step permanece em estado ativo apropriado, criando-se nova tentativa. `FAILED` é atribuído somente quando não existe nova tentativa automática válida.

## 12. Tentativas, retry, retomada e replay

### 12.1 Attempt

Cada tentativa deve registrar:

- `attemptId`, `stepId`, número ordinal e causa;
- início, deadline, término e duração observada;
- Adapter e versões de contrato utilizados;
- chave idempotente e garantia declarada;
- estado e erro normalizado;
- referências de request e response minimizados;
- interação externa e trace relacionados.

### 12.2 Retry

Retry é uma nova tentativa do mesmo step na mesma execução e mesmo plano. Somente ocorre quando:

1. o erro é tecnicamente retryable;
2. a política publicada permite;
3. a operação admite repetição segura;
4. o budget de tentativas e tempo não foi esgotado;
5. circuit breaker, rate limit e bulkhead permitem;
6. não há evidência de conclusão externa incompatível.

### 12.3 Retomada

Retomada continua a mesma execução após espera, reinício técnico ou intervenção prevista. Deve carregar o mesmo `executionId`, plano e versões, revalidar integridade, adquirir controle exclusivo e reconstruir o estado somente de registros persistidos. Steps concluídos não são repetidos, salvo protocolo idempotente explícito de reconciliação.

### 12.4 Replay

Replay é nova execução correlacionada, com novo `executionId`, motivação e autorização próprias. Não apaga nem altera a execução original. Pode usar nova versão de rota apenas quando isso for intenção explícita, autorizada e auditada. Replay não é mecanismo oculto de retry.

## 13. Espera externa e processos longos

### 13.1 Wait Definition

Toda espera deve declarar:

| Campo | Regra |
|---|---|
| `waitType` | Evento, callback, polling governado, timer ou ação operacional prevista |
| `correlationRuleRef` | Regra de correlação exata e autorizada |
| `acceptedSignalContractRef` | Contrato e versão do sinal aceito |
| `deadline` | Prazo máximo dentro do deadline da execução |
| `resumeTransitionRef` | Transição permitida após validação |
| `expiryTransitionRef` | Transição em expiração |
| `deduplicationPolicyRef` | Tratamento de sinais repetidos |
| `securityPolicyRef` | Autenticação, autorização e prevenção de replay |

URL livre, tópico improvisado ou callback não governado não constitui definição válida.

### 13.2 Sinais e retomada

Um sinal externo deve ser autenticado, autorizado, validado por schema, correlacionado e deduplicado antes de mudar estado. Sinal tardio após terminalização não reabre a execução; é registrado para reconciliação. Sinais concorrentes são ordenados por transição atômica e os perdedores permanecem evidenciados.

### 13.3 Expiração e resultado desconhecido

Timeout local não prova que o destino não executou. Quando o resultado externo for desconhecido, o step e a execução devem refletir incerteza por erro e evidência, e a política pode exigir consulta idempotente ou reconciliação. A Engine não repete operação com efeito apenas para descobrir seu resultado.

## 14. Falha parcial

Existe falha parcial quando pelo menos um resultado ou efeito válido permanece e um ou mais objetivos técnicos exigidos não foram concluídos ou compensados.

A política de falha da rota deve declarar, por step ou grupo:

- se a falha é fatal, tolerada ou condiciona join;
- se novos ramos podem iniciar;
- se ramos em andamento devem concluir, ser cancelados ou ignorados;
- quais resultados podem compor saída parcial;
- quais compensações são exigidas;
- qual terminal é permitido;
- quais alertas e ações operacionais são necessários.

O estado `PARTIALLY_SUCCEEDED` deve incluir outcome técnico `PARTIAL`, erros canônicos, resultados válidos minimizados e evidências das pendências. Não pode mascarar falha obrigatória nem reinterpretar outcome de negócio.

## 15. Compensação delegada

### 15.1 Princípio

O Spider coordena capacidades compensatórias publicadas pelo domínio responsável. Ele não desfaz transações externas por manipulação direta de dados e não promete transação distribuída exactly-once.

### 15.2 Requisitos

Uma definição compensatória deve declarar:

- step original e efeito que pode ser compensado;
- capacidade, operação e Adapter de compensação;
- contrato de entrada derivado de referências e resultados autorizados;
- condições de aplicabilidade;
- ordem em relação a outras compensações;
- idempotência, timeout e retry próprios;
- resultados possíveis, inclusive “não reversível”;
- owner e procedimento de reconciliação.

Compensações são executadas, por padrão, na ordem inversa das dependências efetivadas, salvo ordem explícita aprovada. Apenas steps com efeito confirmado e compensação aplicável entram no conjunto. Falha de compensação produz `COMPENSATION_FAILED` no step e terminal `PARTIALLY_SUCCEEDED` ou `FAILED` na execução, conforme efeitos preservados e política publicada.

## 16. Cancelamento

Cancelamento é solicitação técnica, não garantia automática de reversão. Deve ser autenticado, autorizado, idempotente e permitido pela rota e pelo estado atual.

- steps ainda não iniciados podem ser marcados `CANCELLED` ou `SKIPPED` conforme semântica;
- tentativa em andamento recebe cancelamento somente se Adapter e destino declararem suporte;
- conclusão concorrente vence ou perde conforme transição atômica registrada;
- efeitos já confirmados exigem compensação explícita, quando existente;
- destino sem garantia de cancelamento gera reconciliação, não falsa confirmação.

## 17. Idempotência e concorrência

O controle de execução deve impedir que múltiplos workers avancem o mesmo step de forma incompatível. A estratégia física permanece em aberto, mas a semântica exige:

1. aquisição exclusiva ou transição condicional versionada;
2. gravação durável da intenção técnica antes de interação quando necessário;
3. chave idempotente estável por operação lógica;
4. registro de tentativa antes de retry;
5. inbox/deduplicação para sinais e callbacks;
6. outbox ou mecanismo equivalente quando publicação e estado precisarem de consistência;
7. reconciliação de interações cujo resultado seja desconhecido.

Nenhum mecanismo autoriza afirmar exactly-once além da garantia demonstrável de toda a cadeia. O objetivo é efeito logicamente deduplicado e comportamento recuperável.

## 18. Budgets temporais e resiliência

O deadline da execução é absoluto. Cada step recebe budget compatível com o tempo restante; retry, espera, backoff, callback e compensação consomem budgets próprios governados.

Regras mínimas:

- timeout de transporte não substitui deadline do step;
- timeout do step não excede deadline da execução;
- backoff não ultrapassa a próxima oportunidade válida;
- retry storm deve ser evitado por jitter governado, circuit breaker, rate limit e bulkhead;
- paralelismo não elimina limites por destino;
- expiração deve produzir transição persistida e evidência;
- relógios físicos não definem ordem causal isoladamente; versões e sequências de transição também são registradas.

## 19. Relação com CanonicalExecutionResult

O terminal da execução deve ser projetado de modo coerente no contrato do SPIDER-ARCH-004:

| Estado terminal | `technicalStatus` esperado |
|---|---|
| `SUCCEEDED` | `SUCCESS` |
| `PARTIALLY_SUCCEEDED` | `PARTIAL` |
| `COMPENSATED` | `FAILURE` ou outcome específico compatível; nunca `SUCCESS` enganoso |
| `FAILED` | `FAILURE` |
| `TIMED_OUT` | `FAILURE` |
| `REJECTED` | `REJECTED` |
| `CANCELLED` | `FAILURE` ou status futuro versionado específico |

Estados não terminais `RUNNING`, `WAITING_EXTERNAL` e `COMPENSATING` projetam `PENDING`. A evolução de enums deve seguir as regras de compatibilidade do SPIDER-ARCH-004.

## 20. Evidências e observabilidade

Devem existir evidências correlacionáveis para:

- resolução da rota, candidatos e motivo normalizado;
- versão e integridade da Route Definition e do Execution Plan;
- transições da execução e dos steps;
- avaliação de condições e joins;
- agendamento, tentativas, retries e budgets;
- invocações de Adapter e interações externas;
- sinais de espera, deduplicação, expiração e retomada;
- decisões de falha parcial, cancelamento e compensação;
- resultados, erros e callbacks.

Métricas, logs e traces não substituem o histórico de controle. Payloads e resultados devem ser minimizados, mascarados e referenciados conforme classificação, autorização e retenção. Endereço físico, credenciais e detalhes proprietários ficam em evidência protegida ou configuração de ambiente, nunca na rota canônica.

## 21. Neutralidade tecnológica e comunicação universal

A semântica deste documento independe de HTTP, REST, SOAP, mensageria, arquivo, banco de dados, RPC ou tecnologia proprietária.

```text
Step canônico
    ↓ AdapterBindingRef
Porta universal Engine–Adapter
    ├── Adapter REST/HTTP ─────► Mock REST nesta fase
    ├── Adapter SOAP/XML ──────► Mock SOAP nesta fase
    ├── Adapter mensageria ────► Simulador de fila/evento nesta fase
    ├── Adapter arquivo ───────► Simulador batch/arquivo nesta fase
    ├── Adapter de dados ──────► Simulador controlado nesta fase
    └── Adapter específico ────► Simulador de protocolo nesta fase
```

API é uma possibilidade de integração, não decisão universal. A `Route Definition` identifica capacidade, operação e binding lógico; detalhes físicos pertencem ao Adapter e à configuração governada por ambiente.

## 22. Estratégia Mock-first e fase final

Até a fase final, todos os testes e execuções devem usar Mock Endpoints, stubs ou simuladores contratuais. O conjunto deve representar:

- sucesso técnico e outcome de negócio positivo ou negativo;
- falha antes, durante e depois do envio;
- latência, timeout e resultado desconhecido;
- indisponibilidade, rate limit e circuito aberto;
- resposta inválida e incompatibilidade de versão;
- repetição idempotente e conflito de chave;
- paralelismo, conclusão fora de ordem e joins;
- aceitação assíncrona, callbacks duplicados, tardios ou ausentes;
- retomada após reinício;
- falha parcial, cancelamento e compensação bem-sucedida ou falha.

Os simuladores não definem a arquitetura e não devem induzir acoplamento a REST ou a qualquer tecnologia específica. Na fase final, cada legado real será certificado contra os mesmos contratos e cenários aplicáveis. A troca de Mock por destino real atrás do Adapter não pode alterar a Engine, o Contrato Canônico, a Route Definition ou a máquina de estados.

## 23. Validação de Route Definition

Antes de publicação, uma rota deve passar por validações automatizáveis de:

1. identidade, versão, jornada e contratos existentes;
2. grafo bem formado, steps únicos e referências válidas;
3. alcançabilidade de todos os steps e terminais;
4. ausência de ciclos genéricos e esperas sem expiração;
5. dependências e joins coerentes;
6. condições determinísticas, tipadas e sem efeitos colaterais;
7. bindings e versões compatíveis de Adapter;
8. schemas e mappings compatíveis entre steps;
9. políticas de retry compatíveis com idempotência;
10. budgets temporais finitos e coerentes;
11. falhas, terminais e compensações definidos;
12. ausência de regra bancária e de endereço físico no núcleo;
13. minimização e classificação de dados;
14. conformidade integral com Mock-first nesta fase;
15. reprodutibilidade do Execution Plan esperado.

Publicação deve falhar se houver ambiguidade ou incompatibilidade. Warning não substitui requisito normativo.

## 24. Testes de conformidade

A suíte derivada deste documento deve cobrir, no mínimo:

- seleção determinística e rejeição de empate;
- fixação e integridade de versões;
- sequência, fork, paralelismo e cada política de join;
- condições verdadeiras, falsas, inválidas e ambíguas;
- cada transição válida e rejeição de transição inválida;
- concorrência de workers sobre o mesmo step;
- retry seguro, esgotamento e conflito idempotente;
- reinício entre persistência e interação externa;
- espera, sinal válido, duplicado, inválido e tardio;
- timeout com resultado externo desconhecido;
- falha parcial e projeção correta do resultado;
- compensação completa, parcial, não aplicável e falha;
- cancelamento antes, durante e depois de efeito confirmado;
- proteção de evidências e ausência de dados sensíveis em erro público;
- equivalência contratual entre diferentes tecnologias simuladas de Adapter;
- substituibilidade futura Mock–legado sem mudança do núcleo.

Nesta fase, a suíte é executada exclusivamente contra Mocks, stubs e simuladores controlados.

## 25. Decisões arquiteturais consolidadas

1. `Route Definition` é grafo declarativo, governado, versionado e imutável após publicação.
2. `Execution Plan` materializa uma rota para uma execução e fixa todas as versões antes do primeiro step.
3. A Engine não cria caminhos, steps ou decisões ausentes da rota publicada.
4. Sequência, paralelismo, join, espera e compensação são construções explícitas.
5. Condições são determinísticas, tipadas, sem efeitos colaterais e não contêm regra bancária.
6. Estados da execução, steps, tentativas e interações são distintos e correlacionados.
7. Transições são atômicas no controle técnico, auditáveis e irreversíveis após terminalização.
8. Retry, retomada e replay possuem semânticas distintas.
9. Espera externa exige contrato, segurança, correlação, deadline e deduplicação governados.
10. Timeout não presume ausência de efeito externo.
11. Falha parcial é explícita e não pode ser mascarada como sucesso.
12. Compensação é capacidade delegada, não rollback automático nem garantia de atomicidade distribuída.
13. Cancelamento não promete reversão de efeitos já confirmados.
14. O scheduler respeita idempotência, concorrência, resiliência e budget absoluto.
15. A definição lógica é neutra a protocolo, framework, produto e topologia.
16. API é opção; a comunicação universal permanece baseada em contrato canônico e Adapters.
17. Nesta fase, Adapters usam exclusivamente Mocks, stubs e simuladores contratuais.
18. Legados reais somente entram na fase final e não podem exigir mudança da Engine ou dos contratos canônicos.

## 26. Invariantes arquiteturais

1. Nenhum step inicia antes da persistência íntegra do `Execution Plan`.
2. Toda execução usa exatamente uma versão publicada de rota.
3. Toda dependência resolvida possui versão exata e reproduzível.
4. Nenhum step chama diretamente endpoint, fila, arquivo, banco ou legado.
5. Todo caminho executado existe na rota publicada.
6. Todo step ativo é alcançável e possui terminal ou espera com prazo.
7. Toda condição é determinística e sua avaliação é evidenciada.
8. Retry nunca ocorre sem política e idempotência compatíveis.
9. Tentativa anterior nunca é apagada por retry ou retomada.
10. Estado terminal nunca é reaberto.
11. Sinal externo nunca altera estado sem autenticação, validação, correlação e deduplicação.
12. Timeout não autoriza repetição cega de operação com efeito.
13. Compensação somente executa capacidade publicada e aplicável.
14. `COMPENSATED` não equivale a sucesso original nem prova restauração perfeita.
15. Resultado parcial identifica efeitos preservados e falhas remanescentes.
16. Outcome de negócio delegado não é recriado ou reinterpretado pela Engine.
17. Particularidades de transporte permanecem no Adapter.
18. Nenhum legado real é conectado antes da fase final.
19. Mock e destino real devem cumprir a mesma porta e os mesmos testes aplicáveis.
20. Trocar o destino atrás do Adapter não altera rota, plano, Engine ou Contrato Canônico.

## 27. Pontos ainda abertos

| Tema | Questão a decidir |
|---|---|
| Representação física | JSON/YAML ou outro formato, schema da DSL e canonicalização |
| Expressões | Linguagem segura de condições e mappings, tipos e sandbox |
| Compilador | Versionamento, validação, assinatura e compatibilidade do materializador |
| Persistência | Modelo físico de plano, estados, attempts, locks e snapshots |
| Concorrência | Optimistic locking, leases, fencing tokens e recuperação de worker |
| Entrega | Outbox/inbox, garantias por transporte e reconciliação |
| Scheduling | Filas, prioridades, fairness, backpressure e isolamento por tenant/domínio |
| Timers | Serviço de timers, precisão, escala, clock skew e recuperação |
| Eventos | Envelope canônico, CloudEvents/AsyncAPI e ordenação |
| Cancelamento | Matriz de garantias por modalidade de Adapter |
| Compensação | Catálogo, owners, irreversibilidade e tratamento operacional |
| Falha parcial | Taxonomia definitiva de terminais e projeção no outcome canônico |
| Reprocessamento | Políticas de replay, autorização e escolha explícita de versão |
| Operação | Pausa, retomada assistida, override controlado e segregação de funções |
| Retenção | Histórico de estado, snapshots, evidências e direito de descarte |
| Test harness | Formato dos cenários, relógio virtual e simuladores multi-protocolo |
| Topologia | Monólito modular ou serviços, particionamento e alta disponibilidade |
| Fase final | Inventário e certificação individual dos legados e seus Adapters |

## 28. Critérios de aceite

O SPIDER-ARCH-005 é considerado apto a orientar a próxima etapa quando:

1. Route Definition, Execution Plan, Step e Attempt estiverem semanticamente separados;
2. a estrutura mínima da rota e do plano estiver aceita;
3. fixação de versões e integridade antes da execução estiverem inequívocas;
4. sequência, paralelismo, joins e condições tiverem regras determinísticas;
5. máquinas de estados da execução e do step estiverem definidas;
6. retry, retomada e replay estiverem diferenciados;
7. espera externa, sinais, deadline e reconciliação estiverem formalizados;
8. falha parcial, cancelamento e compensação delegada estiverem explicitamente limitados;
9. a neutralidade tecnológica e a porta universal Engine–Adapter estiverem preservadas;
10. API permanecer uma opção, sem se tornar premissa arquitetural;
11. Mock-first e o adiamento dos legados reais à fase final estiverem preservados;
12. a suíte mínima de conformidade puder ser derivada sem implementação prematura.

## 29. Próxima etapa recomendada

Antes de implementar, recomenda-se criar:

> **SPIDER-ARCH-006 — Protocolo Universal Engine–Adapter e Perfis de Integração**

Esse documento deverá formalizar a porta lógica de invocação, capabilities declaradas por Adapter, resultados imediatos e assíncronos, normalização de erros, idempotência, segurança, evidências e perfis de transporte para REST/HTTP, SOAP/XML, mensageria, arquivo, dados e protocolos específicos.

Os perfis deverão ser certificados inicialmente apenas com Mocks, stubs e simuladores. Legados reais permanecerão fora do escopo até a fase final.

Schemas físicos, código e documentos `SPIDER-PROMPT-NNN` somente devem ser produzidos após a aprovação da sequência arquitetural aplicável. Prompts de implementação permanecem numerados e separados dos documentos `SPIDER-ARCH-NNN`.
