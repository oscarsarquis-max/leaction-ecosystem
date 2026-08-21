# SPIDER-ARCH-012 — Estratégia de Testes, Certificação e Qualidade Arquitetural

| Campo | Valor |
|---|---|
| Identificador | SPIDER-ARCH-012 |
| Título | Estratégia de Testes, Certificação e Qualidade Arquitetural |
| Status | Proposta arquitetural inicial |
| Predecessor | SPIDER-ARCH-011 — Topologia, Implantação, Escalabilidade e Alta Disponibilidade |
| Escopo | Especificação lógica normativa, sem implementação |

## 1. Objetivo

Formalizar a estratégia de testes, certificação e qualidade arquitetural do Spider. Este documento define portfólio de testes, níveis, responsabilidades, ambientes, dados sintéticos, simuladores, conformidade de contratos, propriedades, cenários assíncronos, segurança, performance, resiliência, fault injection, compatibilidade, certificação de Adapters e gates de promoção.

O objetivo é produzir evidência objetiva de que o Spider executa definições publicadas de forma determinística, segura, recuperável, observável e tecnologicamente neutra.

Este documento não escolhe framework, linguagem de teste, pipeline, ferramenta de qualidade, produto de virtualização, plataforma de carga ou fornecedor. Não autoriza implementação nem conexão com legados reais.

## 2. Vocabulário normativo

Os termos “deve”, “não deve” e “somente” expressam requisitos arquiteturais. “Pode” expressa possibilidade admitida.

- **Test Case**: caso com precondições, estímulo, resultado esperado e evidências.
- **Scenario**: fluxo composto que pode atravessar múltiplos componentes e estados.
- **Test Oracle**: mecanismo que determina o resultado esperado.
- **Conformance Suite**: conjunto normativo aplicável a todo produtor ou consumidor de um contrato.
- **Certification**: decisão governada baseada em evidências de conformidade e qualidade.
- **Quality Gate**: condição obrigatória para promoção ou ativação.
- **Test Harness**: infraestrutura reutilizável para executar cenários e coletar evidências.
- **Fault Injection**: introdução controlada de falha para validar comportamento.
- **Golden Dataset**: conjunto versionado de inputs e outputs esperados.
- **Property-based Test**: teste de invariantes sobre ampla geração de casos.
- **Mutation Test**: avaliação da capacidade da suíte detectar alterações defeituosas.

## 3. Decisões centrais

1. Testabilidade é requisito de arquitetura e deve existir em contratos, estados, Adapters e simuladores.
2. A estratégia combina testes rápidos e isolados com testes integrados, de propriedades e cenários ponta a ponta.
3. Contratos canônicos e a Porta Universal possuem suítes de conformidade independentes de tecnologia.
4. Mocks e simuladores devem reproduzir contratos e modos de falha, não a implementação interna de legados.
5. Resultados esperados são derivados de definições publicadas e oráculos determinísticos.
6. Testes devem distinguir falha técnica, rejeição, timeout, estado inconclusivo e outcome de negócio delegado.
7. Segurança, privacidade, resiliência, performance e recuperação integram os gates de qualidade.
8. Evidências de teste são versionadas e vinculadas aos hashes dos artefatos certificados.
9. Nenhum ambiente de teste usa credencial, endpoint ou dado real antes da fase final.
10. Certificação final de legado reutiliza a mesma suíte aplicável usada contra simuladores.

## 4. Princípios

1. Testar comportamento observável, não detalhes desnecessários de implementação.
2. Favorecer testes determinísticos e reproduzíveis.
3. Controlar tempo, aleatoriedade e concorrência nos testes.
4. Falhar rápido em contrato e manter diagnóstico suficiente.
5. Evitar dependência excessiva de testes ponta a ponta frágeis.
6. Manter dados de teste sintéticos, mínimos e versionados.
7. Tornar falhas, latência e duplicidade injetáveis.
8. Testar caminhos negativos e recuperação com a mesma prioridade dos caminhos felizes.
9. Garantir isolamento e limpeza entre execuções.
10. Preservar evidências sem expor dados sensíveis.

## 5. Portfólio de testes

```text
Testes estáticos e de arquitetura
        ↓
Testes de unidade e propriedades
        ↓
Testes de contrato e conformidade
        ↓
Testes de módulo/componente
        ↓
Testes de integração com simuladores
        ↓
Testes de cenário e ponta a ponta simulados
        ↓
Performance, segurança, resiliência e recuperação
        ↓
Certificação de release e Adapter
        ↓ somente na fase final
Certificação de binding com legado real
```

Os níveis se complementam; um teste mais amplo não substitui evidência de níveis inferiores.

## 6. Testes estáticos

Devem cobrir, conforme artefato:

- sintaxe e schema;
- dependências proibidas entre módulos;
- referências e versões;
- compatibilidade;
- secrets e dados sensíveis;
- vulnerabilidades conhecidas;
- licenças e proveniência;
- complexidade e padrões críticos;
- contratos não documentados;
- código morto ou configuração órfã;
- mappings e expressões inseguras;
- migrations incompatíveis.

Análise estática não substitui execução de testes.

## 7. Testes de arquitetura

Regras arquiteturais devem ser verificáveis automaticamente quando possível:

- Engine não depende de implementação de Adapter;
- domínio contextual não depende de transporte;
- módulos não acessam internals alheios;
- nenhum endpoint físico aparece na Route Definition;
- nenhum secret entra em artefato governado;
- regras bancárias não aparecem na Engine ou mappings;
- Control Plane não participa de cada step;
- Adapters implementam Porta Universal;
- persistência de negócio não é criada no Spider;
- bindings desta fase apontam somente para Mocks.

## 8. Testes de unidade

Unidades devem ser pequenas, rápidas e independentes de rede, relógio real e storage externo. Cobrem:

- validações;
- mappings;
- canonicalização;
- fingerprint idempotente;
- state transitions;
- conditions;
- error mappings;
- policy calculations;
- authorization decisions;
- retention calculations;
- SLI calculations.

Cobertura de linha isolada não demonstra qualidade. Caminhos e invariantes críticos devem possuir assertions semânticas.

## 9. Testes de propriedades

Propriedades iniciais:

1. mesma entrada canônica e mesmas versões produzem o mesmo plano;
2. serialização e desserialização preservam significado;
3. fingerprint é estável para campos equivalentes;
4. mesma idempotency key não aceita fingerprint diferente;
5. estado terminal nunca retorna a estado ativo;
6. retry nunca apaga attempt anterior;
7. mapping não produz campo fora do schema;
8. classificação de dado nunca é enfraquecida por transformação;
9. timeout efetivo não excede deadline;
10. nenhuma rota válida contém step sem terminal ou wait finito.

Geração deve respeitar schemas e também produzir casos inválidos próximos aos limites.

## 10. Mutation testing

Mutation testing pode ser exigido para componentes críticos, como:

- state machines;
- authorization;
- idempotência;
- canonicalização;
- mappings de erro;
- cálculo de deadline;
- compensação;
- retenção e masking.

Mutantes sobreviventes devem ser analisados; meta numérica isolada não substitui relevância dos cenários.

## 11. Testes de contrato canônico

A suíte do Contrato Canônico deve validar:

- versões suportadas e incompatíveis;
- campos obrigatórios;
- tipos, limites e formatos;
- canonicalData por operation;
- identity e correlation;
- policies por referência;
- callbackRef governado;
- resultado imediato e assíncrono;
- technicalStatus versus businessOutcome;
- CanonicalError;
- evidências e referências;
- evolução compatível.

Produtor e consumidor devem executar a mesma suíte aplicável.

## 12. Testes da Route Definition

Devem validar:

- identidade, jornada e contracts;
- graph bem formado;
- dependências e alcançabilidade;
- ausência de ciclos genéricos;
- conditions determinísticas;
- fork, join e terminais;
- waits com deadline;
- retries compatíveis com idempotência;
- compensation explícita;
- bindings publicados;
- ausência de regra bancária e endpoint físico;
- reprodutibilidade do Execution Plan.

## 13. Testes do Execution Plan

Para o mesmo request e release:

- versões resolvidas são iguais;
- nodes e dependencies são iguais;
- policies efetivas são iguais;
- digest é estável;
- nenhum step é criado dinamicamente;
- alteração posterior do Control Plane não modifica plano;
- runtime incompatível rejeita plano;
- corrupção de integridade falha seguro.

## 14. Testes de máquinas de estado

Cada estado e transição deve ser coberto:

- caminho feliz;
- rejeição antes do primeiro efeito;
- falha durante step;
- timeout;
- wait e retomada;
- cancellation;
- partial success;
- compensation completa e falha;
- transição concorrente;
- terminal imutável;
- restart entre transições;
- signal tardio.

Testes de modelo podem explorar sequências de transições além de casos escritos manualmente.

## 15. Testes da Porta Universal

A conformance suite deve tratar a implementação do Adapter como caixa-preta e validar:

- UniversalAdapterRequest;
- UniversalAdapterResult;
- capabilities declaradas;
- versões suportadas;
- immediate, async e unknown;
- deadline e timeout;
- idempotência;
- error normalization;
- trace e identity;
- security profile;
- evidence references;
- ausência de detalhe físico na Engine.

## 16. Certificação de Adapter

### 16.1 Entrada

- Adapter versionado;
- Capability Declaration;
- bindings candidatos;
- contratos e mappings;
- perfil de segurança;
- simulador certificado;
- evidências de build e supply chain.

### 16.2 Suíte

1. compatibilidade da Porta Universal;
2. operações declaradas;
3. mappings de entrada e saída;
4. normalização de erros;
5. idempotência e certainty;
6. async e callback;
7. timeout e unknown;
8. segurança e secrets;
9. observabilidade;
10. limites e resiliência;
11. perfil tecnológico;
12. fault injection.

### 16.3 Saída

```text
AdapterCertification
├── certificationId
├── adapterRef
├── bindingClassRef
├── conformanceSuiteVersion
├── testedArtifactDigests[]
├── environmentRef
├── evidenceRefs[]
├── limitations[]
├── validFrom
├── validUntil?
└── status
```

Alteração de comportamento, guarantee, mapping ou dependency crítica pode invalidar a certificação.

## 17. Simuladores contratuais

Um simulador deve:

- implementar contrato físico versionado;
- produzir respostas determinísticas por cenário;
- permitir latência e falhas configuráveis;
- controlar relógio ou tempo quando necessário;
- registrar interação sem dado sensível;
- suportar idempotência e conflito;
- simular async, callback, evento ou batch aplicável;
- produzir resposta inválida sob comando de teste;
- expor estado somente ao harness autorizado;
- permanecer isolado de sistemas reais.

## 18. Simulador não é arquitetura

São proibidos:

- alterar contrato canônico para acomodar conveniência do Mock;
- assumir REST porque o simulador atual usa HTTP;
- copiar comportamento acidental do simulador como regra;
- usar memória do Mock como garantia de idempotência final;
- inferir SLO real de latência local;
- reutilizar credencial ou dado de legado.

## 19. Catálogo de cenários de simulador

| Grupo | Cenários mínimos |
|---|---|
| Sucesso | imediato, assíncrono, callback e batch |
| Negócio delegado | positivo, negativo e resultado parcial do domínio |
| Contrato | versão incompatível, campo ausente e resposta inválida |
| Disponibilidade | conexão recusada, indisponibilidade e circuito aberto |
| Tempo | latência, timeout antes/depois do envio e callback tardio |
| Idempotência | repetição, conflito e resultado já conhecido |
| Concorrência | respostas fora de ordem e duplicidade |
| Segurança | credencial inválida, replay e assinatura incorreta |
| Recuperação | restart, redelivery, timer duplicado e reconciliação |
| Compensação | sucesso, não aplicável, irreversível e falha |

## 20. Testes de componente

Cada módulo deve ser testado com suas dependências externas substituídas por portas controladas, preservando banco ou mensageria somente quando forem parte essencial do comportamento.

Exemplos:

- Route Resolver com catálogo publicado;
- Planner com Route Definitions;
- Scheduler com store e clock controlados;
- Adapter com simulador de perfil;
- Control Plane com gates e assinatura simulada;
- retention processor com relógio virtual.

## 21. Testes de integração

Validam integração real entre componentes do Spider e tecnologias escolhidas para o ambiente de teste, incluindo:

- persistência e transactions;
- inbox/outbox;
- locks, leases e fencing;
- serialization;
- cache;
- messaging;
- secret resolution de teste;
- observabilidade;
- migrations;
- shutdown e recovery.

Destinos continuam simulados.

## 22. Testes ponta a ponta simulados

Devem iniciar na fronteira de originador simulado e terminar em resultado/callback observável, cobrindo:

- Contexto → Intenção → Capacidade → Produto/Serviço → Jornada;
- request canônico;
- resolução e plano;
- steps e Adapters;
- Mock Endpoint;
- outcome e erro;
- auditoria, trace e evidências;
- idempotência;
- espera, retomada e callback.

Quantidade deve ser controlada; variações combinatórias pertencem a níveis inferiores.

## 23. Oráculos de teste

O resultado esperado deve ser derivado de:

- schema e contrato publicados;
- state machine;
- Route Definition;
- policy versionada;
- fixture e golden dataset;
- Capability Declaration;
- error mapping;
- decisão de autorização conhecida.

Não se deve usar o comportamento atual do código como único oráculo, pois isso preserva defeitos.

## 24. Golden datasets

Golden datasets devem possuir:

- versão;
- schema;
- finalidade;
- origem sintética;
- classificação;
- inputs;
- outputs e evidências esperadas;
- limites conhecidos;
- owner;
- digest.

Mudança de golden output exige revisão semântica, não atualização automática de snapshot.

## 25. Testes de idempotência

Devem cobrir:

- mesma chave e mesmo fingerprint em sequência;
- concorrência da mesma operação;
- mesma chave com payload divergente;
- retry após timeout antes do envio;
- timeout após possível envio;
- resposta reutilizada;
- janela e tombstone;
- mudança de contract major;
- restart do Spider;
- garantia diferente por Adapter;
- ausência de exactly-once demonstrável.

## 26. Testes assíncronos

Devem controlar:

- aceitação sem conclusão;
- signal correto;
- callback duplicado;
- signal fora de ordem;
- signal tardio;
- callback falsificado;
- polling e backoff;
- timer e expiry;
- restart durante wait;
- correlação incorreta;
- dead letter;
- reconciliação.

Espera não deve depender de sleeps longos em suíte rápida; usar relógio controlado quando possível.

## 27. Testes de concorrência

- dois workers adquirindo o mesmo step;
- lease expirado e fencing;
- callback concorrente com timeout;
- cancellation concorrente com conclusão;
- retry concorrente;
- rebalanceamento de partição;
- outbox com múltiplos dispatchers;
- idempotency reservation concorrente;
- activation de snapshot durante nova execução;
- signals simultâneos.

O teste deve provar um único estado válido, não apenas ausência de exception.

## 28. Testes de compensação

Devem distinguir:

- step sem efeito;
- efeito confirmado;
- efeito desconhecido;
- compensation aplicável;
- compensation idempotente;
- ordem inversa;
- ramos paralelos;
- compensation parcialmente concluída;
- compensation failed;
- ação manual de reconciliação.

`COMPENSATED` não deve ser validado como sucesso original.

## 29. Testes de falha parcial

Devem verificar:

- resultados válidos preservados;
- erros e effects remanescentes;
- terminal `PARTIALLY_SUCCEEDED`;
- canonical outcome `PARTIAL`;
- callbacks e evidências;
- ramos cancelados ou concluídos conforme policy;
- ausência de mascaramento como sucesso.

## 30. Testes de segurança

Abrangem:

- authentication e authorization;
- delegation;
- trust zones;
- replay;
- secrets e rotação;
- transport e message security;
- injection por perfil;
- SSRF, path traversal e XML threats;
- masking e data minimization;
- access a evidence;
- supply chain;
- break-glass;
- isolamento de ambientes;
- ausência de legado real.

Resultados críticos impedem promoção independentemente de cobertura ou SLO.

## 31. Testes de privacidade

- somente campos necessários no request de Adapter;
- ausência de payload em logs;
- masking por papel e canal;
- subjectRefs autorizados;
- retention e discard;
- legal hold;
- export mínimo;
- backup e derivados;
- dados sintéticos identificáveis como não reais;
- ausência de reidentificação indevida.

## 32. Testes de performance

### 32.1 Tipos

| Tipo | Objetivo |
|---|---|
| Baseline | Medir comportamento conhecido sob carga controlada |
| Load | Validar carga esperada |
| Stress | Identificar limite e modo de degradação |
| Spike | Validar bursts e backpressure |
| Soak | Detectar degradação ao longo do tempo |
| Scalability | Validar ganho e limite de escala |
| Recovery | Medir drenagem de backlog após falha |

### 32.2 Regras

- workload model versionado;
- dados sintéticos;
- warm-up e steady state definidos;
- percentis, erro e saturação medidos;
- runtimeRelease e release registrados;
- destino simulado com capacidade controlada;
- resultado reproduzível;
- ausência de meta numérica arbitrária.

## 33. Testes de resiliência

Devem validar:

- timeout efetivo;
- retry e budget;
- circuit breaker;
- bulkhead;
- rate limit;
- backpressure;
- load shedding;
- fallback técnico permitido;
- unknown e reconciliation;
- recuperação após dependência retornar.

Retry storm deve ser cenário explícito.

## 34. Fault injection e caos controlado

Falhas injetáveis:

- processo encerrado;
- lease perdido;
- latência de store;
- falha de escrita;
- network partition;
- perda de zona simulada;
- resposta corrupta;
- certificado expirado;
- snapshot inválido;
- broker indisponível;
- clock skew controlado;
- storage cheio;
- callback ausente;
- dependency flapping.

Cada experimento possui hipótese, blast radius, owner, abort conditions e evidências.

## 35. Testes de recuperação

- restart entre persistência e envio;
- restore de estado;
- prevenção de reenvio de outbox;
- timers após restore;
- manutenção de tombstone;
- reconstrução de snapshot;
- replay governado;
- reconciliação de unknown;
- rollback de runtime;
- failover e failback;
- RPO/RTO provisórios.

## 36. Testes de compatibilidade

Matriz mínima:

| Produtor | Consumidor | Compatibilidade |
|---|---|---|
| Runtime novo | Snapshot atual | Obrigatória antes de deploy |
| Runtime atual | Snapshot novo | Conforme capabilities declaradas |
| Contrato minor novo | Consumidor anterior | Validada por regras de evolução |
| Adapter novo | Porta atual | Conformance suite |
| Mapping novo | Contracts atuais | Input/output e error mapping |
| Schema físico novo | Runtime anterior | Durante janela de coexistência |

Compatibilidade não é inferida apenas por SemVer.

## 37. Testes de migrations

- upgrade vazio e com volume;
- coexistência de runtimes;
- backfill idempotente;
- restart durante migration;
- rollback antes e depois de escrita nova;
- preservação de histórico;
- locks e impacto operacional;
- retenção e índices;
- restore de backup anterior;
- schema version correto.

## 38. Testes do Control Plane

Devem cobrir:

- lifecycle de artefato;
- segregation of duties;
- gates;
- dependency closure;
- bundle e manifest;
- digest e assinatura;
- promoção;
- ativação atômica;
- distribuição interrompida;
- snapshot parcial;
- rollback;
- revogação;
- depreciação;
- barreira Mock-first.

## 39. Testes do Data Plane

- request validation;
- route resolution;
- planning;
- scheduling;
- state and attempts;
- Adapter invocation;
- persistence and recovery;
- security enforcement;
- result and callback;
- observability;
- operation com Control Plane indisponível;
- snapshot integrity.

## 40. Testes de observabilidade

- event codes estáveis;
- correlation completa;
- metrics corretas e cardinalidade limitada;
- traces síncronos e assíncronos;
- sampling;
- ausência de dado sensível;
- health e readiness;
- SLI e SLO calculation;
- alert e runbook linkage;
- release markers;
- incident timeline.

## 41. Dados de teste

### 41.1 Regras

- sintéticos por padrão;
- schema-valid;
- casos de limite e diversidade suficientes;
- nenhuma credencial real;
- nenhuma referência reutilizável a pessoa real;
- geração reproduzível por seed registrada;
- classificação e retenção;
- descarte após finalidade;
- acesso limitado.

### 41.2 Anonimização

Dados anonimizados somente são admitidos por processo aprovado que demonstre risco residual aceitável. Pseudonimização não transforma automaticamente dado em sintético.

## 42. Ambientes de teste

| Ambiente lógico | Finalidade |
|---|---|
| Local isolado | Unidade, componente e desenvolvimento |
| Integration | Tecnologias internas e simuladores compartilhados |
| Conformance | Suítes normativas de contratos e Adapters |
| Performance | Carga sintética e capacidade |
| Security | Testes ofensivos e políticas controladas |
| Resilience | Fault injection e recuperação |
| Pre-release | Certificação integrada da release |

Todos permanecem sem conectividade com legados reais antes da fase final.

## 43. Isolamento de testes

- namespace ou partição por execução de teste;
- identities e secrets exclusivos;
- cleanup idempotente;
- clock e seed conhecidos;
- sem dependência de ordem entre testes;
- sem compartilhamento de estado oculto;
- quotas para evitar noisy neighbor;
- rastreabilidade do artefato testado.

## 44. Test Harness

```text
SpiderTestHarness
├── scenarioRunner
├── contractValidators
├── mockControllers
├── virtualClock?
├── faultInjector
├── syntheticDataFactory
├── traceAndEvidenceCollector
├── assertions
├── environmentController
└── certificationReporter
```

O harness deve usar portas públicas ou de teste governadas, não acesso direto a internals para forçar resultado.

## 45. Evidências de teste

```text
TestEvidence
├── testRunId
├── suiteRef
├── scenarioRef
├── artifactDigests[]
├── runtimeReleaseId
├── controlPlaneReleaseId?
├── environmentRef
├── dataSetRef
├── startedAt
├── completedAt
├── result
├── observations
├── traceRefs[]
├── defectRefs[]
└── integrityRef
```

Relatório sem hashes dos artefatos não certifica versão específica.

## 46. Reprodutibilidade

Uma falha deve ser reproduzível por:

- suite e scenario versionados;
- runtime e release;
- seed;
- clock;
- dataset;
- simulator behavior profile;
- fault schedule;
- configuração;
- environment manifest.

Testes não determinísticos devem ser identificados, isolados e corrigidos; retry automático não pode esconder flakiness.

## 47. Flaky tests

Um teste flaky:

- não deve bloquear indefinidamente sem diagnóstico;
- não deve ser ignorado silenciosamente;
- recebe owner, prioridade e prazo;
- pode ser quarentenado com visibilidade;
- não compõe evidência de certificação enquanto instável;
- deve ter causa analisada: tempo, concorrência, ambiente ou oracle.

## 48. Defeitos

Defeitos devem registrar:

- severidade e impacto;
- artefatos e versões;
- cenário e evidência;
- reproducibility;
- owner;
- workaround;
- target de correção;
- regression test;
- decisão de aceite de risco, se aplicável.

Defeito de integridade, segurança crítica ou duplicidade indevida impede promoção.

## 49. Quality gates

### 49.1 Gate de commit ou mudança

- static checks;
- unit e property tests aplicáveis;
- architecture rules;
- secret scan;
- schema validation;
- cobertura de mudança crítica.

### 49.2 Gate de bundle

- contract conformance;
- route validation;
- dependency closure;
- compatibility;
- security analysis;
- evidence integrity.

### 49.3 Gate de release

- integration e E2E simulados;
- performance baseline;
- resilience;
- migrations;
- observability;
- deploy e rollback;
- Adapter certifications válidas;
- readiness review.

### 49.4 Gate de ativação

- ambiente íntegro;
- runtime compatível;
- snapshot completo;
- capacidade;
- alerts e runbooks;
- rollback target;
- barreira Mock-first nesta fase.

## 50. Critérios de severidade

| Classe | Consequência geral |
|---|---|
| Blocker | Promoção proibida |
| Critical | Correção obrigatória antes de ativação |
| Major | Exige correção ou aceite formal com prazo e controle |
| Minor | Pode seguir com backlog governado |
| Informational | Melhoria ou observação sem defeito demonstrado |

Critérios definitivos devem ser alinhados à organização.

## 51. Cobertura

Cobertura deve ser multidimensional:

- requirements;
- contracts;
- states and transitions;
- error categories;
- capabilities and operations;
- profiles;
- security threats;
- recovery scenarios;
- code paths críticos.

Percentual de linha não deve ser gate único.

## 52. Matriz de rastreabilidade

```text
ArchitectureRequirement
        ↓
TestScenario
        ↓
TestRun + Artifact Digests
        ↓
Evidence
        ↓
Quality Gate / Certification Decision
```

Todo requisito normativo crítico deve possuir ao menos uma evidência de teste ou justificativa de verificação alternativa.

## 53. Certificação de release

```text
ReleaseCertification
├── certificationId
├── runtimeReleaseRefs[]
├── controlPlaneReleaseRef
├── applicableSuites[]
├── testRunRefs[]
├── adapterCertificationRefs[]
├── knownLimitations[]
├── acceptedRiskRefs[]
├── issuedAt
├── approverRefs[]
└── status
```

Nova build ou alteração de artefato invalida certificação se o digest mudar, salvo regra explícita para evidência reaproveitável.

## 54. Certificação final de legado

Somente na fase final, cada binding real deve passar por:

- discovery e inventário aprovados;
- contract mapping;
- security and network validation;
- conformance suite da Porta Universal;
- testes funcionais e negativos;
- idempotência e certainty;
- performance e limites;
- resilience e recovery;
- observability;
- operational readiness;
- parallel ou shadow testing quando permitido;
- plano de rollback;
- owner e suporte.

Certificação de um legado não certifica outro, mesmo que usem o mesmo protocolo.

## 55. Critérios de entrada para fase final

Antes de qualquer legado real:

1. arquitetura 001–012 aprovada na sequência aplicável;
2. contratos e Porta Universal implementados e estáveis;
3. simuladores certificados;
4. harness e suites automatizadas;
5. Control Plane e Data Plane governados;
6. security baseline aprovado;
7. observability e runbooks;
8. idempotência, recovery e reconciliation testados;
9. performance baseline;
10. aprovação formal do inventário do legado.

## 56. Critérios de saída da certificação final

- todos os gates críticos aprovados;
- limitações documentadas;
- owners e suporte definidos;
- SLO e capacity compatíveis;
- segurança e dados aprovados;
- evidências íntegras;
- rollback testado;
- operação assistida prevista;
- nenhuma mudança necessária na Engine ou Contrato Canônico;
- binding real ativável apenas por release governada.

## 57. Governança das suítes

Suites, scenarios, datasets e simuladores são artefatos versionados. Devem possuir owner, compatibilidade, revisão e retenção.

Mudança em teste que reduz cobertura ou relaxa assertion exige revisão. Atualizar teste para aceitar defeito não é correção.

## 58. Independência de fornecedor

Conceitos de teste e certificação não dependem de uma ferramenta. O harness pode integrar diferentes frameworks, desde que produza evidência uniforme, rastreável e reproduzível.

## 59. Decisões arquiteturais consolidadas

1. Testabilidade é requisito arquitetural.
2. Portfólio combina níveis e tipos complementares.
3. Testes estáticos e de arquitetura protegem fronteiras.
4. Propriedades validam invariantes além de exemplos.
5. Contrato Canônico e Porta Universal possuem conformance suites.
6. Adapter é certificado como caixa-preta por operação e perfil.
7. Simuladores reproduzem contrato e falhas, não arquitetura de legado.
8. Oráculos derivam de definições publicadas.
9. Idempotência, async, concorrência e compensation têm suites próprias.
10. Segurança, privacidade, performance e resiliência são gates.
11. Dados de teste são sintéticos e versionados.
12. Evidências ligam resultado aos digests dos artefatos.
13. Flaky test não compõe certificação.
14. Coverage é multidimensional.
15. Quality gates variam por estágio.
16. Release certification é imutável para os hashes avaliados.
17. Legado real é certificado individualmente somente na fase final.
18. Trocar Mock por legado não altera Engine, contratos ou suites aplicáveis.

## 60. Invariantes arquiteturais

1. Nenhum artefato crítico é promovido sem teste aplicável.
2. Nenhum teste usa comportamento atual como único oracle.
3. Nenhum Mock define arquitetura do Spider.
4. Nenhum simulador alcança sistema real.
5. Nenhum dado de teste identifica pessoa real nesta fase.
6. Nenhum secret real entra em ambiente de teste.
7. Nenhuma certificação existe sem digests.
8. Nenhum retry de teste oculta flakiness.
9. Nenhum terminal inválido é aceito pela state suite.
10. Nenhum Adapter é certificado sem error e idempotency tests.
11. Nenhum timeout inconclusivo é tratado como retry seguro por conveniência.
12. Nenhum outcome negativo é contado automaticamente como falha técnica.
13. Nenhum teste de performance usa somente média.
14. Nenhum experimento de falha ocorre sem abort conditions.
15. Nenhuma migration é promovida sem recovery test.
16. Nenhum alerta crítico é certificado sem runbook.
17. Nenhuma vulnerabilidade crítica é compensada por cobertura alta.
18. Nenhum legado real é conectado antes dos critérios de entrada.
19. Nenhuma certificação de legado é reutilizada por similaridade.
20. Integração real não altera núcleo nem Contrato Canônico.

## 61. Pontos ainda abertos

| Tema | Questão a decidir |
|---|---|
| Frameworks | Ferramentas por linguagem e nível |
| Pipeline | Orquestração, paralelismo e cache |
| Harness | Implementação e interfaces |
| Simuladores | Runtime, scenario control e state |
| Virtual clock | Biblioteca e abrangência |
| Property tests | Geradores e shrinking |
| Mutation | Escopo e thresholds |
| Contract testing | Registry, broker e publicação |
| Performance | Plataforma, workload e ambientes |
| Security testing | SAST, DAST, SCA, fuzz e pentest |
| Fault injection | Ferramenta, blast radius e governance |
| Test data | Factory, catálogo e anonimização |
| Evidence | Formato, assinatura e retenção |
| Quality gates | Thresholds e approvers |
| Flaky tests | Quarentena, SLA e reporting |
| Certification | Validade, renovação e revogação |
| Fase final | Ambientes e coordenação com owners dos legados |

## 62. Critérios de aceite

O SPIDER-ARCH-012 é considerado apto a orientar a próxima etapa quando:

1. portfólio e princípios de teste estiverem aceitos;
2. testes estáticos, de arquitetura, unidade e propriedades estiverem definidos;
3. conformance suites do contrato, rota, plano e Porta Universal estiverem formalizadas;
4. certificação de Adapter possuir entrada, suíte e saída;
5. simuladores e catálogo de cenários estiverem especificados;
6. integração, E2E, async, concorrência e compensation estiverem cobertos;
7. segurança, privacidade, performance, resiliência e recovery estiverem integrados;
8. dados, ambientes, harness e evidências estiverem governados;
9. quality gates e rastreabilidade estiverem definidos;
10. certificação de release e legado estiverem separadas;
11. critérios de entrada e saída da fase final estiverem explícitos;
12. nenhuma decisão exigir framework ou fornecedor prematuro.

## 63. Próxima etapa recomendada

Antes de implementar, recomenda-se criar:

> **SPIDER-ARCH-013 — Roadmap de Implementação Incremental, Migração e Critérios de Fase**

Esse documento deverá transformar as decisões arquiteturais em uma sequência de entrega segura, definir incrementos, dependências, gates, artefatos, estratégia de convivência com a baseline atual, migração sem big bang, critérios para prompts de implementação e condições formais para iniciar a fase final de integração com legados reais.

O roadmap deverá preservar a separação entre documentos `SPIDER-ARCH-NNN` e prompts `SPIDER-PROMPT-NNN`. Até a fase final, toda implementação e certificação continuará usando somente Mocks, stubs, simuladores e dados sintéticos.

---

## Apêndice — Alinhamento com SPIDER-ARCH-013 entregue (errata de identificador)

O identificador **SPIDER-ARCH-013** foi publicado como **Console Operacional e Visualização** (`SPIDER-ARCH-013-console-operacional-e-visualizacao.md`), incluindo o **manifesto versionado de capabilities (PROMPT-001…026)** como artefato de roadmap rastreável e certificável por testes. Isso **não reescreve** a intenção desta seção 63: a especificação normativa completa de migração física / convivência / gates de fase final permanece **adiada** e poderá ser um ARCH posterior ou extensão. Qualidade e suítes deste ARCH-012 continuam aplicáveis ao console (DenyAll, flags, redaction, E2E Mock-only).
