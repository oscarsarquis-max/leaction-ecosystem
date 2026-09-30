# ACTIONFINANCE_REV_004_COR_001 — Correções de contas, baixas e extrato

Versão 0.1 — 29/09/2026. Execução do corretivo. Sem aprovação de produção/piloto. Sem PRM_005.

O parecer `ACTIONFINANCE_REV_004_PARECER_ANALISTA.md` **não estava no repositório**; o trabalho seguiu o prompt COR_001 e o [REV_004](ACTIONFINANCE_REV_004.md), que permanece intacto.

## C1 — Repetição segura nas escritas de conta

| Campo | Conteúdo |
|---|---|
| Mudança | `AccountCreateDialog`, `AccountFormPage` e `AccountDetailPage` passam a usar `freezeWrite`/`sendPending`. Resultado desconhecido preserva chave/corpo/rota/empresa/ator e oferece «Tentar novamente». 400/409 limpa o pendente e permite nova operação. Troca de contexto (`STALE`) não reenvia. |
| Prova | Vitest: diálogo e página dedicada após perda de transporte (mesma chave/corpo); validação 400 gera nova chave; rename com a mesma chave. IT `replayCreateAccountKeepsSingleOpeningMovement`: duas POST com a mesma chave → 1 conta e 1 OPENING. IT `replayUpdateAccountIsStable`: PATCH repetido → 1 RENAMED. A simulação de transporte é só no frontend; a unicidade é no banco do Testcontainers. |
| Resultado | Passou |
| Pendência | Nenhuma neste recorte |

## C2 — Conflito e tentativa pendente na baixa/estorno

| Campo | Conteúdo |
|---|---|
| Mudança | Em `VERSION_CONFLICT` a tela busca título/baixa atuais, mostra o restante novo e **não** altera o valor digitado nem reenvia. O próximo envio usa versão atual e chave nova. Retry de resultado desconhecido que cai em 400/409 limpa `pending` e `unknownResult`. Estorno com a mesma máquina de estados. |
| Prova | Vitest recebível: 409 → restante R$ 50,00 visível, valor 100,00 preservado, segundo envio com versão 2 e chave nova. Vitest a pagar: timeout + 409 destrava «Registrar pagamento». Vitest estorno: timeout + 400 destrava «Confirmar estorno do registro». |
| Resultado | Passou |
| Pendência | A disputa de duas sessões humanas no mesmo título não foi clicada no Playwright; o 409 + revisão está coberto no Vitest e o lock/rollback no IT de concorrência. |

## C3 — Extrato com fotografia consistente

| Campo | Conteúdo |
|---|---|
| Mudança | `AccountService.movements` em `@Transactional(readOnly=true, isolation=REPEATABLE_READ)`. Cabeçalho e extrato usam só `currentBalanceMinor` dessa resposta. Troca rápida de período incrementa geração e zera o extrato anterior. |
| Prova | IT `movementsStayConsistentAcrossPagesRetroactiveAndConcurrentWrite`: baixa concorrente durante o GET; `previous + entradas − saídas = periodEnd` nas linhas da página completa; page 0 e page 1 (size 20) compartilham os três saldos; OPENING primeiro; movimento em 2026-09-05 visível. Vitest ignora resposta atrasada de outro `to`. |
| Resultado | Passou |
| Pendência | Nenhuma neste recorte |

## C4 — Extrato mobile rotulado

| Campo | Conteúdo |
|---|---|
| Mudança | Cartão: data + tipo, descrição, **Entrada/Saída** ou **Abertura** (inclusive 0/negativo), **Saldo após** separado, «Ver registro» quando há baixa. Estorno identificado além da entrada/saída efetiva. Tabela desktop preservada. Logos não tocados. |
| Prova | `mobile-360-statement.png`: Abertura R$ 200,00 ≠ saldo após; Entrada R$ 50,00 com saldo após R$ 250,00; Entrada R$ 100,00 com saldo após R$ 350,00; Estorno + Saída R$ 50,00 com saldo após R$ 300,00. Desktop `desktop-1280-statement.png`: colunas Entrada/Saída/Saldo após. `scrollWidth = clientWidth` em 360 e 1280. |
| Resultado | Passou |
| Pendência | Nenhuma neste recorte |

## C5 — Jornada real e invariantes

| Campo | Conteúdo |
|---|---|
| Mudança | Playwright `frontend/scripts/capture-cor-001-journey.mjs` cria dados próprios (não seed). ITs de rollback (concorrente deixa 1 alocação/1 movimento/1 histórico) e estorno concorrente (1 reversão + 1 movimento inverso). |
| Prova | Duas jornadas automatizadas (1280 e 360): conta saldo inicial R$ 200,00; título R$ 150,00; baixa 50 → restante 100; baixa 100 → quitado; estorno 50 → restante 50; pagamento 50 em obrigação; viewer sem botões de escrita. Persistência pela API real atrás da UI. |
| Resultado | Passou |
| Pendência | Nenhuma neste recorte |

## Jornada

Tudo **automatizado** (Playwright headless). Nada apenas simulado no frontend. Cliques e preenchimentos em `documents/reviews/screenshots/prm-004-cor-001/journey-log.json`.

Dados criados nesta execução:

| Viewport | Conta | Recebível | Obrigação |
|---|---|---|---|
| 1280 | Conta jornada COR 001 desktop-1280-1790690239992 | Recebível jornada COR 001 desktop-1280-1790690239992 | Obrigação jornada COR 001 desktop-1280-1790690239992 |
| 360 | Conta jornada COR 001 mobile-360-1790690244080 | Recebível jornada COR 001 mobile-360-1790690244080 | Obrigação jornada COR 001 mobile-360-1790690244080 |

Passos por viewport: Entrar na demonstração → Nova conta (200,00 em 2026-09-01) → Novo recebível 150 → Registrar recebimento 50 (Pix) → conferir restante 100 → Registrar 100 → conferir Recebido → abrir baixa 50 → Estornar registro → restante 50 → extrato → Nova conta a pagar 150 → pagamento 50 → Sair → token viewer A (sem Novo recebível / Registrar / Corrigir).

Capturas em `documents/reviews/screenshots/prm-004-cor-001/` (18 PNG + `journey-log.json`). Tentativas anteriores da jornada também deixaram contas/títulos fictícios no banco local; não foram apagadas.

## Testes

| Comando | Contagem | Skip | Exit |
|---|---|---|---|
| `backend\mvnw.cmd verify` | Surefire 7; Failsafe 36 | 0 | 0 |
| `frontend npm run lint` | 0 erros | — | 0 |
| `frontend npm test` | 24/24 | 0 | 0 |
| `frontend npm run build` | ok | — | 0 |
| `npm audit` e `npm audit --omit=dev` | 0 vulns | — | 0 |
| `npm run capture:cor-001` | jornada 1280+360 | — | 0 |

`npm ci` não repetido. Log Maven: `documents/reviews/evidence/prm-004-cor-001/mvnw-verify.log`.

## Dados

Volumes e migrations V1–V5 preservados. **Nenhuma migration nova.** Backup/restore do REV_004 permanece válido (sem mudança de schema/grants). Dados locais de demonstração e as jornadas COR_001 foram acrescentados, não apagados.

## Serviços

Ao encerrar: UI `http://127.0.0.1:5179/` HTTP 200; API `http://127.0.0.1:8091/actuator/health` `status=UP`. Postgres local do ActionFinance intacto.

## Limites

Registro local de fatos. Nenhuma cobrança, Pix, transferência, pagamento ou comunicação externa. ActionFinance continua autônomo e integrável. PRM_005 não emitido nem executado.

## Aceite

A execução não é aprovação. O aceite pertence ao analista após o retorno do proprietário.
