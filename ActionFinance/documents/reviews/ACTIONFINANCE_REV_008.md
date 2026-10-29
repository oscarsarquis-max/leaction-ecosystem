# ACTIONFINANCE_REV_008 — Primeira fatia via Spider (consulta ActionHub Pay)

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_008 |
| Prompt | [ACTIONFINANCE_PRM_008](../prompts/ACTIONFINANCE_PRM_008.md) |
| Data | 30/09/2026 |
| Executor | Cursor |
| Ambiente | Isolado / homologação local. **Sem ativação em produção.** |
| Aceite | Analista: **aprovado e encerrado** em 01/10/2026 no recorte isolado. [Encerramento](ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA.md). Relato original abaixo preservado. |

Este relatório não declara viabilidade geral da Spider nem integração Pay em produção.

## Residual do PRM_007 (não misturar)

Concluído no ciclo anterior: login humano, nome Loja de Pães, logout/CSRF autenticado, restore PITR isolado e limpeza (só o RDS de produção ficou). Digest `sha256:7c4cc0de…da5b65`.

Não concluído para aceite final do PRM_007: invalidação de `SPRING_SESSION` no banco restaurado. Publicação **não** declarada. Este PRM_008 **não** reabre restore nem pede novo login.

## Matriz factual do ActionHub Pay

Levantamento em `leaction-platform/services/gateway-api`. Marketplace Flask não tem rotas de pagamento.

| Capacidade | Estado | Endpoint / código | Auth | Empresa | Teste | Nota |
|---|---|---|---|---|---|---|
| Recebimento (checkout inbound) | Existe | `POST /v1/payments`, `POST /v1/checkout/amount`, sessions/catalog | Variável (amount exige app secret) | `app_id` / `client_id` | Token MP `TEST-` | Cliente paga o Hub |
| Pagamento de saída | Ausente | — | — | — | — | Não inventar payout |
| Consulta S2S por ID | Parcial | `GET /v1/checkout/amount/:orderId` | App secret + allowlist | Mesmo app | — | Só cobrança avulsa |
| Consulta S2S PanelDX | Ausente | sem `GET /v1/payments/:id` | — | — | — | |
| Borda Spider (este ciclo) | Proposto/implementado | `GET /v1/integration/payments/:orderId` | `X-Spider-Provider-Key` + `X-Pay-App-Id` | App mapeado pela Spider | Sem secrets no AF | Adaptação mínima |
| Estados finais | Existe | `PENDING` / `PAID` / `CANCELLED` / `REFUNDED` | — | — | — | Mapeados para acompanhamento |
| Cancelamento | Parcial | `POST /v1/checkout/amount/:id/cancel` | App secret | Mesmo app | — | Não é estorno |
| Estorno API | Ausente | — | — | — | — | Painel MP |
| Idempotência create | Parcial | amount checkout `Idempotency-Key` | App | — | — | `POST /v1/payments` sem chave |
| Eventos / webhook | Existe no Hub | `/webhooks/mercadopago` + outbox | Sem assinatura no handler atual | Por `external_reference` | — | **Não** usado neste recorte; sem webhook AF |
| Spider/provider prévio | Ausente | — | — | — | — | |

Decisão: a fatia demonstrável é **consulta de recebimento de teste**. Pedido de pagamento sandbox **não** foi implementado: o Pay não oferece payout e o create inbound exigiria meio seguro de resolver timeout sem duplicar cobrança — o amount checkout tem idempotência, mas este ciclo não autoriza criar cobrança real nem sandbox de valor.

## Lacunas da Spider (antes → agora)

| Lacuna 1.2 | Estado após PRM_008 |
|---|---|
| Purpose só seguro/crédito | 1.3 acrescenta `FINANCIAL_EXTERNAL_LOOKUP` sem reutilizar 1.2 `extensions` |
| EXPERIENCE não executa capability | Mantido. AF só `QUERY_STATUS` / declaração |
| Sem satélite `actionfinance` | Registry local-demo; **não** é certificação |
| Idempotência Spider em RAM | Continua em RAM. Deduplicação durável da consulta está no AF (`external_operation`) |
| Sem provider Pay | `actionhub-pay` + `HttpActionHubPayCapabilityAdapter` + dispatcher |
| Gates INT apontavam PRM_005/006 | IDs já usados; correção em INT_001 §6 |

Contratos 1.0–1.2 e testes SegSense/SpiderBank não foram reescritos.

## Componentes e dados

| Peça | Papel | Caminho |
|---|---|---|
| Contrato 1.3 | Purpose + `extensions.financialLookup` | `spider/backend/src/main/resources/contracts/satellite/1.3/` |
| EXPERIENCE `actionfinance` | Intenção e acompanhamento | `application-local-demo.yml` |
| PROVIDER `actionhub-pay` | Executa `LOOKUP_ACTIONHUB_PAYMENT` | adapter HTTP + bindings empresa→`pay_app_id` |
| Borda simulador | `POST .../executions` em `:8097` | `spider/tools/actionhub-pay-edge/server.js` |
| Borda Pay real | `GET /v1/integration/payments/:id` | `leaction-platform/services/gateway-api/domain/spider-pay-lookup.js` |
| AF V8/V9 | mapping, operação, inbox/outbox | `database/migrations` |
| AF cliente | Só URL da Spider | `HttpSpiderInteractionClient` |
| UX | Painel no detalhe se `homolog=true` | `frontend/src/App.tsx` |

Mapeamento local explícito: empresa demo `11111111-1111-4111-a111-111111111111` → `homolog-padaria`. Não é a Loja de Pães de produção (`624023a4-…`). Produção recusa `integration.homolog=true`.

## Como executar a fatia isolada

1. Subir a borda: `ActionFinance/scripts/dev/start-prm008-slice.ps1` (`127.0.0.1:8097`, modo SIMULATOR).
2. Spider `local-demo` com `SPIDER_ACTIONFINANCE_APPLICATION_SECRET`, `SPIDER_ACTIONHUB_PAY_EDGE_SECRET` e `SPIDER_ACTIONHUB_PAY_EDGE_URL=http://127.0.0.1:8097`.
3. AF `local-demo` com `ACTIONFINANCE_INTEGRATION_HOMOLOG=true`, `ACTIONFINANCE_SPIDER_BASE_URL=http://127.0.0.1:8080` (porta real da Spider), **sem** URL/secret do Pay.
4. Abrir um título da Padaria Exemplo → “Consultar no ActionHub Pay” com `pay-homolog-0001`.
5. Correlation: o mesmo `correlationId` sai do AF, aparece na Spider e volta no painel (detalhes de rastreio).

Se `ACTIONHUB_PAY_BASE_URL` estiver na **borda** (não no AF), o simulador encaminha ao GET real. Sem isso, `origin=SIMULATOR`.

## Provas e limites

| # | Pedido | O que este ciclo cobre | Limite |
|---|---|---|---|
| 1 | Intenção → roteamento → Pay → AF | Teste HTTP Spider + serviço AF | Pay **real** só se a borda encaminhar e o Hub estiver no ar |
| 2 | Replay / conflito de chave | Mesma chave reconsulta; fingerprint diferente → 409 | Concorrência real de dois JVM não provada |
| 3 | Resposta perdida sem duplicar execução | Lookup não cria cobrança; `DROP_FIRST` na borda | Pedido de pagamento **bloqueado** |
| 4 | Restart | Identidade da operação no Postgres AF | Idempotência da Spider some no restart (RAM) |
| 5 | Evento duplicado / empresa errada | Empresa fora do allowlist 403; confirmado não regride | Sem canal de eventos Push |
| 6 | AF sem Spider não fala com Pay | Cliente AF só tem `spiderBaseUrl`; produção sem homolog | Instrumentação de rede compose não empacotada |
| 7 | Sem permissão / empresa trocada | Membership + mapping + allowlist Spider | — |
| 8 | Contratos antigos / AF manual | 1.0–1.2 intactos; baixa manual independente | — |

**Serviço real:** AF e Spider Java.  
**Sandbox Pay:** borda GET implementada; **não** exercitada contra Hub vivo neste relatório.  
**Simulador:** borda `:8097`, identificado em `providerOrigin`.  
**Não implementado:** payout, create sandbox de cobrança, webhook, baixa automática, Panne, certificação de satélite, gasto AWS novo.

## Parecer técnico

A prova **demonstra orquestração**: o EXPERIENCE não escolhe URL do Pay; a Spider valida propósito 1.3, empresa e binding, seleciona `LOOKUP_ACTIONHUB_PAYMENT` no registry e despacha o adapter do provider. Isso é diferente de um proxy AF→Pay.

A prova **não** demonstra integração real com ActionHub Pay nem execução segura de pagamento. Sem payout, sem create inbound neste ciclo, e sem Hub sandbox exercitado, o aceite de “viabilidade ponta a ponta com Pay” **não** cabe. O que cabe é: o modelo EXPERIENCE → orquestração → PROVIDER aguenta uma consulta financeira versionada, com isolamento de empresa e persistência no AF.

Lacunas que ainda impedem execução real segura: persistência da Spider; canal async autenticado; payout ou create com resolução de timeout no Pay; vínculo produção Loja de Pães↔app Pay; ativação (não autorizada aqui).

## Encerramento do analista

Ciclo **aprovado e encerrado** em 01/10/2026, com COR_001 e COR_002. Parecer integral: [ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA](ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA.md). Este relato original não foi reescrito. Sem PRM_009.
