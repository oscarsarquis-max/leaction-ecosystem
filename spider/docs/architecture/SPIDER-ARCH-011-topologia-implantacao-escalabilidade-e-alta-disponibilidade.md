# SPIDER-ARCH-011 — Topologia, Implantação, Escalabilidade e Alta Disponibilidade

| Campo | Valor |
|---|---|
| Identificador | SPIDER-ARCH-011 |
| Título | Topologia, Implantação, Escalabilidade e Alta Disponibilidade |
| Status | Proposta arquitetural inicial |
| Predecessor | SPIDER-ARCH-010 — Observabilidade, SLOs, Operação e Resposta a Falhas |
| Escopo | Especificação lógica normativa, sem implementação |

## 1. Objetivo

Formalizar os princípios e limites de implantação do Spider, definindo componentes lógicos, critérios de empacotamento, monólito modular versus serviços, escalabilidade, isolamento, particionamento, alta disponibilidade, distribuição, deploy, rollback de runtime, continuidade e recuperação.

Este documento separa arquitetura lógica de topologia física. Um componente lógico não implica processo, container, serviço ou repositório independente. A decomposição física deve ser guiada por evidências de escala, risco, segurança, disponibilidade, ownership e operação.

Este documento não escolhe nuvem, datacenter, sistema operacional, container runtime, orquestrador, service mesh, balanceador, banco, broker ou ferramenta de deploy. Não define sizing definitivo nem autoriza implementação ou integração com legados reais.

## 2. Vocabulário normativo

Os termos “deve”, “não deve” e “somente” expressam requisitos arquiteturais. “Pode” expressa possibilidade admitida.

- **Componente lógico**: conjunto coerente de responsabilidades e contratos.
- **Unidade de implantação**: artefato executável promovido e operado independentemente.
- **Monólito modular**: única unidade de implantação com módulos e dependências internas explicitamente controlados.
- **Serviço**: unidade de implantação independente com contrato, dados técnicos, ciclo e operação próprios.
- **Célula**: conjunto isolado de capacidade que atende partição explícita de carga.
- **Shard**: partição de dados ou trabalho com regra determinística de ownership.
- **Stateless worker**: worker sem estado de execução exclusivo mantido apenas em memória local.
- **Failure domain**: conjunto de recursos que pode falhar por causa comum.
- **Availability Zone**: domínio de falha independente dentro de uma região ou localidade lógica.
- **Runtime Release**: versão implantável do código e dependências executáveis.

## 3. Decisões centrais

1. Arquitetura lógica não determina distribuição física.
2. A baseline recomendada para evolução inicial é monólito modular no backend, salvo evidência contrária.
3. Microserviços não são objetivo arquitetural; são opção condicionada a critérios mensuráveis.
4. Data Plane e Control Plane possuem ciclos distintos, mas não precisam nascer como dezenas de serviços.
5. Workers de execução devem ser recuperáveis e evitar estado exclusivo em memória.
6. Escala horizontal é preferida para componentes concorrentes quando o modelo de estado permitir.
7. Particionamento possui regra determinística, ownership e reconciliação.
8. Alta disponibilidade elimina pontos únicos de falha dentro do escopo de SLO aprovado.
9. Deploy de runtime e publicação de artefatos do Control Plane são processos distintos.
10. Nesta fase, todos os ambientes permanecem isolados de legados reais e usam apenas Mocks e carga sintética.

## 4. Componentes lógicos

```text
Ingress e Contratos Contextuais
        ↓
Identity / Security Enforcement
        ↓
Context and Intent Boundary
        ↓
Route Resolver
        ↓
Execution Planner
        ↓
Execution Coordinator / Scheduler
        ↓
Universal Adapter Port
        ↓
Adapter Implementations → Mocks nesta fase

Componentes transversais
├── Persistence and Idempotency
├── Inbox / Outbox / Timers
├── Evidence / Audit
├── Observability
└── Security

Control Plane
├── Catalog and Contract Management
├── Validation and Approval
├── Bundle / Release Management
└── Distribution to Data Plane
```

Os limites acima devem existir no código e nos contratos, mesmo quando compartilharem processo e banco.

## 5. Contextos de responsabilidade

| Contexto lógico | Responsabilidade principal |
|---|---|
| Ingress | Recepção, limites, identidade, validação e correlação |
| Contextual | Contexto, intenção e referências governadas |
| Resolution | Seleção determinística de rota publicada |
| Planning | Materialização íntegra do Execution Plan |
| Execution | Estados, scheduling, retries, waits e compensação |
| Integration | Porta Universal, Adapters e perfis |
| Control | Autoria, aprovação, publicação e rollback |
| Evidence | Evidências, auditoria e retenção |
| Operations | Saúde, observabilidade, reconciliação e incidentes |

Dependências entre contextos devem apontar para portas explícitas, não para classes ou tabelas internas de outro módulo.

## 6. Baseline de implantação

### 6.1 Baseline recomendada

```text
Spider Backend — monólito modular
├── ingress
├── security
├── contextual
├── resolution
├── planning
├── execution
├── integration-port
├── adapter-runtime
├── persistence
├── evidence
└── operations

Control Plane inicial
└── módulos administrativos separados logicamente

Simuladores
└── processos independentes somente para teste contratual
```

A baseline reduz custo operacional enquanto os contratos e limites amadurecem. Não autoriza acoplamento entre módulos.

### 6.2 Condições

- módulos possuem APIs internas ou portas explícitas;
- dependências seguem direção arquitetural;
- modelos internos não atravessam limites indiscriminadamente;
- migrations e ownership de dados técnicos são identificáveis;
- observabilidade distingue módulos;
- testes podem executar módulo isoladamente;
- extração futura é possível sem reescrever semântica.

## 7. Monólito modular

O monólito modular é adequado quando:

- time e domínio ainda estão consolidando limites;
- escala é compatível com uma unidade horizontalmente replicável;
- ciclos de release são coordenados;
- requisitos de isolamento podem ser atendidos no mesmo runtime;
- transações locais simplificam consistência;
- custo operacional de distribuição seria maior que o benefício.

Ele não deve se tornar monólito sem fronteiras. Acesso direto entre tabelas ou classes internas de módulos deve ser restrito.

## 8. Critérios de decomposição

Um componente pode tornar-se serviço independente quando houver evidência persistente de um ou mais critérios:

1. perfil de escala muito diferente;
2. isolamento de falha necessário para SLO;
3. exigência de segurança ou zona distinta;
4. ciclo de release realmente independente;
5. ownership estável por equipe autônoma;
6. tecnologia específica justificada pelo problema;
7. volume ou retenção de dados técnicos incompatível;
8. latência ou proximidade de destino específica;
9. necessidade de implantação regional distinta;
10. contenção ou saturação não resolvida por modularidade.

Uma extração deve apresentar benefício mensurável, custo operacional, contrato, dados, migração, observabilidade, segurança e rollback.

## 9. Anti-critérios de decomposição

Não justificam serviço isoladamente:

- nome de entidade ou tabela;
- preferência tecnológica;
- desejo abstrato de modernização;
- quantidade de classes;
- existência de endpoint;
- simulação local atual;
- tendência de mercado;
- organização temporária do time;
- tentativa de evitar disciplina modular.

## 10. Data Plane e Control Plane físicos

A separação lógica é obrigatória. A separação física pode ocorrer em etapas.

### 10.1 Data Plane

O Data Plane prioriza baixa latência, previsibilidade, isolamento, escala, continuidade e ausência de edição administrativa no caminho crítico.

### 10.2 Control Plane

O Control Plane prioriza governança, consistência, aprovação, integridade e distribuição. Sua indisponibilidade não deve interromper execuções com snapshot válido.

### 10.3 Opções admitidas

- mesma unidade, módulos e permissões separadas na fase inicial;
- unidades independentes com storage compartilhado sob ownership explícito;
- unidades e stores separados quando risco e escala justificarem.

## 11. Unidades de execução

### 11.1 Ingress workers

Recebem requests, aplicam limites, segurança e validação inicial. Devem poder escalar horizontalmente sem afinidade obrigatória de sessão.

### 11.2 Execution workers

Adquirem trabalho por transição condicional, lease e fencing. Não dependem de memória local para recuperar execução.

### 11.3 Timer workers

Processam waits e deadlines de modo idempotente. Disparo duplicado deve ser seguro.

### 11.4 Delivery workers

Processam outbox, callbacks e mensagens respeitando idempotência, ordering e backpressure.

### 11.5 Adapter workers

Podem permanecer no runtime principal ou ser isolados por perfil, risco, dependência ou escala. A Porta Universal permanece a mesma.

### 11.6 Estado verificado (SPIDER-PROMPT-019)

No baseline 0.19.0, o **Runtime de Workers Duráveis** (`CAP-019`, `OFF_BY_DEFAULT`, `SIMULATED_INFRASTRUCTURE`) materializa schedules com lease/fencing para os sete tipos canônicos (sinal, wait expiry, callback delivery/reconciliação/recovery, signal recovery, envelope). Não é cluster/Kafka produtivo: a posse é simulada no store do Spider; integrações permanecem `MOCK_ONLY`. Drain ordenado e leitura de backlog são superfícies de operação, não HA multi-célula (022).

## 12. Estado local

É permitido em memória:

- cache derivável e versionado;
- configuração do snapshot ativo;
- buffers limitados e descartáveis;
- conexão e client pools;
- métricas temporárias;
- leases com autoridade persistida externamente.

É proibido manter apenas em memória:

- estado único de execução;
- decisão de idempotência;
- outbox não persistida;
- timer sem registro durável;
- evidência obrigatória;
- credencial permanente;
- mudança administrativa ainda não publicada.

## 13. Escalabilidade horizontal

Para escalar horizontalmente, um componente deve:

- externalizar estado durável necessário;
- usar ownership e concorrência explícitos;
- possuir readiness correta;
- suportar término gracioso;
- distribuir carga sem dependência de ordem acidental;
- limitar fan-out e retries;
- expor saturação e capacidade;
- evitar cache divergente não detectável.

Adicionar instância não deve aumentar duplicidade de efeito.

## 14. Escalabilidade vertical

Escala vertical pode ser usada quando eficiente e simples, especialmente em baseline inicial. Não deve substituir limites, backpressure ou planejamento de capacidade.

Dependência de recurso único muito grande deve ser reconhecida como risco de recovery e failure domain.

## 15. Particionamento de trabalho

```text
PartitionAssignment
├── partitionKeyDefinitionRef
├── partitionCount
├── ownershipEpoch
├── assignmentState
├── workerRefs[]
├── rebalancePolicyRef
└── evidenceRef
```

Regras:

- chave determinística e estável durante a execução;
- distribuição compatível com cardinalidade;
- ownership único por epoch quando necessário;
- fencing de owner anterior;
- rebalanceamento observável e recuperável;
- ausência de significado bancário embutido na chave;
- hot partitions detectáveis.

## 16. Particionamento de dados

Stores podem ser particionados por executionId, tempo, tenant lógico, região ou combinação. A escolha deve preservar:

- atomicidade do agregado;
- unicidade idempotente no escopo;
- consulta operacional essencial;
- retenção e descarte;
- restore e reconciliação;
- isolamento de acesso;
- movimentação sem perda de integridade.

Cross-shard transaction não é premissa. Fluxos que a exigirem devem ser redesenhados ou possuir coordenação explícita.

## 17. Células

Arquitetura celular pode isolar carga por partição, domínio ou classe quando escala e blast radius justificarem.

Uma célula deve possuir:

- regra determinística de roteamento;
- capacidade e SLO próprios;
- stores e filas compatíveis;
- isolamento de falha;
- observabilidade agregável;
- processo de expansão e drenagem;
- ausência de dependência síncrona entre células no caminho crítico.

Células não são necessárias na baseline inicial.

## 18. Balanceamento

Balanceamento deve considerar:

- readiness e health;
- afinidade somente quando justificada;
- capacidade disponível;
- distribuição consistente de partition key;
- drenagem durante deploy;
- retry no nível correto;
- prevenção de retry storm;
- preservação de client identity e trace autorizados.

Load balancer não deve selecionar rota de negócio ou Adapter.

## 19. Filas e scheduling

Filas lógicas devem declarar:

- tipo de trabalho;
- prioridade;
- ordering;
- deduplicação;
- visibility ou lease;
- retry e dead letter;
- retenção;
- capacidade e backpressure;
- owner e métricas.

Prioridade não pode causar starvation. Work stealing deve respeitar partition ownership e segurança.

## 20. Autoscaling

Autoscaling pode usar:

- taxa de entrada;
- backlog e idade;
- utilização de worker;
- latência;
- saturação de pool;
- deadlines próximos;
- service class.

CPU isolada pode ser indicador insuficiente para processos I/O-bound ou filas. Scaling deve considerar tempo de inicialização, capacidade do destino e efeito sobre stores.

Autoscaling não pode ultrapassar quotas, rate limits ou capacidade certificada de Adapter.

## 21. Failure domains

Devem ser identificados:

- processo;
- host ou nó;
- pool;
- zona;
- região ou site;
- store;
- broker;
- identity provider;
- secrets/key service;
- Control Plane;
- binding e destino.

Uma réplica no mesmo failure domain não oferece alta disponibilidade contra falha daquele domínio.

## 22. Alta disponibilidade

Para uma capacidade classificada como altamente disponível:

- múltiplas instâncias elegíveis;
- distribuição por failure domains;
- estado replicado conforme RPO;
- failover testado;
- health e readiness corretos;
- ausência de singleton oculto;
- capacidade restante após falha;
- prevenção de split-brain;
- observabilidade da convergência;
- runbook e owner.

O nível definitivo depende da service class e dos SLOs.

## 23. Multi-zona

Implantação multi-zona deve considerar:

- latência entre zonas;
- quorum e consistência;
- afinidade de dados;
- tráfego e custo;
- falha de zona completa;
- perda parcial de conectividade;
- reentrada e reconciliação;
- capacidade N-1;
- distribuição de secrets e chaves.

Distribuir instâncias sem distribuir dependências críticas não completa a solução multi-zona.

## 24. Multi-região ou multi-site

É opção futura condicionada a RTO, RPO, residência, latência e risco. Modos possíveis incluem ativo-passivo, warm standby, active-active particionado ou outras combinações.

Active-active requer:

- ownership claro de execução;
- idempotência global no escopo;
- prevenção de split-brain;
- resolução de conflito;
- roteamento estável;
- replicação compatível;
- reconciliação após partição.

Não é baseline inicial.

## 25. Consistência e CAP operacional

Durante partição, cada componente deve declarar se prioriza disponibilidade ou consistência para a operação específica.

Exemplos:

- idempotência e transição de estado priorizam consistência;
- métricas podem tolerar perda limitada;
- cache de snapshot pode continuar com última versão válida;
- nova publicação pode ser bloqueada sem quorum de integridade;
- execução com efeito não deve prosseguir sem autoridade durável requerida.

Não existe escolha única para todo o Spider.

## 26. Persistência e alta disponibilidade

Cada store deve declarar:

- owner e fonte de autoridade;
- consistência;
- replicação;
- failover;
- backup e restore;
- RPO e RTO;
- particionamento;
- retenção;
- capacidade;
- observabilidade;
- comportamento sob degradação.

Réplicas de leitura não devem retornar estado incompatível para decisão de transição ou idempotência.

## 27. Caches

Caches podem armazenar artefatos publicados, resolution data e projections deriváveis.

Regras:

- chave inclui versão aplicável;
- TTL e invalidação explícitos;
- origem íntegra conhecida;
- cache miss não altera semântica;
- stale read somente quando policy permite;
- conteúdo sensível protegido;
- divergência detectável;
- cache local descartável.

Cache nunca é fonte única de Execution Plan ou idempotência.

## 28. Rede

Topologia de rede deve aplicar:

- segmentação por ambiente e zona de confiança;
- ingress e egress controlados;
- allowlist de destinos por binding;
- DNS ou resolução governada;
- proteção contra SSRF e pivot;
- limites e observabilidade;
- caminho de administração separado;
- ausência de acesso a legados nesta fase.

A Engine não recebe rotas de rede. Adapters resolvem configuração autorizada.

## 29. Isolamento de Adapters

Um Adapter pode ser isolado em unidade própria quando:

- usa runtime ou biblioteca incompatível;
- exige zona de rede específica;
- possui credencial ou classificação mais restrita;
- apresenta risco de estabilidade;
- escala de forma distinta;
- requer ciclo de atualização independente;
- protocolo bloqueante compromete runtime principal.

O isolamento mantém Porta Universal, contratos, estados e testes de conformidade.

## 30. Isolamento por tenant, domínio ou originador

Quando necessário, isolamento pode ocorrer por quotas, pools, partições, células ou unidades. Deve impedir noisy neighbor e acesso cruzado.

Isolamento não pode ser derivado de campo não autenticado. O escopo vem do Security Context e da configuração governada.

## 31. Runtime Release

```text
RuntimeRelease
├── runtimeReleaseId
├── componentRef
├── version
├── artifactDigest
├── dependencyManifestRef
├── supportedProtocolVersions[]
├── supportedArtifactVersions[]
├── configurationSchemaRef
├── securityEvidenceRefs[]
├── testEvidenceRefs[]
└── status
```

Release de runtime é distinta da release de artefatos do Control Plane. Compatibilidade entre ambas deve ser validada.

## 32. Configuração

Configuração deve ser:

- versionada quando semântica;
- segregada por ambiente;
- validada por schema;
- resolvida por referência;
- protegida por acesso;
- auditada;
- atualizada de forma atômica quando necessário;
- separada de secrets;
- reversível.

Feature flag não deve alterar regra bancária ou criar rota não publicada.

## 33. Deploy

O fluxo mínimo é:

```text
Build reproduzível
→ testes e análise
→ artefato íntegro
→ promoção
→ pre-deploy checks
→ implantação controlada
→ readiness
→ observação
→ conclusão ou rollback
```

Deploy não deve executar migration destrutiva irreversível sem estratégia compatível.

## 34. Estratégias de deploy

São admitidas, conforme componente:

- rolling;
- blue-green;
- canary;
- replace;
- shadow para comparação sem efeito;
- deploy celular.

A estratégia deve declarar capacidade temporária, coexistência de versões, compatibilidade, drenagem, critérios de sucesso e rollback.

## 35. Coexistência de versões

Durante deploy, versões diferentes podem coexistir. Requisitos:

- contratos backward/forward compatíveis na janela;
- registros com schema version;
- snapshots suportados por ambos os runtimes;
- mensagens consumíveis ou roteadas corretamente;
- nenhuma interpretação divergente de estado;
- observabilidade por runtimeReleaseId;
- tempo máximo de coexistência.

## 36. Drenagem e término gracioso

Antes de remover instância:

- parar de aceitar novo trabalho;
- concluir ou devolver leases de forma segura;
- persistir estado;
- interromper polling e timers sem duplicidade;
- liberar conexões;
- finalizar spans e métricas possíveis;
- respeitar deadline de shutdown;
- usar fencing para trabalho retomado por outro worker.

Encerramento forçado deve ser recuperável.

## 37. Migrations

Migrations devem seguir expansão e contração quando coexistência exigir:

```text
Adicionar estrutura compatível
→ publicar runtime que usa ambas
→ migrar/backfill idempotente
→ confirmar consumidores
→ remover estrutura antiga em release posterior
```

Migration não pode reinterpretar histórico nem bloquear indiscriminadamente o Data Plane sem janela governada.

## 38. Rollback de runtime

Rollback deve considerar:

- compatibilidade com dados escritos pela nova versão;
- mensagens e outbox produzidas;
- snapshot ativo;
- migrations;
- secrets e configuração;
- processos longos iniciados;
- causa do incidente;
- observabilidade de convergência.

Rollback de código não reverte efeito externo ou execução já concluída.

## 39. Feature flags

Flags podem controlar rollout técnico, observabilidade ou ativação segura. Devem possuir owner, validade, ambiente, default seguro e plano de remoção.

São proibidas flags permanentes sem governança, flags que contornem autorização e flags que introduzam endpoints livres ou integração real nesta fase.

## 40. Compatibilidade Runtime–Artefatos

Antes da ativação, validar:

- versão do Contrato Canônico;
- versão da Route Definition;
- versão da Porta Universal;
- schemas e mappings;
- estados e enums;
- policies;
- snapshot e manifest;
- Adapter declarations;
- migrations aplicadas.

Runtime incompatível deve permanecer `NOT_READY`.

## 41. Continuidade do Control Plane

O Control Plane deve possuir backup, restore, integridade e capacidade de redistribuir releases conhecidas. Sua indisponibilidade não impede Data Plane com snapshot seguro.

Operações administrativas podem ser bloqueadas durante falha; isso é preferível a publicar estado inconsistente.

## 42. Continuidade do Data Plane

O Data Plane deve:

- usar último snapshot válido dentro da policy;
- preservar execução e idempotência;
- aplicar backpressure sob perda de dependência;
- não iniciar efeito sem persistência requerida;
- recuperar workers, timers e deliveries;
- operar em capacidade degradada explícita quando permitido;
- expor impacto por service class.

## 43. Disaster recovery

DR deve ser definido por service class e stores. O plano deve incluir:

- RPO e RTO;
- sequência de recuperação;
- dependências de identidade e chaves;
- artefatos e configuração;
- estado, idempotência e outbox;
- prevenção de split-brain;
- validação antes de aceitar tráfego;
- reconciliação após failover;
- failback;
- testes periódicos.

## 44. Capacidade N-1

Capacidades críticas devem avaliar operação após perda do maior failure domain previsto. Se N-1 não for economicamente ou tecnicamente exigido, a limitação deve ser explícita na service class.

Autoscaling durante falha não substitui capacidade mínima se o tempo de provisionamento exceder o budget.

## 45. Segurança da implantação

- identidade de workload por unidade;
- least privilege;
- artefatos assinados ou verificados;
- secrets injetados por mecanismo autorizado;
- filesystem e rede restritos;
- administração segregada;
- logs sem secrets;
- imagens e dependências mínimas;
- políticas de runtime;
- isolamento entre ambientes.

## 46. Observabilidade da topologia

Devem ser visíveis:

- runtime release por instância;
- snapshot ativo;
- zona, célula e partição;
- readiness e health;
- ownership e leases;
- fila e backlog;
- capacidade e saturação;
- distribuição de tráfego;
- versão durante canary;
- failover e rebalanceamento;
- divergência e split-brain suspeito.

## 47. Operação de múltiplas versões

Dashboards e alertas devem permitir comparar versões sem explodir cardinalidade. Incidente deve identificar runtimeReleaseId, releaseId do Control Plane e população afetada.

Processos longos mantêm runtime compatível até terminalização ou estratégia governada de retomada.

## 48. Critérios de prontidão de deploy

Uma unidade está pronta quando possui:

- owner;
- contrato e dependências;
- build reproduzível;
- testes e evidências;
- health e readiness;
- métricas, logs e traces;
- capacity model;
- limits e backpressure;
- security profile;
- deploy e rollback testados;
- migration segura;
- runbooks;
- testes com Mocks e carga sintética.

## 49. Testes de topologia

Devem ser automatizáveis:

- escala horizontal sem duplicidade;
- worker crash e lease recovery;
- shutdown gracioso e forçado;
- rebalanceamento de partição;
- hot partition;
- perda de instância, nó e zona simulada;
- store failover;
- backlog e autoscaling;
- backpressure e load shedding;
- rolling, canary e blue-green aplicáveis;
- coexistência de versões;
- migration e rollback;
- snapshot incompatível;
- split-brain e fencing;
- restore e DR;
- isolamento de rede e ambiente;
- impossibilidade de alcançar legado real.

## 50. Estratégia Mock-first

Nesta fase:

- topologias usam somente ambientes isolados;
- Adapters alcançam somente Mocks;
- carga é sintética;
- falhas de nó, zona, rede e store são simuladas;
- multi-zona ou multi-região, se testadas, não envolvem sistemas reais;
- secrets e certificados são exclusivos de teste;
- nenhuma rota de egress para legados é permitida;
- sizing é provisório e baseado em cenários artificiais.

Os testes devem validar arquitetura, não reproduzir limitações particulares dos simuladores atuais.

## 51. Decisões arquiteturais consolidadas

1. Componentes lógicos não implicam serviços físicos.
2. Monólito modular é a baseline inicial recomendada.
3. Decomposição exige evidência de escala, isolamento, segurança ou ownership.
4. Data Plane e Control Plane têm ciclos separados.
5. Workers são recuperáveis e evitam estado exclusivo em memória.
6. Escala horizontal usa concorrência, leases e fencing explícitos.
7. Particionamento é determinístico e observável.
8. Arquitetura celular é opção futura, não baseline.
9. Alta disponibilidade considera failure domains reais.
10. Multi-região não é decisão prematura.
11. Consistência e disponibilidade são decididas por operação.
12. Adapter pode ser isolado sem alterar Porta Universal.
13. Runtime Release e Control Plane Release são distintos.
14. Deploy suporta coexistência, drenagem e rollback.
15. Migration preserva compatibilidade e histórico.
16. Rollback de código não reverte efeitos externos.
17. DR preserva estado, idempotência, integridade e prevenção de split-brain.
18. Nesta fase, somente Mocks, ambientes isolados e carga sintética são permitidos.

## 52. Invariantes arquiteturais

1. Nenhum módulo acessa internals de outro sem porta definida.
2. Nenhum serviço é criado sem justificativa mensurável.
3. Nenhum worker depende de estado único apenas em memória.
4. Nenhuma réplica processa lease vencida após novo fencing token.
5. Nenhuma partição possui dois owners válidos no mesmo epoch quando exclusividade é exigida.
6. Nenhuma escala automática ultrapassa limite certificado do destino.
7. Nenhum cache é fonte única de plano ou idempotência.
8. Nenhum load balancer decide rota de negócio.
9. Nenhuma fila possui retry ou retenção indefinidos.
10. Nenhum deploy ativa runtime incompatível com snapshot.
11. Nenhuma versão publicada é alterada durante deploy.
12. Nenhum shutdown descarta execução aceita.
13. Nenhuma migration destrutiva ocorre sem transição compatível.
14. Nenhum rollback reinterpreta dado escrito.
15. Nenhuma feature flag contorna governança ou segurança.
16. Nenhum failover admite split-brain silencioso.
17. Nenhum ambiente de teste usa secret real.
18. Nenhuma rota de rede desta fase alcança legado real.
19. Nenhum teste de carga usa dado real.
20. Futuro legado permanece isolado atrás do Adapter.

## 53. Pontos ainda abertos

| Tema | Questão a decidir |
|---|---|
| Baseline física | Processos, módulos e empacotamento inicial |
| Orquestração | Containers, VMs, funções ou combinação |
| Nuvem/site | Provedor, regiões, zonas e residência |
| Stores | Produtos, replicação e particionamento |
| Mensageria | Broker, filas, ordering e HA |
| Service discovery | Resolução, health e failover |
| Load balancing | Estratégias internas e externas |
| Autoscaling | Métricas, limites e warm-up |
| Células | Critérios e chave de roteamento |
| Multi-região | Modo, ownership e replicação |
| Deploy | Ferramenta, canary, blue-green e gates |
| Migrations | Ferramenta e estratégia por store |
| Configuração | Store, refresh e versionamento |
| Runtime security | Policies, images e attestation |
| DR | RPO/RTO, failover, failback e testes |
| Custos | FinOps, capacidade mínima e eficiência |
| Fase final | Conectividade, proximidade e HA por legado real |

## 54. Critérios de aceite

O SPIDER-ARCH-011 é considerado apto a orientar a próxima etapa quando:

1. componentes lógicos e unidades físicas estiverem separados;
2. baseline de monólito modular estiver aceita ou substituída por evidência;
3. critérios e anti-critérios de decomposição estiverem claros;
4. workers, estado local e escala horizontal estiverem definidos;
5. particionamento, células e balanceamento estiverem limitados;
6. failure domains, HA, multi-zona e multi-região estiverem formalizados;
7. stores, caches, rede e Adapters tiverem responsabilidades explícitas;
8. runtime release, configuração e deploy estiverem separados do Control Plane;
9. coexistência, migrations, drenagem e rollback estiverem cobertos;
10. continuidade, N-1 e DR estiverem especificados;
11. testes de topologia puderem ser derivados;
12. Mocks, ambientes isolados e carga sintética permanecerem exclusivos nesta fase.

## 55. Próxima etapa recomendada

Antes de implementar, recomenda-se criar:

> **SPIDER-ARCH-012 — Estratégia de Testes, Certificação e Qualidade Arquitetural**

Esse documento deverá formalizar pirâmide e portfólio de testes, conformidade de contratos, testes de propriedades, integração com simuladores, cenários assíncronos, caos controlado, segurança, performance, resiliência, compatibilidade, certificação de Adapters, gates de qualidade, dados sintéticos, ambientes e critérios de entrada e saída para cada fase.

A estratégia permanecerá independente de framework e fornecedor. Até a fase final, toda integração será validada exclusivamente contra Mocks, stubs e simuladores; legados reais somente serão certificados na etapa final prevista. Prompts de implementação permanecem separados em `SPIDER-PROMPT-NNN`.
