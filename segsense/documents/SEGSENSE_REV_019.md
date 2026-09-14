# SEGSENSE_REV_019 — Revisão de aderência do PRM_019

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_REV_019 |
| Versão | 1.0 |
| Data | 14/09/2026 |
| Status | PRM_019 **executado nesta etapa**. **Não** autoaprovado. **Não** inicia PRM_020. Há no máximo um corretivo para este PRM. |

## Tela antiga × tela nova (linguagem humana)

**Antes (PRM_018 visível ao patrocinador):** a pessoa escolhia um radio técnico (“Entender opções ilustrativas”, “Comparar lacunas”, “Pedir cotação vinculante (será recusada, sem chamar o Test Double)”) e marcava duas caixas (“Confirmo esta intenção” e “Confirmo que não informei dados pessoais”) sem poder dizer o que queria. Não havia prêmio em R$ calculado.

**Agora (URL nova `:15178/demonstracao/mvp-integrado`):** a pessoa descreve o contexto (ex.: “Houve incêndios nas proximidades”) e escreve o que quer (ex.: “Quero contratar um seguro residencial”). A tela mostra “Entendi que você quer avaliar uma proteção residencial” e a frase de que **simular não é contratar**. O botão é **Gerar cotação simulada**. Sem os radios e sem as duas confirmações. Se faltar tipo de imóvel, valor ou período, aparecem **perguntas**. Com dados suficientes, aparece **Cotação simulada** com **R$ 540,00** (apartamento, capital R$ 300.000, 12 meses) — o mesmo número que o mock calculou nesta execução. A jornada antiga (“entender opções ilustrativas”) continua devolvendo possibilidades **sem** R$.

Evidência visual: `documents/evidencias/SEGSENSE_PRM_019/mvp-quote-540-1440.png` e `mvp-missing-questions-1440.png`.

## Matriz (executada)

A matriz canônica está em `SEGSENSE_FUN_004`. Prova HTTP na stack isolada (`:19088` → Spider `:19080` → mock `:19095`):

| Passo | Resultado observado |
|---|---|
| Relato de incêndios + intenção residencial, sem campos | `MISSING_CONTEXT`; `missingContext` dwelling/amount/period; `mockCalled=false`; perguntas humanas |
| URL governada `/demonstracao/fontes/proximidade-incendios` + mesma intenção | `MISSING_CONTEXT`; origem `SATELLITE_GOVERNED`; mock **não** chamado; artigo **não** agrava preço |
| Apartamento, R$ 300.000, 12 meses | `SIMULATED_QUOTE_AVAILABLE`; `premiumAnnualCents=54000`; `quoteReference=qte-…`; capability `GENERATE_SYNTHETIC_HOME_QUOTE` |
| Casa, mesmo capital | `66000` centavos (R$ 660,00) |
| Apartamento, R$ 600.000 | `108000` centavos (R$ 1.080,00) |
| Sem contexto | `MISSING_CONTEXT` local; Spider não necessária |
| “quero pagar agora” | `REJECTED` no BFF; `spiderDecisionId=null`; mock não chamado |
| Replay da mesma chave | mesmo `id` e mesmo `quoteReference` / 54000 |
| Mudança de capital na mesma chave | HTTP **409** |
| Mock parado | `MOCK_UNAVAILABLE`; `simulatedQuote=null`; sem prêmio antigo |
| Família + “entender opções” (API antiga) | `PRE_PROPOSAL_AVAILABLE`; itens ilustrativos; **sem** R$ |
| `GET :19095/health` `recentExecutions` | só `preq-…` da Spider; SegSense **não** chama o mock |

Exemplo reproduzível: `premiumAnnualCents = round_half_up(30_000_000 × 18 / 10_000) = 54_000` → **R$ 540,00**. Taxas inventadas (`HOME_QUOTE_SYNTHETIC_V1`); **não** são de mercado nem da Icatu. Incêndios na fonte editorial **não** entram na conta (`nearbyFiresDidNotAdjustPremium=true`).

A UI do navegador, na mesma stack, mostrou **R$ 540,00** e a mesma regra (capital 30_000_000 centavos → 54000).

## Contratos

| Contrato | Estado |
|---|---|
| Satellite 1.0 | Intactos os schemas; jornada ilustrativa e rota legado |
| Satellite 1.1 | Contribuições + atributos de cotação (máx. 8); capital **não** é enum de allowlist |
| Provider 1.0 | `BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO`; só `scenarioKey` |
| Provider 1.1 | `GENERATE_SYNTHETIC_HOME_QUOTE`; inputs numéricos; **não** concatena prêmio em `scenarioKey` |

## Prova visual (Playwright, Chrome headless, `:15178`)

Viewports 1440×900, 768×1024, 390×844, 320×568 e zoom 200%: logo nas posições do PRM_018 (home 142×80; MVP/Icatu/fonte 177×100; admin 106×60 / 92×52 em 320). Overflow horizontal: **não** observado. HTTP 200 **não** foi o aceite: a jornada foi clicada (contexto → intenção → perguntas → R$ 540,00).

| Prova | Resultado |
|---|---|
| Radios / caixas redundantes | Ausentes no carregamento da MVP |
| Teclado | Tab: skip-link → logo → nav → contexto → ditar → URL → fontes → intenção → ditar → CTA. Anel `rgb(96, 24, 232) solid 3px` |
| Impressão | `form` e `.demo-top` ocultos; faixa de simulação visível; “Cotação simulada” da tentativa corrente |
| Ditado real com microfone | **NÃO VERIFICADO**. A UI **não** pediu permissão automaticamente. Fallback de texto permanece |
| Jornada ilustrativa | `mvp-family-illustrative-1440.png`; sem R$ |
| Convite `/c/{token}` vigente | **NÃO VERIFICADO** |
| Logo PNG oficial SHA-256 | `CEF4A9C0B8F7B0D8F2A50D85DE41FEA02498B15E3021EBB063E75945810C089D` (intacto; derivado de header inalterado nesta fatia) |

Inventário: `documents/evidencias/SEGSENSE_PRM_019/inventory-prm019.json`.

## Segurança e privacidade

- Instrução curta para cenário sintético; sem atestado de “não informei dados pessoais” como mecanismo de segurança.
- Validação/minimização no servidor; PII óbvia continua recusada antes do fingerprint.
- Relato bruto **não** atravessa a fronteira Spider; só tema estruturado + atributos de cotação (tipo, capital em centavos, período).
- Sem CPF, nome, endereço exato ou telefone nesta etapa.
- SegSense **não** chama o mock; não conhece taxa nem regra interna.
- Pedido de contratação efetiva recusado no BFF, sem Spider.

## Testes

| Gate | Resultado |
|---|---|
| Mock `node --test` (incl. golden `HOME_QUOTE_SYNTHETIC_V1`) | passou na sessão de implementação (16 testes) |
| Frontend lint / test / build | passou na sessão de implementação (jornada + SHA do PNG) |
| Spider testes focados (Satellite 1.1, demo HTTP, regras) | passaram na sessão de implementação |
| SegSense IT de jornada + Flyway vazio → V16 | passou na sessão de implementação |
| `mvnw verify` completo SegSense / `mvn test` amplo Spider | **não** reexecutados neste encerramento |
| Preflight / ACL / segredos | stack isolada já autenticada; valores **não** impressos |

## Migrations e stacks

| Item | Estado |
|---|---|
| V16 `SIMULATED_QUOTE_AVAILABLE` | aplicada no volume isolado `segsense_pgdata_isolated_cor016` (Postgres `:15437`) |
| Volume da reunião `:5437` | **não** migrado por este PRM |
| Stack nova | FE `:15178`, BFF `:19088`, Spider `:19080`, mock `:19095` (reiniciado após prova de queda; ledger `owned-run-cor016.json`), runId `772742a0a5274f35ba338bb0f6148338` |
| Stack `:5178` | **não** morta; PID da reunião inalterado na prova de mock down |

Parada só com `.\stop-mvp-demo.ps1 -LedgerPath ...owned-run-cor016.json`. Sem `pids.txt`.

## Git

**Não** houve commit, push nem deploy. Working tree mistura este PRM com fatias anteriores (PRM_014–018) e **Experience Hub** (`spider/frontend/src/hub/**` e screenshots) — **não** incluir Hub neste eventual commit. Sem senhas no chat.

## Fontes oficiais e o que não foi verificado

| Fonte | Uso | Não verificado |
|---|---|---|
| SUSEP — informações para escolha de seguro | Distinguir informação, simulação e contratação | — |
| Institucional Icatu (vida, previdência, capitalização) | Não rotular a simulação residencial como oferta Icatu | Contrato/API de seguro residencial autorizado pela Icatu — **ausente** |

## Ressalvas honestas

1. Ditado real com permissão de microfone: **NÃO VERIFICADO**.
2. Convite público vigente: **NÃO VERIFICADO**.
3. Piloto amplo / E2E original do plano: **não** realizado (continua adiado).
4. Parágrafo “Como este valor foi calculado” ainda ecoa `APARTMENT` e centavos (formato da Spider a partir do resultado). O destaque visível é **R$ 540,00** / capital em reais.
5. Processo BFF desta partida ainda devolve `nÃ£o` em `contextElements.note` (bytecode anterior). O fonte Java foi corrigido; **não** foi reiniciado o BFF só por isso.
6. A API ainda aceita `intentionConfirmed=true` no POST; a UI não mostra as caixas — o CTA é a ação explícita.
7. Isto **não** é cotação Icatu, apólice, proposta nem contratação. Sem autorização de provedor real, a entrega é a simulação honesta.

Esta revisão **não** aprova o PRM. Pare para auditoria. Sem PRM_020.
