# SPIDER-PROMPT-020 — Capacidade, Backpressure e Resiliência Governada

> **Entrega VERIFIED (0.20.0):** registro fiel do entregue em  
> [`SPIDER-PROMPT-020-capacity-backpressure-resilience.md`](./SPIDER-PROMPT-020-capacity-backpressure-resilience.md).  
> Este arquivo permanece como **autorização / especificação de escopo** da emissão.

## 1. Estado oficial e autorização de escopo

- Produto de partida: **Spider 0.19.0**; produto pós-entrega: **0.20.0** (CAP-020 VERIFIED).
- Commit de referência: `d94aa3c9c6aa0d3b82ee513c96d6eec0639c431e` (`feat(spider): add durable worker runtime with lease fencing`).
- Estado Git observado na emissão: branch `main`, **ahead 9** de `origin/main`, sem push; alterações alheias ao Spider no monorepo devem ser preservadas.
- Baseline de partida: **297 testes backend + 41 testes frontend**; pós-entrega ver manifesto (`backendTests` 374; `frontendTests` 55 placeholder até suíte FE 020).
- Predecessor obrigatório: **CAP-019 / SPIDER-PROMPT-019 VERIFIED**.
- Grupo: `GROUP_B_RUNTIME_OPERATIONS` — CAP-020 é o segundo incremento (**2/3** após VERIFIED).
- Título oficial: **Capacidade, Backpressure e Resiliência Governada**.
- Objetivo oficial: **Limits, bulkheads, circuits, quotas e load shedding**.
- Estado após implementação: `VERIFIED` / `OFF_BY_DEFAULT` / `SIMULATED_INFRASTRUCTURE`.
- Boundary da capability: **`SIMULATED_INFRASTRUCTURE`**.
- Boundary das integrações: **`MOCK_ONLY`**.

Este prompt autoriza implementar **somente CAP-020**. Não implementar comandos/requeue/workbench do CAP-021, topologia/HA/DR do CAP-022, SDK/certificação de adapters do CAP-023, readiness do CAP-024, fundações corporativas do CAP-025 ou piloto real do CAP-026.

## 2. Missão

Introduzir uma camada governada, determinística e observável de **admissão, isolamento e reação à saturação** para proteger a Engine, os processors canônicos, o Runtime de Workers e os adapters mock já existentes.

O incremento deve responder, de forma tipada e auditável:

1. qual política efetiva foi aplicada;
2. qual recurso/escopo estava protegido;
3. por que uma unidade foi admitida, atrasada ou rejeitada;
4. qual pressão existia no instante da decisão;
5. se um bulkhead ou circuit estava limitando o fluxo;
6. qual evidência permite reproduzir e explicar a decisão.

Capacidade não é regra bancária, roteamento de negócio, autoscaling real ou operação manual. A Engine e os processors permanecem donos da semântica do efeito; o CAP-019 permanece dono de schedule, claim, lease, fencing, heartbeat e drain.

## 3. Princípios e decisões arquiteturais obrigatórias

1. **Admissão antes do efeito**: toda recusa/atraso deve ocorrer antes de iniciar novo efeito canônico. Trabalho já adquirido não pode ser abandonado silenciosamente.
2. **Sem segundo scheduler**: CAP-020 consulta backlog/schedules e condiciona novos claims/admissões; não duplica `DurableSchedule`, lease ou fencing.
3. **Política tipada e versionada**: nada de scripts, SpEL ou expressões livres. Toda decisão registra `policyRef` e versão efetiva.
4. **Separação de escopos**: suportar, no mínimo, `GLOBAL`, `WORKER_TYPE`, `SCHEDULE`, `ADAPTER_BINDING` e `SERVICE_CLASS` quando a referência existir. Ausência de referência não autoriza inventar domínio.
5. **Estado explícito**: circuit e pressão nunca podem ser inferidos apenas de logs. Devem possuir snapshot/read-model consultável.
6. **Falha segura e explicável**: configuração inválida impede ativação da policy; indisponibilidade do módulo de capacidade não transforma falha em admissão ilimitada silenciosa.
7. **Telemetria observa; não comanda**: métricas e Operational Events descrevem decisões, mas não substituem o estado persistido nem disparam mudanças implícitas.
8. **Determinismo testável**: relógio, medição e geração de IDs devem ser injetáveis nos testes.
9. **Sem promessa produtiva**: nenhuma alegação de capacidade real, throughput corporativo, HA, autoscaling, Kafka/Kubernetes, IdP/KMS ou legado real.
10. **OFF_BY_DEFAULT**: desligado, o comportamento e as superfícies do baseline 0.19.0 permanecem inalterados.

## 4. Modelo mínimo de domínio

Implementar contratos equivalentes, preservando a linguagem do código existente:

- `CapacityPolicy`: código, versão, escopo, referência do alvo, estado, limites, janelas e timestamps.
- `CapacityLimit`: concorrência máxima, backlog máximo/soft limit, taxa/quota por janela e timeout de aquisição quando aplicável.
- `AdmissionRequest`: operation ref, scope refs, worker/schedule/adapter refs, instante e correlation refs, sem payload sensível.
- `AdmissionDecision`: `ADMITTED | DELAYED | REJECTED_QUOTA | REJECTED_CAPACITY | REJECTED_CIRCUIT_OPEN | SHED`.
- `PressureSnapshot`: utilização, concorrência, backlog, taxa, quota restante, circuit/bulkhead state e freshness.
- `BulkheadState`: ocupação e capacidade por escopo; aquisição/liberação idempotentes.
- `CircuitState`: `CLOSED | OPEN | HALF_OPEN`, contadores/janela, `openedAt`, `probeAfter` e transições causais.
- `LoadSheddingDecision`: motivo tipado, prioridade/classe técnica quando governada, policy ref e evidência.

As decisões devem possuir identificador, timestamp, policy/version, escopo, resultado, reason code e correlações disponíveis. Metadados seguem allowlist/redaction; nunca persistir token, secret, HMAC completo ou payload de negócio.

## 5. Policies e limites

Fornecer catálogo/configuração versionada com defaults conservadores para demo, validado no startup/ativação. Cobrir:

- limite de concorrência por escopo (bulkhead);
- limite de backlog hard e soft;
- quota/rate limit por janela determinística;
- limiar de abertura, janela, tempo aberto e probes do circuit;
- regra explícita de load shedding quando limite hard for atingido;
- precedence determinística entre policies (a mais específica válida prevalece; empate é erro de configuração);
- modo `MONITOR_ONLY` para visualizar decisão sem bloquear, claramente rotulado;
- modo `ENFORCED` somente quando a flag específica estiver ativa.

Policies não podem ser editadas arbitrariamente pela UI neste incremento. Mudança administrativa, aprovação/publicação completa e workbench pertencem a capabilities posteriores. Para CAP-020, configuração controlada e versionada no backend é suficiente.

## 6. Integração com o Runtime de Workers (CAP-019)

Integrar a admissão no ponto anterior a **novos claims** e/ou à invocação protegida, sem alterar o protocolo de lease/fencing:

- worker em `DRAINING` continua recusando novos claims por regra do 019;
- schedule inelegível continua fora do CAP-020;
- admissão rejeitada/adiada não pode consumir fencing token como se houvesse execução;
- decisão após claim, se tecnicamente inevitável, deve liberar/concluir o claim por outcome explícito e testado, nunca deixá-lo stale por omissão;
- backlog do 019 é fonte observacional; o 020 acrescenta thresholds/políticas, sem semear trabalho artificial;
- batch size e concorrência efetivos respeitam o menor limite aplicável;
- load shedding não apaga trabalho durável; para schedules duráveis, significa não admitir agora e registrar a decisão. Rejeição definitiva só é válida em fronteira síncrona explicitamente modelada.

## 7. Bulkheads, circuits, quotas e load shedding

### 7.1 Bulkheads

- isolamento por escopo, sem pool global oculto;
- aquisição atômica e liberação garantida em sucesso/falha/timeout;
- ausência de vazamento após exceção;
- saturação produz decisão tipada e evento operacional.

### 7.2 Circuits

- transições determinísticas `CLOSED → OPEN → HALF_OPEN → CLOSED/OPEN`;
- somente resultados técnicos elegíveis contam para o circuito;
- resultado de negócio negativo não abre circuit automaticamente;
- probes concorrentes são limitados;
- retry existente não pode multiplicar chamadas além da policy efetiva;
- estado do circuit é governança técnica, não alteração da máquina de estados da Engine.

### 7.3 Quotas / rate limits

- janela e algoritmo definidos no contrato (sem dependência de tempo de parede nos testes);
- chave de quota baseada apenas em escopos técnicos permitidos;
- consumo e remanescente observáveis;
- concorrência não é confundida com taxa.

### 7.4 Load shedding

- razão explícita (`BACKLOG_HARD_LIMIT`, `CONCURRENCY_EXHAUSTED`, `QUOTA_EXHAUSTED`, `CIRCUIT_OPEN` ou equivalente tipado);
- nenhuma prioridade baseada em dado bancário ou inferência probabilística;
- nada é descartado silenciosamente;
- resposta/API usa erro canônico compatível e não vaza existência/autorização.

## 8. Persistência e modos

- Oferecer store em memória para testes/demo e persistência técnica coerente com o padrão JPA/H2/PostgreSQL do projeto para estado que precise sobreviver a restart.
- Circuit state, contadores necessários e decisões/evidências devem ter ownership explícito e retenção limitada.
- Persistência não é event sourcing; Operational Events não são fonte de verdade.
- Concorrência deve ser protegida com transição atômica/CAS/locking coerente com o projeto.
- Reinício não pode reabrir capacidade ilimitada sem sinalização; freshness/staleness deve ser visível.

## 9. Flags e configuração

Adotar prefixo coerente, por exemplo:

| Flag | Papel |
|---|---|
| `spider.capacity.enabled` | master do módulo, default `false` |
| `spider.capacity.http.enabled` | APIs do Console, exige master + console HTTP |
| `spider.capacity.local-demo.enabled` | dados/cenários controlados de demo local |
| `spider.capacity.enforcement.enabled` | aplica bloqueio real no runtime simulado; default `false` |

Knobs detalhados devem residir em policies versionadas, não proliferar como flags. Com master off, não criar coordenadores/HTTP/loops do módulo e manter os 338 testes do baseline semanticamente compatíveis.

## 10. API do Console

Sob `/v1/console/capacity` (somente com console HTTP + master + HTTP habilitados), expor leitura:

- `GET /` — snapshot consolidado;
- `GET /policies` — policies efetivas e versões;
- `GET /pressure` — pressão por escopo;
- `GET /bulkheads` — ocupação/limites;
- `GET /circuits` — estados e últimas transições;
- `GET /decisions` — decisões recentes paginadas/filtráveis.

Usar ação authz dedicada, por exemplo `VIEW_CAPACITY`. Não criar endpoint genérico de mudança/reset/requeue/force-open/force-close: isso anteciparia operações governadas do CAP-021. DenyAll, flag off, autorização ausente ou ID não enumerável devem seguir o padrão **404 sem enumeração** do Console.

## 11. Observabilidade e saúde

Emitir métricas e Operational Events de baixa cardinalidade para:

- admission decision por resultado/reason code;
- utilização e saturação de bulkhead;
- quota consumida/restante em faixas adequadas;
- circuit transitions e probes;
- load shedding;
- policy inválida/stale.

Adicionar dimensões de saúde somente quando o módulo estiver ligado, por exemplo `CAPACITY`, `BACKPRESSURE`, `BULKHEAD_SAFETY` e `CIRCUIT_HEALTH`. Com o módulo desligado, a leitura do 017/019 não muda. Amostra ausente ou snapshot stale resulta em `UNKNOWN`/inconclusivo, nunca falso verde.

## 12. Failure Lab

Estender o laboratório apenas com cenários controlados `CAPACITY_RESILIENCE`, todos `MOCK_ONLY`, sem falha externa real:

- saturação de bulkhead com admissão rejeitada e posterior recuperação;
- backlog acima de soft/hard threshold;
- circuit abre, bloqueia, entra em half-open e recupera;
- quota esgota e renova na janela;
- load shedding preserva trabalho durável e evidencia a decisão.

Predicados devem ser tipados. Cada run produz evidence bundle redigido com policy ref, decisões, fatos e verificação. Sem dados reais, o cenário é inconclusivo, nunca aprovado por omissão.

## 13. Console/UI — representação visual progressiva

Criar a superfície **Capacidade & Resiliência** integrada à navegação existente:

1. **Visão executiva**: pressão geral, modo `MONITOR_ONLY/ENFORCED`, boundary e alertas de saturação.
2. **Capacidade por escopo**: barras/medidores com usado, limite, backlog e freshness; cores não podem ser o único sinal.
3. **Bulkheads e circuits**: estado, ocupação, última transição e motivo.
4. **Quotas e shedding**: consumo da janela, renovação e decisões recentes.
5. **Drill-down**: decisão → policy/version → worker/schedule/adapter refs → Operational Events/evidência.

Banner permanente: **DEMONSTRAÇÃO · INFRAESTRUTURA SIMULADA · INTEGRAÇÕES MOCK · SEM CAPACIDADE PRODUTIVA AFERIDA**. A UI deve ser responsiva, acessível, ter estados loading/empty/error/stale e não hardcodar dados do roadmap.

## 14. Evidências visuais obrigatórias

Criar script reprodutível `frontend/scripts/capture-capacity-resilience-screenshots.mjs` e gravar em `docs/technical/screenshots`:

| Arquivo | Evidência |
|---|---|
| `020-capacity-overview-desktop.png` | visão geral e boundary |
| `020-capacity-pressure-desktop.png` | limites/backlog por escopo |
| `020-capacity-circuit-open-desktop.png` | circuit aberto com causa |
| `020-capacity-load-shedding-desktop.png` | decisão de shedding e rastreabilidade |
| `020-capacity-mobile.png` | viewport mobile |

As capturas devem usar local-demo determinístico e exibir conteúdo real da API, não fixtures hardcoded no componente.

## 15. Testes e critérios de aceite

### 15.1 Backend

- validação, versionamento, precedence e conflito de policies;
- admissão para todos os resultados/reason codes;
- concorrência real de bulkhead, sem over-admission nem leak;
- transições e probes do circuit com clock determinístico;
- quota em bordas de janela;
- hard/soft backlog e load shedding sem perda de trabalho durável;
- integração com claim/lease/fencing/drain do CAP-019;
- persistência/restart e staleness;
- telemetria, health e evidence redigidos;
- authz, flags e 404 sem enumeração;
- manifesto/roadmap/contrato anti-drift.

### 15.2 Frontend

- renderização progressive disclosure;
- estados loading/empty/error/stale/monitor/enforced;
- bulkhead/circuit/quota/shedding e drill-down;
- boundary visível em desktop/mobile;
- acessibilidade básica e ausência de dados hardcoded.

### 15.3 Regressão e prova

- `mvn test` no backend completamente verde;
- `npm test` no frontend completamente verde;
- `npm run build` no frontend verde;
- registrar contagens finais, zero failures/errors/skipped e arquivos de screenshot;
- nenhum teste existente removido, ignorado ou enfraquecido para obter verde.

## 16. Atualização documental obrigatória na implementação

A implementação só pode ser declarada `VERIFIED` se atualizar, no mesmo incremento:

1. `SPIDER-ARCH-010`: métricas, Operational Events, health, saturação e evidência.
2. `SPIDER-ARCH-011`: admission/backpressure nas unidades de execução, deixando explícito que não há autoscaling/HA real.
3. `SPIDER-ARCH-013`: nova superfície do Console, APIs, authz, boundary e screenshots.
4. `SPIDER-ARCH-014` — **Espelho Funcional do Produto**: baseline 0.20.0, linguagem de negócio, jornada visual, superfícies, flags, limitações e estado do Grupo B 2/3.
5. Este `SPIDER-PROMPT-020`: converter especificação em registro fiel do entregue, sem apagar decisões/limites.
6. Manifesto, contrato anti-drift e roadmap: CAP-020 `VERIFIED`, runtime `OFF_BY_DEFAULT`, integração `SIMULATED_INFRASTRUCTURE`; `currentPrompt=SPIDER-PROMPT-020`; produto `0.20.0`; contagens reais.
7. README/guia de apresentação quando necessário para reproduzir a demo e capturas.

Roadmap, manifesto e contrato devem permanecer idênticos em grupo, título, objetivo, status, runtime, integração e dependência.

## 17. Definition of Done

CAP-020 estará concluído somente quando:

- limits, bulkheads, circuits, quotas e load shedding estiverem implementados, tipados, governados e observáveis;
- integração com o Runtime de Workers não duplicar scheduling nem quebrar lease/fencing/drain;
- nenhum trabalho durável for perdido ou descartado silenciosamente;
- flags off preservarem o baseline;
- boundary `SIMULATED_INFRASTRUCTURE` + integrações `MOCK_ONLY` estiver evidente em API, UI, docs e evidências;
- Console/UI mostrar progressivamente pressão, políticas e decisões;
- screenshots reprodutíveis estiverem gravados;
- suítes backend/frontend e build estiverem verdes;
- SPIDER-ARCH e Espelho Funcional estiverem sincronizados;
- manifesto/roadmap/contrato não apresentarem drift;
- CAP-021–026 permanecerem apenas `PLANNED` e sem implementação antecipada.

## 18. Não objetivos e boundaries invioláveis

- não integrar IdP, KMS, mTLS, broker, Kubernetes, cloud autoscaler ou legado real;
- não medir/prometer capacidade produtiva;
- não criar HA multi-instância, DR ou restore;
- não criar UI administrativa genérica nem comandos de reconciliation/requeue;
- não alterar regra bancária, resolução de intenção, rota publicada ou máquina de estados;
- não substituir processors, stores canônicos ou o runtime 019;
- não promover `CORPORATE_SANDBOX`, `REAL_PILOT` ou `PRODUCTION`;
- não implementar qualquer parte de CAP-021–026.

## 19. Referências autoritativas

- `docs/roadmap/SPIDER-ROADMAP-IMPLEMENTACAO-016-026.md`.
- `backend/src/main/resources/implementation/spider-capability-manifest.json`.
- `backend/src/main/resources/implementation/spider-roadmap-015-026-contract.json`.
- `docs/technical/SPIDER-PROMPT-019-durable-workers-scheduling.md`.
- `docs/architecture/SPIDER-ARCH-001-baseline-e-principios-arquiteturais.md`.
- `docs/architecture/SPIDER-ARCH-003-contrato-canonico-e-modelo-de-execucao.md`.
- `docs/architecture/SPIDER-ARCH-005-definicao-de-rotas-execution-plan-e-maquina-de-estados.md`.
- `docs/architecture/SPIDER-ARCH-010-observabilidade-slos-operacao-e-resposta-a-falhas.md`.
- `docs/architecture/SPIDER-ARCH-011-topologia-implantacao-escalabilidade-e-alta-disponibilidade.md`.
- `docs/architecture/SPIDER-ARCH-013-console-operacional-e-visualizacao.md`.
- `docs/architecture/SPIDER-ARCH-014-arquitetura-funcional-do-produto.md`.
