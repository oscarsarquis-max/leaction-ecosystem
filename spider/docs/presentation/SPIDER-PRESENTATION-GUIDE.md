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
2. Aba **Implementação**: grupos A–D, CAP-015–018 VERIFIED (Grupo A completo), 019–026 PLANNED, baseline 240/25.
3. Aba **Apresentação**: preflight readiness; se READY, capítulo 4 → `RETRY_THEN_SUCCESS`.
4. Abrir detalhe: journey map + timeline persistidos (2 attempts).

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

## Roteiro 15 minutos

1. ARCH-013 + manifesto como fonte do roadmap.
2. Diferença execution state vs implementation state.
3. Comparar endpoint legado preservado vs jornada canônica (não usar legado na demo).
4. Callback/reconciliation cenário.
5. Capítulo Failure Lab (acima).
6. Troubleshooting (abaixo) e encerramento.

## Perguntas esperadas

| Pergunta | Resposta honesta |
|----------|------------------|
| É produção? | Não — MOCK_ONLY, flags off by default. |
| Tem SLO? | SLOs do Cockpit Operacional são **provisórios** (017), não contratuais. |
| Failure Lab quebra produção? | Não — só mocks; OFF_BY_DEFAULT; sem legado real. |
| JWT na UI? | Não no caminho canônico. |
| Dados inventados? | Não — timeline/plan persistidos; evidência do lab é redigida. |

## Mock versus real

Integração real começa quando capabilities saírem de `MOCK_ONLY` sob governança — ainda não. Adapter real ativo falha readiness.

## Troubleshooting

- Console indisponível: `spider.console.enabled` + `http.enabled`.
- Auth negada: profile `local-demo` + `local-demo.enabled=true`.
- Readiness not-ready: habilitar canonical submit/status conforme checklist.
- Porta ocupada: liberar 8080/5180.

## Encerramento seguro

```powershell
# encerrar processos iniciados pelo start-presentation (PIDs impressos)
Stop-Process -Id <backendPid>,<frontendPid> -Force -ErrorAction SilentlyContinue
```

Não apagar bancos amplos; seed local-demo é idempotente por executionId fixo.
