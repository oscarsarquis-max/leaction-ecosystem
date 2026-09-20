# SEGSENSE_REV_019 — Revisão de aderência do PRM_019

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_REV_019 |
| Versão | 1.1 |
| Data | 15/09/2026 |
| Status | PRM_019 executado; corretivo único `SEGSENSE_PRM_019_COR_001` executado nesta etapa. **Não** autoaprovado. **Não** inicia PRM_020. Sem segundo corretivo. |

## Tela antiga × tela nova (linguagem humana)

**Antes (PRM_018 visível ao patrocinador):** a pessoa escolhia um radio técnico e marcava caixas sem poder dizer o que queria. Não havia prêmio em R$ calculado.

**PRM_019 (URL nova `:15178/demonstracao/mvp-integrado`):** a pessoa descreve o contexto e escreve o que quer. Sem radios. Com dados suficientes, aparece **Cotação simulada** com **R$ 540,00** (apartamento, capital R$ 300.000, 12 meses).

**Desvio corrigido no COR_001:** em **Como este valor foi calculado**, a superfície pública ecoava o texto interno da Spider (`18 bps`, `APARTMENT`, `30000000 centavos`, `54000 centavos`). Isso não é linguagem de negócio.

**Agora (COR_001, mesma URL, mesmos números):**

> O simulador considerou o valor de proteção de R$ 300.000,00, o tipo de imóvel apartamento e o período de 12 meses. Aplicou a regra demonstrativa vigente para esse cenário e calculou um prêmio anual simulado de R$ 540,00.

A frase **não** está fixa no frontend: tipo, capital, período e prêmio vêm dos campos persistidos desta tentativa (`insuredAmountCents`, `dwellingType`, `coverPeriodMonths`, `premiumAnnualCents`), formatados em reais e rótulos humanos. `bps`, enum, centavos brutos, `scenarioKey`, `capability`, `Test Double`, versões de contrato e IDs ficam só em **Detalhes técnicos desta tentativa**.

Evidência visual: `documents/evidencias/SEGSENSE_PRM_019_COR_001/mvp-quote-540-1440.png` e `mvp-quote-technical-1440.png`.

## Origem de cada número mostrado (caso auditado)

| O que a pessoa vê | Origem | Não é |
|---|---|---|
| R$ 540,00 (prêmio) | `simulatedQuote.premiumAnnualCents = 54000` desta execução, após `COMPLETED` do mock | taxa de mercado, Icatu, fallback |
| R$ 300.000,00 (capital) | `simulatedQuote.insuredAmountCents = 30000000` persistido | valor inventado na UI |
| apartamento | `dwellingType=APARTMENT` mapeado para rótulo humano | enum na superfície |
| 12 meses | `coverPeriodMonths=12` persistido | período de apólice real |
| “não alteraram o prêmio” | `nearbyFiresDidNotAdjustPremium=true` nesta resposta | ajuste atuarial |
| 18 / APARTMENT / 30000000 / 54000 / HOME_QUOTE_SYNTHETIC_V1 | só no `details` técnico | linguagem pública |

Fórmula intacta: `premiumAnnualCents = round_half_up(30_000_000 × 18 / 10_000) = 54_000`.

## Frase pública antes → depois

| Superfície | Antes (PRM_019) | Depois (COR_001) |
|---|---|---|
| Como este valor foi calculado | Eco de `humanCalculation` da Spider: “capital × 18 bps”, `APARTMENT`, centavos | Texto derivado dos mesmos campos, em reais e “apartamento” |
| Detalhes técnicos | IDs; memória interna incompleta na dobra pública | Código, bps, centavos, regra e `humanCalculation` internos |

## Matriz de estados (COR_001)

| Estado | Superfície pública | Provider | Evidência |
|---|---|---|---|
| `MISSING_CONTEXT` | Perguntas primeiro; **sem** “Possibilidades ilustrativas”, “Por que surgiram” nem “Nenhuma pendência humana veio nesta resposta” | `mockCalled=false` | HTTP `http-proof.json`; PNG `mvp-missing-questions-1440.png` |
| `SIMULATED_QUOTE_AVAILABLE` / COMPLETED | Resultado e período → dados usados → explicação humana → limites (regra fictícia; incêndios não alteraram) → `details` recolhido | mock calculou 54000 | HTTP quote-540; PNG `mvp-quote-540-1440.png` |
| Replay idêntico | Mesmo `id` e `quoteReference` | não recalcula como fato novo | HTTP `replay.sameId=true` |
| Mudança material | UI descarta o R$ anterior; HTTP **409** na mesma chave | — | PNG `mvp-quote-invalidated.png`; HTTP 409 |
| Provider indisponível | “Provedor ilustrativo indisponível”; **sem** R$ 540,00 nem cotação | `simulatedQuote=null` | `provider-down-http.json`; PNG `mvp-provider-down-1440.png` |
| Jornada ilustrativa antiga | Possibilidades; sem R$ | capability 1.0 | PNG `mvp-family-illustrative-1440.png` |

## Prova visual (Playwright, Chrome headless, `:15178`)

Viewports 1440×900, 768×1024, 390×844, 320×568 e zoom 200%: logo nas posições do PRM_018; overflow horizontal **não** observado. HTTP 200 **não** foi o aceite: a jornada foi clicada.

| Prova | Resultado |
|---|---|
| Explicação pública sem `bps` / `APARTMENT` / centavos brutos | Observado no bloco `.mvp-quote` |
| Detalhes técnicos com regra/taxa/unidades/IDs | Observado com a dobra aberta |
| Teclado | Tab inclui skip-link; anel `rgb(96, 24, 232) solid 3px` no skip-link |
| Impressão | `form` e `.demo-top` ocultos; faixa de simulação visível; “Cotação simulada” da tentativa corrente |
| Ditado real com microfone | **NÃO VERIFICADO**. A UI **não** pediu permissão automaticamente |
| Jornada ilustrativa | Sem R$ |
| Convite `/c/{token}` vigente | **NÃO VERIFICADO** |

Inventário: `documents/evidencias/SEGSENSE_PRM_019_COR_001/inventory-prm019-cor001.json`.

## Gates (COR_001) — falhas anteriores não omitidas

| Gate | Resultado |
|---|---|
| Frontend lint / test / build | **passou** (82 testes; lint limpo após correção de template literal; `tsc -b && vite build` ok). `npm ci` **não** foi reexecutado sobre `node_modules` do Vite isolado `:15178` para não derrubar a stack de auditoria; a instalação vigente reproduziu lint/test/build |
| Mock `node --test` (16, incl. golden R$ 300k → 54000) | **passou** |
| Spider suíte Satellite/capability/1.0+1.1: `SatelliteContractV1Test` (19), `SatelliteContractJsonSchemaTest` (4), `SatelliteContractArchitectureTest` (2), `SatelliteInteractionHttpTest` (4), `SegSenseDemoApiHttpTest` (4), `SegSenseDemoDecisionServiceTest` (3), `SegSenseDemoApplicationAuthTest` (2) | **passou** (38 testes) |
| SegSense `mvnw verify` **primeira** execução | **falhou** (2 ITs): `ContextLinkIT` esperava `http://127.0.0.1:5178/c/` e recebeu `:15178`; `SegSenseApplicationIT` CORS 403 no Origin `:5178`. Causa: variáveis da stack isolada (`SEGSENSE_PUBLIC_BASE_URL`, `SEGSENSE_FRONTEND_ORIGIN`) no processo Maven. **Não** é defeito da fórmula nem da V16 |
| SegSense `mvnw verify` após remover essas variáveis | **passou** — Tests run: 43, Failures: 0. Flyway em banco vazio (Testcontainers) aplicou V1–V16 |
| Flyway volume isolado `:15437` | V1–V16 presentes; V16 `demo simulated quote status` sem reescrita |
| Preflight isolado | `preflight=ok mock=TEST_DOUBLE spider=SATELLITE_CONTRACT_V1 segsense=SEGSENSE` |
| ACL / stop fail-closed `test-mvp-ops.ps1` | **ok**; reunião `:8095/:8080/:8088` intacta |
| Logs e evidências públicas | varredura contra os valores carregados dos segredos locais: **sem vazamento** nos logs `.mvp-logs` nem em `SEGSENSE_PRM_019_COR_001` |

A fórmula **não** foi alterada para passar teste. Nenhuma migration nova.

## Stacks

| Item | Estado |
|---|---|
| Stack nova (prova) | FE `:15178`, BFF `:19088`, Spider `:19080`, mock `:19095` (reiniciado após a prova de queda; PID isolado distinto do mock da reunião), Postgres `:15437` `segsense-postgres-isolated-cor016` |
| Stack `:5178/:8088/:8080/:8095` | **não** morta; PIDs da reunião inalterados nas provas de mock down e `test-mvp-ops` |
| Ledger | `.mvp-logs/owned-run-cor016.json` (gitignored). Parada só com `stop-mvp-demo.ps1 -LedgerPath` desse ledger. Sem `pids.txt` |

## Git

**Não** houve commit, push nem deploy neste corretivo.

| Aplicação | Neste corretivo |
|---|---|
| `segsense/` | UI pública, testes, scripts de prova, docs `SEGSENSE_*`, evidências |
| `segsense-provider-mock/` | **sem alteração de código**; golden 16/16 reexecutados |
| `spider/` satélite/provider | **sem alteração de código** neste corretivo; suíte pertinente reexecutada |
| Experience Hub (`spider/frontend/src/hub/**`, screenshots, relatório) | sujeira **alheia**; **não** faz parte deste corretivo |

## Ressalvas honestas

1. Ditado real com permissão de microfone: **NÃO VERIFICADO**.
2. Convite público vigente: **NÃO VERIFICADO**.
3. Piloto amplo / E2E original do plano: **não** realizado (continua adiado).
4. `npm ci` não foi refeito na pasta do frontend isolado enquanto o Vite `:15178` estava no ar.
5. A API ainda aceita `intentionConfirmed=true` no POST; a UI não mostra as caixas.
6. Isto **não** é cotação Icatu, apólice, proposta nem contratação.

Esta revisão **não** aprova o PRM nem o corretivo. Pare para auditoria. Sem PRM_020.
