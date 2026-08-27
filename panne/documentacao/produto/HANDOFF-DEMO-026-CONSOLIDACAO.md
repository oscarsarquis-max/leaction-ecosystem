# Handoff — consolidação Panne Demo 026

## Identidade do envio

| Campo | Valor |
|---|---|
| Branch de consolidação | `feat/panne-demo-026` |
| Remoto | `origin` (`https://github.com/oscarsarquis-max/leaction-ecosystem.git`) |
| Destino | `origin/main` via worktree limpo + cherry-pick |
| SHA final no monorepo | `5cc13bad2f251682b143d9fcf979827070f12837` |
| Deploy | **não executado** |
| CURSOR-027 | **não iniciado** |

## Estado R026-001…012

| ID | Estado |
|---|---|
| R026-001 | validada |
| R026-002 | validada |
| R026-003 | validada |
| R026-004 | validada integralmente |
| R026-005 | validada |
| R026-006 | validada integralmente |
| R026-007 | validada integralmente |
| R026-008 | validada |
| R026-009 | validada integralmente |
| R026-010 | validada integralmente |
| R026-011 | validada integralmente |
| R026-012 | corrigida e revalidada (ciclo técnico Cursor + confirmação Cortex da instância final) |

Documento canônico: `produto/REVISAO-PROPRIETARIO-026.md`.

## Testes (pré-commit na estação)

| Suíte | Comando | Resultado |
|---|---|---|
| Backend | `python -m pytest tests -q` em `panne/backend` | **297 passed**, 2 skipped (~134 s) |
| Frontend | `npm test` em `panne/frontend` | **180 passed** / 30 files (~17 s) |
| Build | `npm run build` (`tsc --noEmit && vite build`) | **OK** (~8 s) |

## Demo local (ciclo limpo, sem mutações)

| Checagem | Resultado |
|---|---|
| `/health` | 200 |
| `/ready` | 200 |
| `/entrar` | 200 |
| Ambiente | demo |
| Banco lógico | `panne_demo` |
| Âncora | `2026-08-24` |
| Instância | efêmera por execução (não contrato permanente) |

## Limitações restantes

- Separação (pick) permanece consulta/impressão na demo; fluxo completo de nova separação ainda não disponível na tela.
- Produção ainda não alterada; próximo passo operacional é planejamento separado de deploy de produção e demo para validadores.
- Artefatos runtime em `.tmp-demo/` continuam locais e ignorados pelo Git.

## Próximo passo

Planejamento separado do deploy de produção e da demo para validadores. **Não** iniciar CURSOR-027 neste handoff.
