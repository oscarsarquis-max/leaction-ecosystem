# Auditoria operacional — CURSOR-028-CMS (2026-08-31)

Log: `ops/audit-20260831-114105.log` · CSV: `ops/etapas.csv`

## Tabela

| Etapa | Duração | Processo/comando | Resultado | Anomalia |
|------|--------:|------------------|-----------|----------|
| descoberta/leitura | ~0s | modules + gate | ok | — |
| testes Action Hub | 0,4s | `node --test cms-panne-keys.test.js` | **3 pass** | ExitCode vazio no Start-Process (instrumentação) |
| testes Panne backend | 5,3s | `pytest test_login_editorial.py` | **13 pass** | idem ExitCode |
| testes Panne frontend | 10,1s | `npm.cmd test login-editorial` | **7 pass** | 1ª tentativa com `npm` (não .cmd) falhou no launcher — causa distinta |
| build Panne FE | 10,1s | `npm run build` | ok | sem `npm install` |
| build Hub tsc | 10,1s | `tsc --noEmit` action-hub | ok | — |
| subida serviços | 6,9s | uvicorn :5080 + vite :5180 | ok | Docker off → Hub não subiu |
| geração evidências | 70,2s wall / ~5s útil | `npm exec node capture-028-cms.mjs` | ok (5 PNGs) | **cache miss:** `npm exec` baixou `node@26.8.1` (~65s) |
| encerramento | 3,6s | stop PIDs 7840/28216/17376/28372 | limpo | 1ª tentativa falhou (`$pid` reserved PS) |

**Etapa mais lenta (útil):** evidências wall-clock por overhead `npm exec`; útil real ~5s. Entre testes/builds: FE test / builds ~10s empatados.

## Respostas

1. **Travamento real ou demora?** Demora + falha de instrumentação. Sem hang da IDE; processo Playwright/vite respondiam. Overhead `npm exec` instalando Node.
2. **Causa confirmada:** Docker Desktop off (Hub admin bloqueado); `npm` sem `.cmd` no Start-Process; `$pid` reserved no cleanup; `npm exec` install surpresa.
3. **Órfãos?** Não ao final — :5080/:5180 livres após stop da árvore desta passagem.
4. **Repetição automática?** Não do mesmo comando pela mesma causa. FE refeito com launcher correto; cleanup refeito com nome de parâmetro correto.
5. **Ajuste anti-recorrência:** usar `npm.cmd` / `node` direto; nunca `npm exec` para scripts locais; não usar parâmetro `$pid` no PowerShell; checar Docker antes de prometer Hub UI.
6. **Tempo útil vs perdido:** útil ≈ 45–55s (testes+builds+subida+captura); perdido ≈ 65s (`npm exec`) + ~10s launcher/cleanup.
7. **Terminou limpa?** Sim para Panne local. Hub CMS screenshot pendente por Docker.

## Cursor/IDE

- Último comando longo antes de parecer “parado”: wait loop do capture (60s progress log emitido).
- CPU: node/playwright ativos; não espera de input.
- IDE não perdeu retorno — AwaitShell reportou conclusão.
- Sem reinício automático de pytest/vitest após falha de teste.

## Critério de parada

Não violado para loop de comando. Bloqueio Docker documentado (sem start Docker forçado / sem AWS).
