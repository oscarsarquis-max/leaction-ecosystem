# SEGSENSE_REV_015 — Revisão de aderência do PRM_015

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_REV_015 |
| Versão | 1.1 |
| Data | 14/09/2026 |
| Status | PRM_015 executado; único corretivo `SEGSENSE_PRM_015_COR_001` executado nesta etapa. **Não** autoaprovado. Não avança PRM_016. |

## Histórico da ressalva de parada (não apagado)

| Item | Resultado na execução original do PRM_015 | Resultado após COR_001 |
|---|---|---|
| `Stop-Process` só com PID de `pids.txt` em `prove-mvp-http.ps1` | Removido. Prova `PROVIDER_UNAVAILABLE` em Spider isolada. | Preservado. |
| `stop-mvp-demo.ps1` | Recusava só por glob amplo na command line (`*segsense-provider-mock*`, `*spring-boot.run.profiles=local-demo*`). PID reciclado ou processo semelhante no mesmo repo/profile podia coincidir. `Assert-MvpRefusesStalePid` testava `Test-MvpOwnedProcess`, **não** o script que mata. | Stop **não** lê `pids.txt`. Só o ledger gitignored `.mvp-logs/owned-run.json`. Cada alvo passa por PID + listener da porta + executável + marcador único + início. Divergência: sem `Stop-Process`, mensagem, processo intacto. |
| PID obsoleto/reciclado | Helper apenas (`test-mvp-ops.ps1` + `Assert-MvpRefusesStalePid`). | `test-mvp-ops.ps1` invoca o **`stop-mvp-demo.ps1` real** com ledger temporário. |
| Wrappers Maven/npm | PID do launcher era gravado em `pids.txt` e podia ser morto. | Launcher não é alvo. Só o listener comprovado (JVM com `-Dsegsense.mvp.run=`, `node server.js --segsense.mvp.run=`, `mvp-fe-dev.mjs`). |
| Aceite visual 1440/768/390/320/zoom/teclado/impressão | **Não verificado** nesta sessão (sem browser interativo). | Inalterado. Segue para o próximo prompt original. |

## SAT-01 a SAT-10

Distinção: **V1 demo implementado** ≠ certificação/produção.

| SAT | V1 local-demo | Certificação / produção |
|---|---|---|
| SAT-01 Identidade | PARCIAL: `segsense` EXPERIENCE no registry `local-demo` | Sem IdP/mTLS de produção |
| SAT-02 Manifesto | PARCIAL: manifesto preliminar inalterado | NOT_CERTIFIED |
| SAT-03 Contrato | IMPLEMENTADO / DEMO ONLY (`SPIDER-SAT-003`) | Não é certificação de produção |
| SAT-04 BFF | ATENDIDO nesta fatia (Browser→SegSense→V1) | Sem superfície admin autenticada |
| SAT-05 Correlação | ATENDIDO nesta fatia (`correlationId`→`decisionId`→…) | Sem barramento de eventos |
| SAT-06 Assincronia | N/A: `responseChannel=SYNC` somente | Callback ausente |
| SAT-07 Execução Data Plane | N/A: sem `planId`/`executionId` | Fora desta fatia |
| SAT-08 Segurança | PARCIAL: segredo local + ACL + loopback | Sem IdP; não é produção |
| SAT-09 Independência | ATENDIDO: SegSense não conhece routes do mock | — |
| SAT-10 Ops locais | ATENDIDO: jornada demo não exige Spider para o resto do SegSense | — |

## Painel

Alimentado só pela projeção da interação corrente. Sem endpoint público novo. Sem alteração de schema V1. Mock intocado.

## Gates

| Gate | Resultado |
|---|---|
| Frontend test/lint/build | Não reexecutado neste corretivo (sem alteração de UI/produto). Ver execução original do PRM_015: Vitest 70/70; eslint ok; `tsc -b && vite build` ok |
| `mvnw verify` SegSense | Não reexecutado neste corretivo (sem alteração Java). Ver execução original: ok |
| Spider unitário V1 | não tocado |
| Prove HTTP canônico | Prova isolada reexecutada: `providerUnavailableProof=COMPROVADO` (porta `18765` fechada; `PROVIDER_UNAVAILABLE`; sem `providerReference`/itens/`capabilityId`; mock `:8095` pid `10688` e Spider `:8080` pid `54468` inalterados). JVM isolada parada só após verificação de propriedade. |
| Stop real (COR_001) | `test-mvp-ops=ok`. `stop-mvp-demo.ps1` recusou PID obsoleto (`still-running=True`, listener da reunião `10688` intacto), recusou processo semelhante fora desta execução, e parou processo de teste próprio (`action=stopped still-running=False`). Sem ledger da reunião: o script padrão recusou e **não** leu `pids.txt`; pids `10688`/`54468`/`20736`/`47472` inalterados. |
| Visual | **Lacuna:** sem browser interativo. 1440/768/390/320/zoom/teclado/impressão **não verificados** |

## Inventário por aplicação

### segsense/

Painel `SimulationEvidencePanel` (PRM_015); scripts de partida/parada com ledger; `mvp-fe-dev.mjs`; prova isolada com `finally` fail-closed; docs `SEGSENSE_PRM_015`, `SEGSENSE_PRM_015_COR_001`, `SEGSENSE_OPS_001`, esta revisão, JRN_EVID 1.2, DEMO_RUN 1.6, PLN.

### spider/

Sem alteração de schema/rota V1 neste corretivo. Working tree alheio (Experience Hub) **preservado, não editado**.

### segsense-provider-mock/

Sem alteração estrutural. O start passa `--segsense.mvp.run=<guid>` ignorado pelo `server.js`.

### Não tocado

Panne, Hub, School, QMind, Phanton. Sem commit, push, deploy. Sem PRM_016.

## Veredito

PRM_015 **executado**; único corretivo `SEGSENSE_PRM_015_COR_001` **executado**, não autoaprovado. Não haverá segundo corretivo. Lacunas visuais e de produto (entrada de contexto, intenção trabalhada, possibilidades explicadas) seguem para o próximo prompt original.
