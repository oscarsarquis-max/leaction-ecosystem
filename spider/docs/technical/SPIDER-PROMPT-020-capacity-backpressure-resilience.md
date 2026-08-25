# SPIDER-PROMPT-020 — Capacidade, Backpressure e Resiliência Governada

## Baseline

- Produto: **0.20.0** · capability boundary **SIMULATED_INFRASTRUCTURE** · integrações **MOCK_ONLY**
- Predecessor: SPIDER-PROMPT-019 VERIFIED (Grupo B 1/3 → 2/3)
- Grupo corrente: `GROUP_B_RUNTIME_OPERATIONS` (**2/3**)
- Baseline final confirmado: **374** backend · **67** frontend · `npm run build` verde
- Flags (default **false**): `spider.capacity.enabled`; superfícies `spider.capacity.http.enabled`, `spider.capacity.local-demo.enabled`, `spider.capacity.enforcement.enabled` (exigem o master ligado)
- HTTP de capacidade exige também `spider.console.http.enabled=true`
- Autorização original / escopo: `docs/technical/SPIDER-PROMPT-020-capacity-backpressure-governed-resilience.md`

## Missão

Introduzir uma camada governada, determinística e observável de **admissão, isolamento e reação à saturação** para proteger a Engine, os processors canônicos e o Runtime de Workers (019). Capacidade responde, de forma tipada:

1. qual política efetiva foi aplicada;
2. qual recurso/escopo estava protegido;
3. por que a unidade foi admitida, atrasada ou rejeitada;
4. qual pressão existia no instante da decisão;
5. se bulkhead ou circuit limitava o fluxo;
6. qual evidência permite reproduzir a decisão.

A Engine e os processors permanecem donos do efeito; o CAP-019 permanece dono de schedule, claim, lease, fencing, heartbeat e drain. Capacidade **não** é regra bancária, autoscaling real nem operação manual.

## Policies

- Catálogo versionado em classpath: `implementation/capacity-policies-v1.json` (`CapacityPolicyCatalog`).
- Precedência determinística por escopo; empate de precedence no mesmo `scopeType` falha no bootstrap.
- Escopos tipados: `GLOBAL`, `WORKER_TYPE`, `SCHEDULE`, `ADAPTER_BINDING`, `SERVICE_CLASS`.
- Limites: concorrência (bulkhead), backlog soft/hard, quota por janela, limiares de circuit.
- Modos: `MONITOR_ONLY` (observa e admite) vs `ENFORCED` (bloqueia de verdade) — este último só com `spider.capacity.enforcement.enabled=true`.
- Policies não são editáveis pela UI neste incremento (workbench = CAP-021).

## Admissão antes do claim

Integração em `WorkerScheduleRunner`: **avaliar → (opcionalmente reservar bulkhead) → só então `tryClaim`**.

- Recusa/atraso **antes** do claim evita queimar fencing token / versão do schedule sem trabalho executado.
- Worker `DRAINING` e schedule inelegível continuam regras do 019.
- Load shedding **não** apaga trabalho durável: significa não admitir agora e registrar a decisão.
- Bulkhead: aquisição imediata pré-claim; liberação em `finally` (sem vazamento).

Prova no Failure Lab: cenário `CAPACITY_LOAD_SHEDDING` — fato `capacityFencing=UNCHANGED` após recusa.

## Bulkheads, circuits, quotas e shedding

| Mecanismo | Comportamento entregue |
|-----------|------------------------|
| **Bulkhead** | Isolamento por `scopeKey`; `ACQUIRED` / `SATURATED`; liberação idempotente |
| **Circuit** | `CLOSED → OPEN → HALF_OPEN → CLOSED/OPEN`; probes limitados; só falhas técnicas elegíveis |
| **Quota** | Janela determinística (clock injetável); consumo/remanescente observáveis |
| **Load shedding** | Motivos tipados (`CONCURRENCY_EXHAUSTED`, `BACKLOG_HARD_LIMIT`, `QUOTA_EXHAUSTED`, `CIRCUIT_OPEN`, …); nada descartado em silêncio |

Desfechos de admissão (`AdmissionResult`): `ADMITTED` \| `DELAYED` \| `REJECTED_QUOTA` \| `REJECTED_CAPACITY` \| `REJECTED_CIRCUIT_OPEN` \| `SHED`.

## Flags

| Flag | Papel |
|------|--------|
| `spider.capacity.enabled` | Master do módulo (OFF_BY_DEFAULT) |
| `spider.capacity.http.enabled` | Expõe API `/v1/console/capacity/*` |
| `spider.capacity.local-demo.enabled` | Demo local (profile `local-demo`) |
| `spider.capacity.enforcement.enabled` | Aplica bloqueio real (`ENFORCED`); default false → `MONITOR_ONLY` |

Com master off: nenhum bean de coordenação/HTTP do módulo; comportamento byte a byte do baseline 0.19.0.

## API

Base: `/v1/console/capacity` (ativa só com console HTTP + capacity + capacity.http). Authz: `VIEW_CAPACITY`.

| Método | Caminho | Conteúdo |
|--------|---------|----------|
| `GET` | `/` | Snapshot consolidado (modo, policies, pressão, bulkheads, circuits, decisões) |
| `GET` | `/policies` | Policies efetivas e versões |
| `GET` | `/pressure` | Pressão por escopo |
| `GET` | `/bulkheads` | Ocupação / limites |
| `GET` | `/circuits` | Estados e transições |
| `GET` | `/decisions?limit=` | Decisões recentes (máx. 200) |

DenyAll / flags off / credencial ausente → **404** (sem enumeração). Sem endpoints de force-open/reset/requeue (CAP-021).

## Failure Lab — cenários `CAPACITY_RESILIENCE`

Categoria `CAPACITY_RESILIENCE` (boundary do cenário: **MOCK_ONLY**). Runbook: `runbook:failure-lab:capacity@1.0`.

| Código | O que demonstra |
|--------|-----------------|
| `CAPACITY_BULKHEAD_SATURATION` | Bulkhead cheio → admissão rejeitada → liberação |
| `CAPACITY_BACKLOG_HARD_LIMIT` | Backlog no limite duro → `SHED` tipado |
| `CAPACITY_CIRCUIT_OPEN_RECOVER` | Circuit abre, bloqueia, half-open e recupera |
| `CAPACITY_QUOTA_EXHAUSTION` | Quota esgota na janela |
| `CAPACITY_LOAD_SHEDDING` | Shedding **antes** do claim; fencing token inalterado |

Harness: `FailureLabCapacityHarness`. Predicados tipados sobre fatos de capacidade / `AdmissionResult` / `CircuitPhase`.

## Dimensões de saúde (017 + 020)

Com `spider.capacity.enabled=true`, o Cockpit Operacional acrescenta (sem alterar a leitura 017/019 quando o módulo está off):

| Dimensão | Leitura |
|----------|---------|
| `CAPACITY` | Policies publicadas e modo (`MONITOR_ONLY` / `ENFORCED`) |
| `BACKPRESSURE` | Pressão por escopo (CRITICAL → UNHEALTHY; HIGH → DEGRADED) |
| `BULKHEAD_SAFETY` | Algum bulkhead saturado → DEGRADED |
| `CIRCUIT_HEALTH` | OPEN → UNHEALTHY; HALF_OPEN → DEGRADED |

Amostra ausente / snapshot stale → `INSUFFICIENT_DATA` / inconclusivo — nunca falso verde.

## Console / UI

Superfície **Capacidade & Resiliência** (progressive disclosure): pressão, modo, bulkheads, circuits, quotas/shedding e drill-down de decisão → policy → refs. Banner permanente: **DEMONSTRAÇÃO · INFRAESTRUTURA SIMULADA · INTEGRAÇÕES MOCK · SEM CAPACIDADE PRODUTIVA AFERIDA**.

## Screenshots

| Arquivo | Conteúdo |
|---------|----------|
| `020-capacity-overview-desktop.png` | Visão geral e boundary |
| `020-capacity-pressure-desktop.png` | Limites / backlog por escopo |
| `020-capacity-circuit-open-desktop.png` | Circuit aberto com causa |
| `020-capacity-load-shedding-desktop.png` | Decisão de shedding e rastreabilidade |
| `020-capacity-mobile.png` | Viewport mobile |

Geração prevista: `frontend/scripts/capture-capacity-resilience-screenshots.mjs` (local-demo + flags de capacity). PNGs podem ser produzidos separadamente do fechamento documental.

## Boundary

- **SIMULATED_INFRASTRUCTURE**: policies, bulkheads, circuits e quotas são reais no processo do Spider; não há Kafka, K8s autoscaler nem capacity produtiva aferida.
- **MOCK_ONLY** nas integrações: sem IdP/KMS/legado real; Failure Lab não injeta falha em infra externa.
- OFF_BY_DEFAULT: flags off → superfície e beans ausentes.

## Limitações

- **Estado em memória**: decisões (`CapacityDecisionStore`), ocupação de bulkhead, contadores de circuit/quota reiniciam com o processo; leitura declara `dataQuality` / freshness — não há HA multi-instância nem store compartilhado (CAP-022).
- **Sem HA**: capacidade não distribui posse entre nós; não há DR/restore de estado de pressão.
- Sem edição administrativa de policies na UI; sem comandos de reconciliation/requeue (CAP-021).
- Sem autoscaling real, medição de throughput corporativo ou promessa produtiva.

## Grupo B 2/3

Com CAP-020 **VERIFIED**, o `GROUP_B_RUNTIME_OPERATIONS` avança para **2/3**. Próximo elegível: **SPIDER-PROMPT-021** (operações governadas / workbench) — permanece **PLANNED**. CAP-022–026 permanecem **PLANNED**.

## Referências

- ARCH-010 (métricas, eventos, health, saturação)
- ARCH-011 (admissão / backpressure nas unidades de execução; sem autoscaling/HA)
- ARCH-013 (superfície Capacidade, APIs, authz, screenshots)
- ARCH-014 (espelho funcional 0.20.0; linguagem de negócio)
- Manifesto CAP-020
- Roadmap 016–026
- Contrato anti-drift `spider-roadmap-015-026-contract.json`
