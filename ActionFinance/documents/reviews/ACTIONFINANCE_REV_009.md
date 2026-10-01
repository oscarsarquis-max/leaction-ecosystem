# ACTIONFINANCE_REV_009 — Sincronização de recebimentos com passagem visível pela Spider

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_009 |
| Prompt | [ACTIONFINANCE_PRM_009](../prompts/ACTIONFINANCE_PRM_009.md) |
| Data | 01/10/2026 |
| Executor | Cursor |
| Ambiente | Homologação local comprovada. Implantação pública **executada**. Sync autenticado pendente. |
| Aceite | Parcial local preservado. Aceite do proprietário **depende** da jornada no browser. |

Este relatório não declara integração Pay em produção, sandbox do processador, payout, baixa automática nem PRM_010.

## Estados do ADENDO_001 (01/10/2026)

| Estado | Valor |
|---|---|
| Correções COR_001 concluídas | **Sim** — [REV_009_COR_001](ACTIONFINANCE_REV_009_COR_001.md) |
| Pacote pronto para aprovação | Superado — [recomendação de execução](ACTIONFINANCE_REV_009_RECOMENDACAO_EXECUCAO_ANALISTA.md) |
| Implantação autorizada | **Sim** — [autorização](../prompts/ACTIONFINANCE_PRM_009_AUTORIZACAO_PROPRIETARIO.md) |
| Implantação executada | **Sim** — [REV_009_EXECUCAO_PUBLICA](ACTIONFINANCE_REV_009_EXECUCAO_PUBLICA.md) |
| Jornada pública validada tecnicamente | **Parcial** — hosts e isolamento ok; sync novo exige login do operador |
| Aceite do proprietário | **Não** |

Classificação global de publicação: **não declarada.** Host AF no ar desde o PRM_007. Invalidação de `SPRING_SESSION` no restore isolado **continua pendente** e não é resolvida por esta demonstração. PRM_007 permanece identificado em separado. PRM_010 não emitido.

Adendo integral: [ACTIONFINANCE_PRM_009_ADENDO_001_ACEITE_PUBLICO](../prompts/ACTIONFINANCE_PRM_009_ADENDO_001_ACEITE_PUBLICO.md). Levantamento público: [survey-publico-2026-10-01](evidence/prm-009-adendo-001/survey-publico-2026-10-01.md).

## Encerramento do PRM_008 (já emitido)

O analista encerrou o PRM_008 + COR_001/COR_002 em 01/10/2026 no recorte isolado. Cópia: [ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA](ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA.md). Este ciclo **não** reabre esses corretivos.

Residual do PRM_007 (invalidação de sessões restauradas) permanece separado.

## Levantamento — IDs e cardinalidades

Rastreio: `/dashboard/admin/payments` → API admin → tabela Hub `orders`.

| Conceito | Identificador no Hub | Cardinalidade |
|---|---|---|
| Pedido / linha de cobrança Hub | `orders.id` | Uma linha por tentativa corrente daquele checkout |
| Transação do processador | `orders.gateway_reference` | Distinta de `orders.id`; pode ser nula |
| Tentativa | Não há tabela `payment_attempts` | Nova tentativa cria outra ordem ou reusa a mesma via `gateway_ref` |

**Não** tratar `orderId` como `paymentId` do processador.

### Causa do “—” / receita R$ 0,00 na captura do proprietário

O painel admin serializa e soma `valor_negociado` (reais). Checkout avulso grava `amount_cents`. O resumo visual **não** é a fonte do valor. O endpoint de listagem lê, nesta ordem: `amount_cents` → `paid_amount_cents` → `valor_negociado` só se for BRL com exatamente duas casas. Ausência fica nula + `amountAbsent`. Nunca null→0, nunca BRL inventado, nunca timestamp inventado. Sem scraping da página admin.

## Alterações por produto

### ActionHub Pay (`leaction-platform`)

- `GET /v1/integration/payments` (antes de `/:orderId`): empresa/app (`X-Pay-App-Id`), ambiente HOMOLOG|SANDBOX, paginação `limit` 1–50, cursor opaco `{v,a,e,u,i}` validado por app+ambiente.
- Ordenação `updated_at ASC, id ASC`; filtro de sandbox no SQL quando não isolado; rechecagem JS de `app_id` e sandbox comprovado.
- Item público: identidade, status original, valor em unidades mínimas ou ausência, moeda só se vier, datas, `testLabeled`. Sem payload bruto, token ou cartão.
- Simulador da borda **não** lista: `404` “listagem simulada não substitui o Hub”.
- Testes: `spider-pay-lookup.test.js` (9) — `amount_cents`, precisão de `valor_negociado`, sem BRL inventado, cursor fora de escopo recusado.

Dados de teste no banco do Hub são permitidos e devem ser rotulados. Isso **não** prova sandbox vivo do processador nem leitura de produção.

### Spider

- Contrato **1.4**: `LIST_PAYMENT_TRANSACTIONS`, `PURPOSE_FINANCIAL_EXTERNAL_LIST`, `LIST_EXTERNAL_PAYMENTS`, `FINANCIAL_LIST_SOURCE`. Schema novo em `contracts/satellite/1.4/`. 1.0–1.3 intactos.
- EXPERIENCE continua sem `EXECUTE_CAPABILITY`. A Spider escolhe a capacidade.
- Adapter `HttpActionHubPayCapabilityAdapter` + `ActionHubPayListIdentity` (empresa/app/ambiente; `importPersisted=false`).
- Eventos reais: `SATELLITE_REQUEST_RECEIVED` → `SATELLITE_COMPANY_AUTHORIZED` → `CAPABILITY_DISPATCHED` → `OUTBOUND_REQUEST_STARTED` → `PROVIDER_RESULT_RECEIVED` → `SATELLITE_RESPONSE_RETURNED`. Sem etapas inferidas.
- Monitor existente estendido (`projectExecutionJourney.js`, `?q=` + `?execution=`). Sem painel paralelo.
- Retenção do Monitor: RAM, ~24 h / 2 000 eventos; some no restart. Não afirmar histórico persistente.
- Testes HTTP de listagem + empresa estrangeira; identidade do adapter; projeção do Monitor 19/19. Contratos 1.0–1.3 regressão mantida.

### ActionFinance

- V12 incremental (`V12__pay_receipt_sync.sql`): execução, página, checkpoint, transação externa, revisão. Sem FK para título. Grants mínimos; sem DELETE de runtime; sem seed real.
- `PayReceiptSyncService`: HTTP fora de TX; persistência da página + checkpoint da página na mesma TX curta; marco global só no SUCCESS/EMPTY; UNIQUE um `RUNNING` por escopo (409 na disputa); retomada pelo `resume_cursor`; revisão antiga não sobrescreve revisão nova; valor ausente fora de somas.
- API `GET/POST /api/v1/pay-receipts`; leitura `titles:read`; sincronizar `titles:write`.
- UX `/pay-receipts`: filtro de empresa, ambiente visível, última sincronização, lista/cartões, detalhe, “Ver execução na Spider”, aviso de que importar não movimenta dinheiro.
- IT `PayReceiptSyncIT` 4/4 no Postgres 17.6 + V12: múltiplas páginas, datas/IDs coincidentes, valor válido e ausente, pendente/aprovado/reembolsado, repetição sem duplicata, alteração de registro antigo, falha entre páginas + retomada, disputa 409, viewer 403, ambiente incompatível 400. **Spider mockada nestes ITs** — prova persistência AF, não Hub vivo.
- Frontend: lint, vitest 39/39, `vite build` OK.

## Contrato do item (comum)

Identidade estável (`transactionId` = `orders.id`), `orderReference` (neste recorte igual ao id Hub), `processorReference` distinto ou nulo, empresa/binding, origem `ACTIONHUB_PAY`, ambiente, status original e normalizado, `amountMinor` string ou ausência explícita, moeda ou nulo, datas da origem, `originRevision` quando houver, `testLabeled`. Aprovado ≠ liquidação ≠ dinheiro disponível.

## Paginação e retomada

Primeira sincronização percorre o histórico autorizado. Seguintes usam o checkpoint `(updated_at, id)` — inclui cancelamentos, reembolsos e atualizações de registros antigos (sobe `updated_at`). Não filtra só `created_at` nem só aprovados.

Cursor opaco validado por app+ambiente. Alteração durante a paginação: o registro reaparece na janela seguinte; AF deduplica por identidade e aplica só revisão mais nova. Datas iguais desempatam por `id`.

Sem entrega automática de eventos. Sem polling agendado. Ação: **Sincronizar recebimentos**.

## Classificação de prova (separada)

| Classe | Exercitada neste ciclo? | O que isso prova |
|---|---|---|
| Hub real local + banco descartável | **Parcial.** Endpoint e testes de unidade do código real do Pay. Postgres descartável do Hub **não** foi populado nem chamado via FORWARD. | Código de listagem existe; não prova o fio AF→Spider→Hub |
| Simulador | **Não** substitui listagem. Borda devolve 404 se pedirem lista simulada | Não pode ser usado para aceite desta fatia |
| Sandbox do processador | **Não** | Não prova Mercado Pago / meio de pagamento vivo |
| Produção | **Não** lida, não escrita | — |

**Declaração explícita:** só a primeira classe foi tocada, e só no código/unidade. O aceite do prompt pede o fio vivo com banco descartável do Hub. Esse fio **não** foi corrido: em 01/10/2026 o gateway Hub `:4001` e o Monitor `:5180` estavam fora; a engine Spider `:8080` respondia `UP`. O simulador **não** foi usado no lugar do Hub.

## Provas pedidas × estado

| # | Pedido | Estado |
|---|---|---|
| 1 | Várias páginas, IDs/datas iguais, valor válido e ausente, pendente/aprovado/reembolsado; 1º lote, repetição, alteração antiga | **IT AF + unidade Hub.** Não no Hub descartável vivo |
| 2 | Falha entre páginas + restart AF; disputa de dois acionamentos | **IT AF** (mock Spider) |
| 3 | Empresa errada, cursor de outra empresa, ambiente incompatível; credenciais fora do browser/logs | Empresa/cursor: testes Hub + Spider + AF. Credenciais no browser vivo: **não** capturado |
| 4 | Spider interrompida, Hub saudável: sem nova chamada ao provider; AF preserva; religar retoma | **Não exercitado** (Hub/Monitor fora) |
| 5 | Navegador 360/768/1280; sincronizar no AF; abrir execução na Spider; mesma correlação nas três fronteiras | **Não exercitado.** CSS/rota prontos; sem capturas |
| 6 | Antes/depois: sem baixa/título/movimento; backup/restore isolado das estruturas novas, sem RDS | Integridade no IT (`integrity` counts). Backup/restore V12 **não** corrido |

## Gates de verificação

| Gate | Resultado | Caminho |
|---|---|---|
| Hub `spider-pay-lookup.test.js` | 9 passed / 0 fail (reexecutado 01/10) | `evidence/prm-009/verify-2026-10-01/hub-spider-pay-lookup.test.log` |
| Spider testes da fatia + 1.0–1.3 | `mvn -Dtest=ActionFinance…,ActionHubPayList…,SatelliteContractJsonSchema,SatelliteContractV1,SpiderBank…` exit 0 | `evidence/prm-009/verify-2026-10-01/spider-backend-targeted.log` |
| Spider frontend lint/test/build | lint OK; 190 testes; vite build OK | `evidence/prm-009/verify-2026-10-01/spider-frontend.txt` |
| AF frontend lint/test/build | lint OK; 39 testes; vite build OK | `ActionFinance/frontend` |
| AF `mvnw verify` integral | BUILD SUCCESS 01:44; Surefire 31; Failsafe 57 (PayReceiptSyncIT 4); Flyway 12 | `evidence/prm-009/verify-2026-10-01/mvnw-verify.log` |
| Fio vivo FORWARD + browser | **Bloqueado** | Hub `:4001` e Monitor `:5180` recusam conexão; engine `:8080` UP |

Logs por execução devem ficar em pastas novas; não somar XML antigos de `target`. Teste mockado **não** foi classificado como integração real.

## UX e rastreabilidade

- AF: navegação homolog “Recebimentos do Pay”; estados vazios/carregando/sucesso/sem novidades/parcial/indisponível/revisão/negado; “Valor não informado”; selo de teste; link autenticado para o Monitor.
- Spider: Monitor existente; seis fatos reais; `importPersisted` permanece desconhecido/false na Spider.
- Retenção: AF Postgres durável; Spider RAM.

## Documentos atualizados

| Documento | Versão | Caminho |
|---|---|---|
| Prompt integral | 0.1 | [`ACTIONFINANCE_PRM_009.md`](../prompts/ACTIONFINANCE_PRM_009.md) |
| DAT | 0.92 | [`ACTIONFINANCE_DAT_001.md`](../data/ACTIONFINANCE_DAT_001.md) |
| INT | 0.62 | [`ACTIONFINANCE_INT_001.md`](../integrations/ACTIONFINANCE_INT_001.md) |
| UX | 0.10 | [`ACTIONFINANCE_UX_001.md`](../ux/ACTIONFINANCE_UX_001.md) |
| Guia do proprietário | 0.2 | [`ACTIONFINANCE_PRM_009_GUIA_PROPRIETARIO.md`](../operations/ACTIONFINANCE_PRM_009_GUIA_PROPRIETARIO.md) |
| Adendo aceite público | 0.1 | [`ACTIONFINANCE_PRM_009_ADENDO_001_ACEITE_PUBLICO.md`](../prompts/ACTIONFINANCE_PRM_009_ADENDO_001_ACEITE_PUBLICO.md) |
| COR_001 | 0.1 | [`ACTIONFINANCE_REV_009_COR_001.md`](ACTIONFINANCE_REV_009_COR_001.md) |
| Pacote de publicação | 0.1 | [`ACTIONFINANCE_PRM_009_PACOTE_PUBLICACAO.md`](../operations/ACTIONFINANCE_PRM_009_PACOTE_PUBLICACAO.md) |
| Este review | 0.1 | este ficheiro |

## Fora deste ciclo

Deploy, AWS/DNS, escrita em produção, commit/push, dinheiro real, payout, baixa automática, Panne, PRM_010, invalidação de sessão do PRM_007.

## Parecer técnico do executor

A fatia de **contrato, persistência, paginação, permissões e UX** está implementada e coberta por testes isolados. A orquestração EXPERIENCE → Spider escolhe a capacidade; o AF não conhece URL nem credencial do Pay.

O aceite do prompt **não** está fechado: falta o fio ActionFinance → Spider → código real do Hub com Postgres descartável, a evidência no Monitor e as capturas de viewport. Sem essa passagem, o proprietário ainda não consegue ver a execução na Spider com o Pay de verdade. O impedimento concreto é operacional (Hub e Monitor locais fora), não ausência de endpoint.

Parar para revisão do analista.

## Adendo — CONTINUIDADE_001 (01/10/2026)

Prompt: [ACTIONFINANCE_PRM_009_CONTINUIDADE_001](../prompts/ACTIONFINANCE_PRM_009_CONTINUIDADE_001.md). O relato acima permanece. Este adendo cobre o percurso real.

### Ambiente preparado (nada em 5433 / RDS)

| Peça | Endereço | Papel |
|---|---|---|
| Hub Postgres descartável | `127.0.0.1:55432` `hub_prm009` | 26+ cobranças de teste + outra empresa |
| Listagem Pay (código `spider-pay-lookup.js`) | `127.0.0.1:4101` | `ACTIONHUB_PAY_LOOKUP_*` isolado |
| Borda FORWARD | `127.0.0.1:8098` mode=FORWARD | Não lista por simulador. `:8097` SIMULATOR ficou intocada |
| Spider engine | `127.0.0.1:8080` local-demo | EDGE_URL=`:8098` |
| Monitor | `http://127.0.0.1:5180/` | Existente; RAM 24h/2000 |
| ActionFinance | UI `http://127.0.0.1:5179/` API `:8091` | homolog, empresa Padaria `11111111-1111-4111-a111-111111111111` |

O processo em `:4101` monta o `registerSpiderPayLookupRoutes` real. `server.js` completo do gateway **não** foi ligado para não herdar `DATABASE_URL` do Hub compartilhado em `:5433`.

### Percurso exercitado

1. Primeira carga: **SUCCESS**, 26 importadas, 2 páginas. Outra empresa não vazou. `001=12550`, `002=15000` (cobrado, não `paid_amount_cents=14000`), `003` ausente (não zero). Integridade títulos 44→44, baixas 55→55, movimentos 96→96.
2. Repetição: **EMPTY**, imported=0.
3. Alteração de `001` para REFUNDED na origem: **SUCCESS**, updated=1.
4. Falha na 2ª página (borda `list-fail-after=1`): **PARTIAL**, retomada pelo `resume_cursor`. Disputa **200 + 409**. Viewer **403**.
5. Spider interrompida (só a engine, Hub saudável): contador Hub **5→5**, 156 itens preservados, AF informa indisponibilidade. Religada: sync **EMPTY**.
6. Browser 360/768/1280: sem overflow. Sincronizar + **Ver execução na Spider** abriu `http://127.0.0.1:5180/?q=afm-e01b453b-…&execution=afm-e01b453b-…` (ACTIONFINANCE / LIST_EXTERNAL_PAYMENTS / READY). Credenciais da borda **não** aparecem.
7. Eventos reais da mesma execução: `SATELLITE_REQUEST_RECEIVED` → `SATELLITE_COMPANY_AUTHORIZED` → `CAPABILITY_DISPATCHED` (`LIST_PAYMENT_TRANSACTIONS`) → `OUTBOUND_REQUEST_STARTED` (`actionhub-pay`) → `PROVIDER_RESULT_RECEIVED` → `SATELLITE_RESPONSE_RETURNED`. Monitor local-demo não tem login por empresa; o recorte é loopback desta engine.

Evidências: `documents/reviews/evidence/prm-009-continuidade-001/`.

### Correções no percurso

- RUNNING órfão no restart: `reclaimAllRunning` + `reclaimStaleRunning` (PT60S). IT novo verde.
- Cliente AF tratava `PROVIDER_UNAVAILABLE` como página vazia de sucesso; agora `available=false`.
- Cursor Hub: `date_trunc('milliseconds', updated_at)` — `now()` com microssegundos fazia a mesma página voltar e a janela não terminar. Guardas: máx. 20 páginas e interrupção se a página se repetir.
- Restore V12 isolado em `:55433`: 16 runs, 156 transações, 157 revisões, 1 checkpoint. FKs para `company` não restauradas de propósito (dump só das tabelas V12). Sem RDS.

### Classificação

| Classe | Exercitada |
|---|---|
| Hub real local + banco descartável + FORWARD | **Sim.** Código `spider-pay-lookup.js`, 26+ pedidos de teste |
| Simulador | Não usado para listar (`:8097` permanece SIMULATOR, fora deste fio) |
| Sandbox do processador | **Não** |
| Produção / dados reais da loja | **Não** |

### Serviços deixados no ar

AF `:5179`/`:8091`, Spider `:8080`, Monitor `:5180`, Hub isolado `:4101`, borda FORWARD `:8098`, Postgres descartável `:55432`. Sem commit/push/deploy.

Aceite do analista no recorte local. Entrega ao proprietário **intermediária** até a jornada nos hosts públicos.

### Adendo 001 — aceite público (01/10/2026)

COR_001 fechado. Pacote aplicado: [PACOTE_PUBLICACAO](../operations/ACTIONFINANCE_PRM_009_PACOTE_PUBLICACAO.md) v0.4. Relato: [REV_009_EXECUCAO_PUBLICA](ACTIONFINANCE_REV_009_EXECUCAO_PUBLICA.md). Autorização ≠ aceite. Sem PRM_010.
