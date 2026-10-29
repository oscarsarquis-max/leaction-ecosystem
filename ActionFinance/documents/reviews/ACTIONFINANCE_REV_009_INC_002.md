# ACTIONFINANCE_REV_009_INC_002

| Campo | Valor |
|---|---|
| Data | 02/10/2026 |
| Prompt | [ACTIONFINANCE_PRM_009_INC_002](../prompts/ACTIONFINANCE_PRM_009_INC_002.md) |
| Antecedente | [REV_009_INC_001](ACTIONFINANCE_REV_009_INC_001.md) — não sobrescrito |
| Autorização | Recuperação no escopo PRM_009; sem PRM_010 |
| Aceite | **Não** |

Sem cobrança, pagamento, APPLY histórico ou escrita manual dos nove. PRM_007 permanece separado.

## Tentativas da Loja (PRODUCTION)

Empresa `624023a4-57e3-415c-b7d0-925ca1acd3b7`. Sem nomes nem e-mails.

| Run | Início (UTC) | Fim | Estado | Import/upd/rev | Erro persistido | Correlação | spider_message_id |
|---|---|---|---|---|---|---|---|
| `3843271c-6d5e-4e6c-9b7b-f9fffb2ce0b2` | 12:12:45.682Z | 12:12:45.749Z | FAILED | 0/0/0 | mensagem genérica de transporte | `afr-3843271c-…` / página `afp-3843271c-…-1` | none |
| `b75521a8-3dc7-4f35-987f-43fa1e5bb06b` | 12:12:35.847Z | 12:12:36.748Z | FAILED | 0/0/0 | mesma | `afr-b75521a8-…` / `afp-b75521a8-…-1` | none |

Tarefa AF no momento: `actionfinance-web:5`. `pay_receipt_transaction` da Loja = 0. Títulos = 0. Quatro transações pré-existentes noutra empresa (homolog). Flyway 1–13.

A UI “Sincronização indisponível” / “Não foi possível consultar a Spider” é o rótulo de `FAILED` + `last_error` genérico. **Não** foi falta de login: as duas linhas existem, autenticadas, em PRODUCTION.

## Primeira fronteira (comprovada)

Log AF `/actionfinance/web`:

```
spider list transport failed
correlation=afp-3843271c-6d5e-4e6c-9b7b-f9fffb2ce0b2-1
type=BadRequest
message=400 Bad Request: {"errorCode":"INVALID_PAYLOAD","message":"Envelope canónico inválido."}
```

O pedido **chegou à engine** (JSON 400, não HTML 403 do WAF). Autenticação de satélite passou (senão 401). A validação do schema 1.4 rejeitou o envelope **antes** do provider Hub.

Causa: `financialList.environment` no contrato 1.4 só admitia `HOMOLOG` e `SANDBOX`. O AF envia `PRODUCTION` para a Loja. `DemoSliceRules` repetia a mesma restrição. INC_001 (WAF NAT) não é esta falha.

A tela vazia do Monitor nesta tentativa é coerente: não houve `messageId` remoto nem execução READY. Não prova perda por RAM.

Não foi live_mode, APPLY histórico nem ausência de sessão.

## Correção

| Peça | Antes | Depois |
|---|---|---|
| Schema satélite 1.4 | enum HOMOLOG, SANDBOX | + PRODUCTION |
| `DemoSliceRules` listagem | recusava PRODUCTION | aceita PRODUCTION |
| Controller satélite | 400 sem log do schema | `event=satellite_invalid_payload` com `schemaError` |
| AF `HttpSpiderInteractionClient` | last_error genérico | código + referência `afp-…` |
| Spider | `:8` | `:9` digest `95fd2e618aa01880298c2d415cfa3bc1a1f8e97078beb21c42906c658ad0d49d` |
| AF | `:5` | `:6` digest `ba58fab9c0b1911f9bda12d3014c3c1b0fa29fbd02c01eb57e168127d94a1a90` |

Hub Pay **não** alterado. Sem restart indiscriminado; evidência das 400 permanece no CloudWatch.

## Regressão

- `ActionFinanceSatelliteInteractionHttpTest` 7/7, incluindo `productionListIsAcceptedAndDispatchesSelectedCapability` (antes seria 400).
- `HttpSpiderInteractionClientTest` distingue `INVALID_PAYLOAD` da mensagem genérica.

## Prova pública do percurso (sem sessão do operador)

A partir da VPC/NAT do AF (`run-task` Fargate, mesmos subnets/SG), `POST https://api.spider.actionhub.com.br/v1/satellites/interactions` contrato 1.4, empresa Loja, `environment=PRODUCTION`:

```
http=200
status=READY
capability=LIST_PAYMENT_TRANSACTIONS
itemCount=0
reviewCount=9
environment=PRODUCTION
```

Isto é Finance-path → Spider pública → Hub de produção → Spider. Não é loopback no Hub nem mock. Os nove entram como **reviews** (cobrado presente, pago ausente). Correlação de prova: `afp-inc002-proof-1` / `afm-inc002-proof-1`.

A persistência no AF **ocorreu** depois do reparo 1.4 (run SUCCESS abaixo). O deep link autenticado no Monitor desta execução, com o SPA de retomada, ainda exige o login OIDC do operador — sem extrair cookies.

## Complemento — retomada do Monitor (02/10/2026)

Prompt: [ACTIONFINANCE_PRM_009_INC_002_FOCO_MONITOR](../prompts/ACTIONFINANCE_PRM_009_INC_002_FOCO_MONITOR.md). Este bloco não substitui a causa 1.4 acima.

### Causa comprovada (Monitor, separada do 400)

No `MonitorShell`, a consulta dos eventos da execução selecionada agendava o próximo ciclo só após sucesso não terminal. O `catch` gravava o erro e **parava**. `AbortError` de cancelamento esperado e falha de rede no instante em que a aba perde foco produzem o mesmo efeito: o acompanhamento morre até nova seleção ou «Atualizar». Não havia listener de `visibilitychange`/`pageshow`. `useExecutionPolling` (console) parava às 5 falhas e apagava a última observação ao mudar `paused`/`enabled`.

A prova VPC READY/9 reviews **não** é esta falha. A tela vazia das 12:12Z era ausência de execução READY. A perda de foco é um segundo defeito, no ciclo de atualização do Monitor.

### Correção

| Peça | Mudança |
|---|---|
| `monitorLiveQuery.js` + `useLivePoll.js` | um voo, timeout 12s, backoff ≤15s, abort esperado ≠ falha de negócio, retomada em `visibilitychange`/`pageshow`, pausa manual intacta |
| `MonitorShell.jsx` | lista e detalhe usam o ciclo; «Ao vivo» só com consulta bem-sucedida; «Desatualizado · última atualização …» na falha transitória; 401 pede reentrada no mesmo destino; 403 apaga o recorte em cache |
| `TransactionWorkspace.jsx` | detalhe canónico no mesmo ciclo; fases/seleção locais preservadas |
| `useExecutionPolling.js` | deixa de zerar o detalhe ao pausar; retoma após erro transitório |
| AF `HttpSpiderInteractionClient` | log interno `failureClass=CONTRACT\|PROVIDER\|TRANSPORT` (não publicado em nova imagem neste complemento) |

Formato do Monitor, filtros, busca e fases reais inalterados. Sem cookies alterados.

### Testes

- Frontend: 36 testes (live query, poll, Monitor, workspace, polling). Inclui transitório→retoma, AbortError, visibilidade, pausa, resposta atrasada, sem sobreposição, 401 e 403.
- Navegador real (Playwright, preview local, **sem** derrubar a engine pública): troca de aba (`bringToFront`), minimizar/restaurar, `setOffline` + abort da rota de teste. Resultado: execução permanece selecionada; offline marca `Desatualizado`; não surge lista vazia; após a rede voltar, `Ao vivo`; pausa manual com 0 chamadas extra.
- Spider `ActionFinanceSatelliteInteractionHttpTest` exit 0: PRODUCTION continua aceite; `LIVE` reproduz `INVALID_PAYLOAD` (enum); empresa estrangeira e finalidade indevida continuam 403 antes do provider. HOMOLOG/SANDBOX regressados no mesmo class.
- AF `HttpSpiderInteractionClientTest` distingue CONTRACT / PROVIDER / TRANSPORT.

### Versões publicadas neste complemento

| Peça | Valor |
|---|---|
| Monitor SPA | `index-DdA40Xh-.js` + `index-DIs_2fYa.css` em `s3://spider-sandbox-monitor-web` |
| CloudFront | invalidação `I4TIO52MIZ9UI0MEY53LBHO7YK` |
| Spider engine | permanece `:9` (schema PRODUCTION já publicado no bloco anterior) |
| AF web | permanece `:6`; `diagnoseFailureClass` só no código, sem restart |

GET anónimo a `monitor.spider.actionhub.com.br` continua a redirecionar ao Cognito. Isso é sessão, não o defeito de foco.

### Importação autenticada da Loja (não é a prova VPC)

Run `7a179653-15d5-44f8-9f29-f9fe7486d535` · PRODUCTION · SUCCESS · 12:39:39Z–12:39:40Z · importados 9 / atualizados 0 / revisão 9 · `spider_message_id=afm-d3288e80-77cb-41d6-8c6d-8e0214ad25c3` · correlação `afr-7a179653-…`.

Agregados da Loja (sem ids de encomenda): 9 linhas, 9 em revisão, 9 com cobrado, 9 com pago ausente, 0 com pago preenchido. Títulos=0. Flyway 1–13. As quatro linhas de outra empresa permanecem (txn_all=13). Repetir o sync não é objeto desta leitura.

Deep link canónico do AF: `https://monitor.spider.actionhub.com.br/?q=afm-d3288e80-77cb-41d6-8c6d-8e0214ad25c3&execution=afm-d3288e80-77cb-41d6-8c6d-8e0214ad25c3`

O GET anónimo deste URL cai no Cognito. As fases reais e a retomada após perda de foco **nessa** execução, com o bundle `index-DdA40Xh-.js`, ainda precisam da sessão do Monitor. Não é o 400 das 12:12Z; esse caminho já persistiu.

## O que continua separado

APPLY histórico. Canónica 28/09. PRM_007. Aceite do produto: **não**.
