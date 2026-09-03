# Screenshots — SPIDER-PROMPT-015, 017, 018, 019, 020, 020A e 020B

Capturas reais (Playwright) contra UI `http://127.0.0.1:5180` + API local-demo:

| Arquivo | Viewport |
|---------|----------|
| `015-implementation-cockpit-desktop.png` | 1440×900 |
| `015-presentation-readiness-desktop.png` | 1440×900 |
| `015-live-execution-desktop.png` | 1440×900 |
| `015-implementation-cockpit-mobile.png` | 390×844 |
| `017-operational-cockpit-healthy-desktop.png` | 1440×900 |
| `017-operational-cockpit-degraded-desktop.png` | 1440×900 |
| `017-operational-cockpit-insufficient-data-desktop.png` | 1440×900 |
| `017-operational-cockpit-mobile.png` | 390×844 |
| `018-failure-lab-catalog-desktop.png` | 1440×900 |
| `018-failure-lab-running-desktop.png` | 1440×900 |
| `018-failure-lab-verified-desktop.png` | 1440×900 |
| `018-failure-lab-runbook-evidence-desktop.png` | 1440×900 |
| `018-failure-lab-mobile.png` | 390×844 |
| `019-worker-runtime-overview-desktop.png` | 1440×900 |
| `019-worker-runtime-backlog-desktop.png` | 1440×900 |
| `019-worker-runtime-draining-desktop.png` | 1440×900 |
| `019-worker-runtime-stale-recovery-desktop.png` | 1440×900 |
| `019-worker-runtime-mobile.png` | 390×844 |
| `020-capacity-overview-desktop.png` | 1440×900 |
| `020-capacity-pressure-desktop.png` | 1440×900 |
| `020-capacity-circuit-open-desktop.png` | 1440×900 |
| `020-capacity-load-shedding-desktop.png` | 1440×900 |
| `020-capacity-mobile.png` | 390×844 |
| `020A-home-operacional.png` | 1440×900 |
| `020A-home-execucoes.png` | 1440×900 |
| `020A-home-status.png` | 1440×900 |
| `020B-home-jornada.png` | 1440×900 |
| `020B-jornada-retry.png` | 1440×900 |
| `020B-jornada-failure.png` | 1440×900 |
| `020B-navegacao-console.png` | 1440×900 |
| `020B-detalhe-execucao.png` | 1440×900 |
| `020B-jornada-wait-resume.png` | 1440×900 |
| `020B-live-execution-start.png` | 1440×900 |
| `020B-live-execution-retry.png` | 1440×900 |
| `020B-live-execution-complete.png` | 1440×900 |
| `020B-step-details-overview.png` | 1440×1000 |
| `020B-step-details-failed-interaction.png` | 1440×1000 |
| `020B-step-details-retry.png` | 1440×1000 |
| `020B-step-details-success.png` | 1440×1000 |
| `020B-step-details-events.png` | 1440×1000 |
| `CTX-001-home-context.png` | 1440×página |
| `CTX-001-business-intents.png` | componente responsivo |
| `CTX-001-intent-preview.png` | componente responsivo |
| `CTX-001-route-resolution.png` | componente responsivo |
| `CTX-001-context-to-execution.png` | 1440×página |
| `CTX-001-context-journey.png` | componente responsivo |
| `CTX-001A-context-home.png` | 1440×página |
| `CTX-001A-spider-entendeu.png` | componente responsivo |
| `CTX-001A-intent-policy-route.png` | componente responsivo |
| `CTX-001A-context-to-dataplane.png` | 1440×página |
| `CTX-001A-context-step-detail.png` | componente responsivo |

Geração:

```powershell
.\scripts\start-presentation.ps1
cd frontend
node .\scripts\capture-presentation-screenshots.mjs
node .\scripts\capture-operational-health-screenshots.mjs
node .\scripts\capture-failure-lab-screenshots.mjs
node .\scripts\capture-worker-runtime-screenshots.mjs
node .\scripts\capture-capacity-resilience-screenshots.mjs
node .\scripts\capture-020a-home-screenshots.mjs
node .\scripts\capture-020b-journey-screenshots.mjs
node .\scripts\capture-020b-live-screenshots.mjs
node .\scripts\capture-020b-step-details-screenshots.mjs
node .\scripts\capture-ctx-001-screenshots.mjs
node .\scripts\capture-ctx-001a-screenshots.mjs
```

As capturas 017 usam o Cockpit Operacional (console + telemetria + saúde). As cinco capturas 018 usam o Failure Lab com `spider.failure-lab.enabled` e `spider.failure-lab.http.enabled`. As cinco capturas 019 usam o Runtime de Workers com `spider.worker-runtime.enabled` e `spider.worker-runtime.http.enabled`. As cinco capturas 020 usam Capacidade & Resiliência com `spider.capacity.enabled` (+ `http` / `local-demo` / `enforcement` conforme o cenário). Os PNGs podem ser produzidos separadamente do fechamento documental.
