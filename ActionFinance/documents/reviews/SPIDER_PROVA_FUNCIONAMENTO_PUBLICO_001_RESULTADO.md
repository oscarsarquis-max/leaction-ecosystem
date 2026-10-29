# SPIDER_PROVA_FUNCIONAMENTO_PUBLICO_001_RESULTADO

| Campo | Valor |
|---|---|
| Data | 02/10/2026 |
| Protocolo | [SPIDER_PROVA_FUNCIONAMENTO_PUBLICO_001](../prompts/SPIDER_PROVA_FUNCIONAMENTO_PUBLICO_001.md) |
| Autorização | Recuperação PRM_009; sem PRM_010 |
| Aceite | **Não** |
| Funcionamento integral público (jornada autenticada no browser) | **NÃO COMPROVADO** |

Sem cobrança, payout, APPLY, insert manual, cookie extraído ou contorno de OIDC.

## Versões

| Peça | Valor |
|---|---|
| Spider agora | `spider-sandbox-backend:11` · `sha256:51b05e39350327cdfa8fb9d2c5762689ab314abbc598ebab289488cb10a380ea` |
| Spider na sonda satélite / SUCCESS WAF | `:10` · `sha256:95fd2e618aa01880298c2d415cfa3bc1a1f8e97078beb21c42906c658ad0d49d` (substituída; RAM apagada) |
| Telemetria / signal-http | `true` / `true` |
| Persistência | memory · 1 task |
| Edge | `spider-sandbox-monitor-oidc:6` |
| WAF regional `spider-sandbox-api` | default BLOCK · allow `/v1/console` **ou** `/v1/canonical` **e** header de origem CloudFront |
| WAF CloudFront `spider-sandbox-monitor` | default BLOCK · leituras GET/HEAD/OPTIONS · escritas POST/PUT/PATCH/DELETE só em `/v1/console` **ou** `/v1/canonical` |
| CloudFront | `/v1/console/*` e `/v1/canonical/*` → ALB |
| Monitor SPA | `index-obT76M54.js` · invalidação `ICKUI41IAXXT40AZA8OJ12SXGJ` · 15:57:11Z (substitui `index-C6JUX1at.js`) |
| AF Flyway | 1–13 |

## Linha temporal (UTC e −03)

O primeiro dossiê rotulou o replace como «13:33–13:40 −03». Os eventos ECS brutos são **10:33–10:40 −03**, o que é **13:33–13:40Z**. A sonda 13:48Z é **10:48:24 −03**, posterior ao `:10` no ar. Os horários não foram alterados; o erro era o offset no texto.

| Instante UTC | Local −03 | Facto |
|---|---|---|
| 12:39:39.563Z | 09:39:39 −03 | AF run `7a179653` SUCCESS import 9 · msg `afm-d3288e80-…` |
| 12:39:40.356Z | 09:39:40 −03 | Spider READY http=200 corr `afp-7a179653-…-1` |
| 13:20:16.908Z | 10:20:16 −03 | AF run `337dd410` EMPTY import 0 / review 9 · msg `afm-cda669f0-…` (repetição AF autenticada já existente) |
| 13:33:50Z | 10:33:50 −03 | `:9` parada · início da indisponibilidade ~7 min |
| 13:40:00Z | 10:40:00 −03 | `:10` iniciada |
| 13:40:30Z | 10:40:30 −03 | alvo no ALB |
| 13:48:24Z | 10:48:24 −03 | sonda satélite AF-NAT (não é sync Finance) · 22 eventos no store da `:10` |
| 14:11:29Z | 11:11:29 −03 | POST público SUCCESS na `:10` após WAF · `exec-prova001-c-20261002T141129Z` SUCCEEDED |
| 14:16:51Z | 11:16:51 −03 | deploy `:11` · nova janela a 0 tarefas (scheduler + `maximumPercent=100`) |
| 14:23Z | 11:23 −03 | `:11` healthy |
| 14:23:53Z | 11:23:53 −03 | prova dos seis cenários na engine pública |
| 15:42:31Z | 12:42:31 −03 | POST público `/v1/canonical/executions` **depois** da correção do WAF CloudFront: HTTP 401 `application/problem+json` (Edge, sem sessão) |
| 15:42:57Z | 12:42:57 −03 | SPA `index-C6JUX1at.js` publicado |
| 15:57:11Z | 12:57:11 −03 | SPA `index-obT76M54.js` — seleção deixa de voltar ao Finance no poll |

A sonda satélite e o SUCCESS WAF da `:10` **não sobrevivem** no store da `:11`. Não foram reconstruídos.

## Check 1 — `/v1/canonical` e «Falha ao iniciar neste ambiente»

Percurso autorizado do botão: Monitor (OIDC) → CloudFront `/v1/canonical/*` → header de origem → ALB → WAF → engine.

Causa observada do clique falho: a regra WAF `allow-cloudfront-console` só fazia `STARTS_WITH /v1/console`. O POST canónico era **BLOCK** (default). O frontend mapeia qualquer falha sem `executionId` para «Falha ao iniciar neste ambiente.» (`SimulationPanel.jsx`).

Correção: a mesma regra passou a aceitar `/v1/console` **ou** `/v1/canonical`, **ainda exigindo** o segredo de origem. Default continua BLOCK. Sem abertura global.

Prova independente (não é clique no browser): POST ALB `SUCCESS_MULTI_STEP` · 14:11:29Z · http 200 · `SUCCEEDED` · `exec-prova001-c-20261002T141129Z` (engine `:10`). Clique autenticado no SPA: **NÃO VERIFICADO**.

## Check 2 — Seis cenários (não classificar allowlist como PASSOU)

Referência local: `LocalDemoSimulationScenariosTest` (profile `local-demo`) executa os seis com o comportamento esperado.

Recorte público anterior (não era decisão de aceite do protocolo): `SandboxCanonicalCredentials.DEMO_OPERATIONS` = só `SUCCESS_MULTI_STEP`; `SandboxDemoRouteConfig` filtrava o catálogo; `signal-http.enabled=false`. A UI lista os seis; a descoberta `availableScenarios` só devolvia um. Comentário no código: «uma única rota demonstrável no sandbox». Isso **não** dispensa a prova C.

Correção restrita (mock, credencial `sandbox-operator`, sem provider financeiro):

- allowlist dos seis em `SandboxCanonicalCredentials`
- catálogo demo + só `RETRY_THEN_SUCCESS` do Failure Lab
- catálogo de wait + signal-http + adapters de sinal sandbox
- imagem `:11`

Teste local `SandboxSimulationScenariosTest` exit 0.

Prova pública da engine (`:11`, 14:23:53Z), **não** é o clique no Monitor:

| Cenário | Causa anterior | Após correção (engine) | Veredicto browser |
|---|---|---|---|
| SUCCESS_MULTI_STEP | WAF BLOCK | 200 SUCCEEDED `exec-p001-success_multi_step-20261002T142353Z` | **NÃO VERIFICADO** |
| RETRY_THEN_SUCCESS | rota/allowlist ausentes | 200 SUCCEEDED `exec-p001-retry_then_success-20261002T142353Z` | **NÃO VERIFICADO** |
| BUSINESS_NEGATIVE | idem | 200 SUCCEEDED `accepted=false` `exec-p001-business_negative-…` | **NÃO VERIFICADO** |
| WAIT_SIGNAL_RESUME | signal-http off + sem wait catalog | 202 WAITING_EXTERNAL → sinal 200 `ACCEPTED_AND_RESUMED` | **NÃO VERIFICADO** |
| CALLBACK_RECONCILIATION | allowlist | 200 SUCCEEDED sync mock `exec-p001-callback_reconciliation-…` · reconciliação HTTP de callback **não** ligada no sandbox (`callback.reconciliation.enabled` permanece false; ingresso público de callback não publicável) | **NÃO VERIFICADO** / lacuna de reconciliação assíncrona |
| TECHNICAL_FAILURE | allowlist | http 500 (falha técnica); este probe não devolveu `executionId` no corpo lido | **NÃO VERIFICADO** no público por identidade; local `FAILED` |

`availableScenarios` público da `:11`: os seis nomes.

SegSense / SpiderBank: botões sem URL de produto (`VITE_*` vazio no SPA publicado). `GET /v1/console/monitor/simulation` no sandbox declara satélites não publicados. É **navegação sem URL**, não autorização para publicar esses produtos. Dependência externa específica; sem ordem para os alterar.

Canónica 28/09/2026 15:20:33: **FALHOU** (perda histórica). Execução nova não a substitui.

## Check 3 — Repetição no AF e os três conjuntos

A sonda satélite **não** é persistência AF. A repetição AF já existente:

| Run | UTC | Status | import/upd/rev | msg |
|---|---|---|---|---|
| `7a179653-…` | 12:39:39.563Z | SUCCESS | 9/0/9 | `afm-d3288e80-…` |
| `337dd410-…` | 13:20:16.908Z | EMPTY | 0/0/9 | `afm-cda669f0-…` |

Depois do segundo sync (janela até 14:09Z):

| Conjunto | Loja | Global |
|---|---|---|
| `financial_title` | 0 | 0 |
| `settlement` | 0 | 0 |
| `cash_movement` | 0 | 0 |
| `pay_receipt_transaction` | 9 ids distintos · fp `f9d0cdc0f029e904802dfc696ab20a43` | 13 |
| `pay_receipt_transaction_revision` | 9 · 1 `sync_run_id` (só o SUCCESS) | — |

O segundo sync AF **não** duplicou transações, **não** gerou revisão nova e **não** criou título, baixa nem movimento. Hashes iguais do provider, sozinhos, não provam isto; estes totais sim.

Sync autenticado **novo** na UI: **NÃO VERIFICADO** (OIDC Finance).

## Check 4 — returnTo ≠ login completo

Cookie anónimo 302: `returnTo=/?q=afm-prova001-20261002T134747Z&execution=…` prova só a preparação do redirect. Callback Cognito, seleção e fases no SPA: **NÃO VERIFICADO**.

A sonda `afm-prova001-…` **não** substitui o deep link de um sync Finance. Deep link AF ainda válido no RDS: `?q=afm-d3288e80-77cb-41d6-8c6d-8e0214ad25c3&execution=afm-d3288e80-77cb-41d6-8c6d-8e0214ad25c3` — eventos dessa mensagem **não** estão no store da `:11`.

## Check 5–6 — Indisponibilidade e deploy

Duas janelas a 0 tarefas com `desired=1`, `maximumPercent=100`, `minimumHealthyPercent=0`, store RAM:

1. `:9`→`:10` · 13:33:50Z–13:40:00Z (~6,5 min)
2. `:10`→`:11` · 14:16:51Z–~14:23Z (~6 min); o scheduler chegou a matar a task pendente `ce06a532` («Scaling activity initiated by deployment»)

**Não** se alterou percentual de rollout. Réplica extra **não** foi criada (custo). Memória **não** sobrevive a replace. Evidências exportadas em logs/IDs acima **antes** da `:11`. Plano: 1 task; exportar IDs/CloudWatch antes de qualquer replace; não afirmar retenção RAM; não abrir segunda réplica sem decisão.

## Prova A / B / C — matriz do protocolo

| # | Critério | Veredicto |
|---|---|---|
| A1 | Rastrear 7a179653 | **PASSOU** (AF + log Spider; Hub bruto ausente neste account) |
| A2 | Não reconstruir eventos | **PASSOU** |
| A3 | Correções antes de nova execução | **PASSOU** (telemetria, WAF, cenários) |
| A4 | Finance UI → sync → Monitor mesma sessão | **NÃO VERIFICADO** — login humano |
| A5 | Origem Hub produção / reviews | **PASSOU** na sonda satélite (separada do AF) |
| A6 | Sem duplicação no AF | **PASSOU** (SUCCESS→EMPTY, fp estável, rev=9/1 run) |
| A7 | Títulos / baixas / movimentos | **PASSOU** (três zeros na Loja e no global) |
| B1 | Deep link sem sessão → Cognito + returnTo | **PASSOU** (preparação) |
| B2 | Login + fases no browser | **NÃO VERIFICADO** |
| B3 | Troca de aba pública | **NÃO VERIFICADO** |
| C1 | Clique «Sucesso em múltiplas etapas» no SPA | **NÃO VERIFICADO** — bloqueio do POST comprovado e corrigido; clique autenticado ainda não observado |
| C2 | Seis cliques públicos | **NÃO VERIFICADO** — ver matriz do complemento; engine auxiliar não substitui |
| C3 | Canónica 28/09 | **FALHOU** |

Hashes satélite (não são persistência AF): [evidence/prm-009-prova-001/origem-destino-hashes.md](evidence/prm-009-prova-001/origem-destino-hashes.md).

## Complemento — cliques públicos (02/10/2026)

A habilitação dos seis botões e as linhas anteriores na lista **não** comprovam o clique. A requisição do SPA é `POST https://monitor.spider.actionhub.com.br/v1/canonical/executions` (mesma origem, cookie de sessão). Essa chamada foi reproduzida sem adivinhar WAF regional, login ou allowlist.

| Fronteira | Antes da correção | Depois |
|---|---|---|
| Browser → CloudFront | HTTP **403** `text/html` (página CloudFront). Sem `executionId`. A SPA mapeia isto para «Falha ao iniciar neste ambiente.» | HTTP **401** `application/problem+json` sem sessão (Edge). Com sessão, o pedido deixa de morrer nesta fronteira. |
| WAF CloudFront `spider-sandbox-monitor` | default BLOCK. `allow-monitor-reads` = GET/HEAD/OPTIONS. `allow-console-writes` = POST só `STARTS_WITH /v1/console`. POST `/v1/canonical/*` = `Default_Action`. Logs CF WAF: `terminatingRuleId=Default_Action` em pedidos `canonical`. | A mesma regra de escrita passou a aceitar `/v1/console` **ou** `/v1/canonical`. Default continua BLOCK. |
| POST `/nao-autorizado` | 403 HTML | 403 HTML — ingresso **não** ficou global |
| GET `/v1/console/monitor/events` sem sessão | 401 JSON Edge | 401 JSON Edge (lista autenticada inalterada) |
| Engine / ALB | O POST autenticado **não nascia**. Não há `executionId` a recuperar deste clique. | Sem novo replace ECS. `:11` inalterada. |
| SPA | Qualquer falha sem identidade → texto genérico | `index-C6JUX1at.js`: mostra HTTP/código; se o corpo ou o GET posterior tiver execução (500/422), abre-a no Monitor em vez de mascarar |

Causa do clique «Retry com sucesso»: a execução foi **recusada antes de nascer** no WAF do CloudFront (403 HTML). Não foi criada e escondida. Não foi a falha transitória deliberada do cenário Retry. Não foi o WAF regional do ALB (esse já aceitava `/v1/canonical` com o segredo de origem). Não foi ausência de sessão no momento da lista (GET passa em `allow-monitor-reads`).

Correção aplicada sem abrir ingresso global e sem novo custo/réplica. Terraform `allow-console-writes` alinhado. Script `spider/infra/aws/scripts/prm009-prova001-cf-waf-canonical-writes.py`.

### Matriz dos seis — clique público

Provas ALB/engine de 14:23:53Z permanecem **auxiliares**. Clique = **NÃO VERIFICADO** até observação na sessão autenticada.

| Cenário | Causa comprovada do clique falho | Correção | Clique público | Esperado vs observado | Veredicto |
|---|---|---|---|---|---|
| Sucesso em múltiplas etapas | POST canónico 403 CF WAF; sem `executionId` | WAF CF + SPA | ainda não observado nesta sessão | Esperado: etapas e `SUCCEEDED`. Observado: — | **NÃO VERIFICADO** |
| Retry com sucesso | POST 403 corrigido. Relato do proprietário: linha verde `SUCCEEDED`. Isso **não** aprova o cenário: a seleção voltava ao Finance e impedia conferir tentativas | WAF CF + correção da seleção (`index-obT76M54.js`) | `SUCCEEDED` relatado; tentativas/fases **não** conferidas | Esperado: falha transitória na **mesma** execução e sucesso, com linha/detalhe/eventos/origem estáveis. Observado: verde sem permanência da escolha | **NÃO VERIFICADO** |
| Negativa de negócio | Idem | Idem | ainda não observado | Esperado: decisão negativa explícita, distinta de erro técnico | **NÃO VERIFICADO** |
| Espera, sinal e retomada | Idem; sinal também é POST `/v1/canonical/signals` (mesmo prefixo agora permitido) | Idem | ainda não observado | Esperado: espera observável, sinal controlado, retomada da mesma execução | **NÃO VERIFICADO** |
| Callback e reconciliação | Idem; reconciliação HTTP sandbox continua `callback.reconciliation.enabled=false` | WAF CF não liga callback assíncrono | ainda não observado | Esperado: callback externo controlado reconciliado. Síncrono mock **não** fecha este cenário | **NÃO VERIFICADO** / lacuna de reconciliação assíncrona **BLOQUEADA** (configuração sandbox; não forçada) |
| Falha técnica | Idem; 500 da engine sem identidade na SPA antiga mascarava FAILED já criado na sonda ALB | SPA recupera `executionId` do 500/GET | ainda não observado | Esperado: FAILED deliberado navegável. HTTP 500 sem rastreio não basta | **NÃO VERIFICADO** |

SegSense / SpiderBank: continuam **navegação sem URL** no SPA publicado. Não são produto indisponível por este WAF. Sem autorização para os publicar.

Simulação mock ≠ percurso FORWARD Finance/Pay. Badge financeiro de uma execução AF não se aplica a estes cliques.

## Complemento — seleção volta ao Finance

Causa demonstrada no código publicado até `index-C6JUX1at.js`, `MonitorShell.jsx`:

```
useEffect(() => {
  const wanted = params.get('execution') || params.get('q');
  setSelected(match ? match.id : wanted);
}, [transactions]);
```

`transactions` muda a cada ciclo ao vivo (~4 s) e ao voltar da aba Simulação. Se o Monitor foi aberto pelo deep link do Finance (`?q=afm-…&execution=afm-…`), este efeito **reaplica a execução financeira** e descarta o clique no Retry. Não é o poll «escolher o mais recente» (`live[0]` só corre quando ainda não há seleção). Não se desligou a atualização automática para mascarar o defeito.

Correção em `index-obT76M54.js`:

- escolha manual (`open` / simulação) fica em `userPicked` e deixa de ser sobrescrita pelo `q`/`execution` do Finance;
- `replaceState` grava `execution=` da escolha e remove o `q` conflitante;
- a linha escolhida é recolocada na janela das 5 mais recentes (`pinSelectedArrival`);
- troca Monitor ↔ Simulação e «Atualizar» com «Ao vivo» mantêm a mesma identidade.

Teste que reproduz o deep link Finance + clique Retry + refresh ao vivo, **sem** pausar: `MonitorShell.test.jsx` «does not return a manual Retry selection to the Finance deep link after a live refresh». Vitest 30/30 nestes ficheiros.

Prova da permanência no **navegador público**: **NÃO VERIFICADO**. O Chrome preparado desta sessão ficou só com `chrome://intro/`; não há sessão Monitor acessível ao executor agora. Sem extração de cookie. Verde na lista não é aceite do Retry.

## Sessão acompanhada (única intervenção restante)

Checks independentes deste complemento estão feitos (POST 403→401, WAF não global, SPA publicada, engine sem replace). Falta só autenticação humana no browser **já aberto e acessível ao executor** (Chrome CDP local, perfil temporário da prova; cookies não extraídos).

As abas anteriores fecharam. Reabrir o Monitor e o Finance no Chrome preparado da prova.

Pedido: **apenas login** nessas duas abas. Não executar sync nem os seis botões. O executor continua de imediato, **sem pausar** o ao vivo: clicar o Retry já existente, confirmar que a seleção não volta ao Finance após o poll e a troca de aba, inspecionar tentativas/fases/origem mock; depois sync Loja e os restantes cenários.

Ignorar o ecrã «Faça login no Chrome» do perfil temporário.

Pendências intactas e separadas: canónica 28/09, retenção RAM / janelas de replace, regressão Pay, APPLY histórico, HMAC live, preapproval, PRM_007. Sem PRM_010. Aceite **não**.
