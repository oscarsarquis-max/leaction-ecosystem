# Screenshots — SPIDER-PROMPT-015 e 017

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

Geração:

```powershell
.\scripts\start-presentation.ps1
cd frontend
node .\scripts\capture-presentation-screenshots.mjs
node .\scripts\capture-operational-health-screenshots.mjs
```

As quatro capturas 017 são geradas contra o Cockpit Operacional com as flags de console, telemetria e saúde operacional habilitadas. Os PNGs podem ser produzidos separadamente do fechamento documental.
