# Screenshots — SPIDER-PROMPT-015, 017, 018 e 019

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

Geração:

```powershell
.\scripts\start-presentation.ps1
cd frontend
node .\scripts\capture-presentation-screenshots.mjs
node .\scripts\capture-operational-health-screenshots.mjs
node .\scripts\capture-failure-lab-screenshots.mjs
node .\scripts\capture-worker-runtime-screenshots.mjs
```

As capturas 017 usam o Cockpit Operacional (console + telemetria + saúde). As cinco capturas 018 usam o Failure Lab com `spider.failure-lab.enabled` e `spider.failure-lab.http.enabled`. As cinco capturas 019 usam o Runtime de Workers com `spider.worker-runtime.enabled` e `spider.worker-runtime.http.enabled`. Os PNGs podem ser produzidos separadamente do fechamento documental.
