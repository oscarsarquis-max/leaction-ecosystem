# SPIDER Presentation Guide

## Pré-requisitos

- JDK 21, Maven 3.9+, Node 20+
- Portas livres: `8080` (API), `5180` (UI)
- Sem acesso a legado/rede real

## Validar

```powershell
cd C:\Projetos\spider
.\scripts\validate-presentation.ps1
```

## Iniciar demo

```powershell
cd C:\Projetos\spider
.\scripts\start-presentation.ps1
```

URLs típicas:

- UI: http://127.0.0.1:5180
- Readiness: http://127.0.0.1:8080/v1/console/presentation/readiness
- Implementation: http://127.0.0.1:8080/v1/console/implementation

Flags: profile `local-demo` + `spider.console.*` + canonical HTTP conforme script.

## Roteiro 3 minutos

1. Badge **DEMONSTRAÇÃO MOCK** no topo.
2. **Home operacional**: Spider 0.20.0, Health UP, Presentation READY, Runtime SIMULATED_INFRASTRUCTURE, Integrations MOCK_ONLY.
3. Últimas execuções visíveis (sem 401). Ação **Executar demonstração** usa `POST /v1/canonical/executions` e acompanha a **Jornada visual** na Home (somente etapas com evidência; retry visível em `RETRY_THEN_SUCCESS`).
4. Navegação agrupada: Execuções / Operação / Testes & demonstração / Plataforma — não é mais uma fita plana de abas.
5. Aba **Implementação** (grupo Plataforma): grupos A–D, CAP-015–020 VERIFIED (Grupo A 4/4; Grupo B 2/3), 021–026 PLANNED.
6. Aba **Apresentação**: preflight readiness; se READY, capítulo 4 → `RETRY_THEN_SUCCESS`.
7. Detalhe: o que aconteceu → por onde passou → quando (timeline) → o que tecnicamente ocorreu.

## Roteiro 8 minutos

1. Visão geral (amostra paginada — não é SLO).
2. Lista/filtros de execuções.
3. Cockpit: flags redigidas, fronteira Mock.
4. Apresentação capítulos 1–8.
5. Jornada `WAIT_SIGNAL_RESUME` se signal HTTP Mock habilitado; senão explicar checklist.
6. Segurança: posture REDACTED, sem JWT.

## Capítulo Failure Lab (PROMPT-018)

Quando as flags `spider.failure-lab.*` estiverem ligadas no local-demo:

1. Abrir a aba **Failure Lab** — banner permanente MOCK_ONLY / falhas simuladas.
2. Mostrar o catálogo (7 cenários): retry, falha terminal, wait/resume, sinal rejeitado, callback incerto, amostra insuficiente, degradação operacional.
3. Executar um cenário (ex.: `RETRY_THEN_SUCCESS`) com confirmação explícita.
4. Acompanhar status do run → predicados → runbook provisório → evidência redigida.
5. Enfatizar: fault injection **só via mocks**; o lab **não** controla a Engine nem toca legado real.

## Capítulo Runtime de Workers (PROMPT-019)

Quando as flags `spider.worker-runtime.*` estiverem ligadas no local-demo:

1. Abrir a aba **Runtime de Workers** — banner de infraestrutura simulada / sem legado real.
2. Mostrar resumo (status, stale, leases), tabela dos 7 tipos, schedules e backlogs.
3. Demonstrar drain com confirmação explícita (quando permitido).
4. Opcional: Failure Lab cenários `WORKER_*` (crash após claim, contenção, drain, backlog, restart).
5. Enfatizar: runtime dá **posse** (lease/fencing); processors continuam com a **semântica**; OFF_BY_DEFAULT.

## Capítulo Capacidade & Resiliência (PROMPT-020)

Quando as flags `spider.capacity.*` estiverem ligadas no local-demo:

1. Abrir a superfície **Capacidade & Resiliência** — banner de infraestrutura simulada / sem capacidade produtiva aferida.
2. Mostrar modo (`MONITOR_ONLY` vs `ENFORCED`), pressão por escopo, bulkheads e circuits.
3. Drill-down de uma decisão recente → policy/version → reason code.
4. Opcional: Failure Lab cenários `CAPACITY_*` (bulkhead, backlog, circuit, quota, load shedding com fencing intacto).
5. Enfatizar: admissão **antes** do claim; sem HA multi-instância; estado de pressão em memória; OFF_BY_DEFAULT.

## Roteiro 15 minutos

1. ARCH-013 + manifesto como fonte do roadmap.
2. Diferença execution state vs implementation state.
3. Comparar endpoint legado preservado vs jornada canônica (não usar legado na demo).
4. Callback/reconciliation cenário.
5. Capítulo Failure Lab (acima).
6. Capítulo Runtime de Workers (acima).
7. Capítulo Capacidade & Resiliência (acima).
8. Troubleshooting (abaixo) e encerramento.

## Perguntas esperadas

| Pergunta | Resposta honesta |
|----------|------------------|
| É produção? | Não — MOCK_ONLY, flags off by default. |
| Tem SLO? | SLOs do Cockpit Operacional são **provisórios** (017), não contratuais. |
| Failure Lab quebra produção? | Não — só mocks; OFF_BY_DEFAULT; sem legado real. |
| Workers são cluster produtivo? | Não — SIMULATED_INFRASTRUCTURE no store; OFF_BY_DEFAULT; sem Kafka/K8s. |
| Capacidade é autoscaling real? | Não — governo simulado (bulkhead/circuit/quota); sem HA; estado em memória. |
| JWT na UI? | Não no caminho canônico. |
| Dados inventados? | Não — timeline/plan persistidos; evidência do lab é redigida. |

## Mock versus real

Integração real começa quando capabilities saírem de `MOCK_ONLY` sob governança — ainda não. Adapter real ativo falha readiness.

## Troubleshooting

- Console indisponível: `spider.console.enabled` + `http.enabled`.
- Auth negada no **console**: profile `local-demo` + `local-demo.enabled=true`.
- Auth 401 no **ingress canônico**: header `X-Spider-Credential-Ref: local-demo-console` (allowlist; não é permitAll). Sem header o DenyAll permanece.
- Readiness not-ready: habilitar canonical submit/status conforme checklist.
- Porta ocupada: liberar 8080/5180.

## Encerramento seguro

```powershell
# encerrar processos iniciados pelo start-presentation (PIDs impressos)
Stop-Process -Id <backendPid>,<frontendPid> -Force -ErrorAction SilentlyContinue
```

Não apagar bancos amplos; seed local-demo é idempotente por executionId fixo.
