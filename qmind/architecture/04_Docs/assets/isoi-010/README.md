# ISOI-010 screenshots

Capturas com dados fictícios `[DEMO-ISOI-010]` — sem PII.

| Arquivo | Vista |
|---------|--------|
| `cockpit-desktop-full.png` | Desktop completo |
| `cockpit-filtered-queue.png` | Fila filtrada |
| `cockpit-mobile-width.png` | Mobile ~390px |
| `cockpit-drilldown-ei.png` | Evolution / EI |

```powershell
cd C:\Projetos\qmind\web
$env:QMIND_E2E_BASE_URL='http://127.0.0.1:4179'
npx playwright test e2e/iso-intelligence-cockpit-screenshots.spec.ts
```
