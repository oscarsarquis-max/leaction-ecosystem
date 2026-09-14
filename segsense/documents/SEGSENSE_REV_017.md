# SEGSENSE_REV_017 — Revisão de aderência do PRM_017

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_REV_017 |
| Versão | 1.1 |
| Data | 14/09/2026 |
| Status | PRM_017 executado; único corretivo COR_001 nesta etapa. **Não** autoaprovado. Não inicia PRM_018. |

## Reprogramação

O identificador PRM_017 **não** entregou hardening amplo. Entregou **proveniência fiel** e a **experiência demonstrável** da jornada contextual. Segurança/conformidade original permanece adiada (`SEGSENSE_PLN_001` v1.22, `SEGSENSE_ADR_006`). Sem renumeração silenciosa: o hardening **não** passou a ser o PRM_018.

## Contrato

| Versão | Estado |
|---|---|
| Satellite Contract **1.0** | Bytes dos schemas `contracts/satellite/1.0/` **inalterados** (`git diff` vazio). Rota legado SegSense continua 1.0 `SATELLITE_GOVERNED`. Clientes EXPERIENCE existentes inalterados. |
| Satellite Contract **1.1** (DEMO ONLY) | Novo. Jornada pública `POST /api/v1/public/demo/protection-journeys`. `contributions[]` obrigatórias. Headline `USER_DECLARED` válida. Spider aceita 1.0 e 1.1. Resposta ecoa `contractVersion`. `spiderPath` desta prova: `SATELLITE_CONTRACT_V1_1_THEN_CAPABILITY_RESOLUTION`. |

Não é certificação de produção, Provider Satellite certificado, Icatu nem encerramento de `SEGSENSE_REQ_002`.

## Matriz antes / depois — proveniência

| Caso | Antes (PRM_016 / COR_001) | Depois (PRM_017) |
|---|---|---|
| Relato escrito / ditado revisado | BFF escolhia fixture `family()`/`renda` e enviava `sourceType=SATELLITE_GOVERNED` | Contribuição `VISITOR_DECLARED`, `sourceType=USER_DECLARED`, `sourceId=SEGSENSE_DECLARED_*`. Tema só do parser limitado. Narrativa bruta **não** atravessa a fronteira |
| URL governada só | `SATELLITE_GOVERNED` + `sourceId` editorial | Igual na headline; uma contribuição `GOVERNED_SOURCE`; `sourceTimestamp` = publicação do registro (`2026-09-13T12:00:00Z`) |
| URL + relato mesmo tema | Uma provenance governada | Duas contribuições; `selectedContribution=BOTH`; headline `USER_DECLARED`; `scenarioKey` do id **governado** |
| URL + relato temas distintos | `AMBIGUOUS` local (COR_001) | Mantido: **sem** chamada Spider |
| Relato insuficiente / vazio | `MISSING_CONTEXT` local (COR_001) | Mantido |
| Intenção recusada | Spider `REJECTED`; mock não chamado | Mantido; proveniência declarada ainda ecoada |
| UI | Podia sugerir que a Spider interpretou o texto | Rotula mapeamento SegSense vs fonte editorial vs decisão Spider |

Não se atribui à Spider a inferência de palavras-chave feita no BFF.

## Matriz antes / depois — timestamps (UTC)

| Campo | Antes | Depois | Prova HTTP isolada |
|---|---|---|---|
| `message.createdAt` | `GovernedDemoOrigin.CAPTURED_AT` (`2026-09-13T12:00:00Z`) | Instante UTC do submit que monta o envelope | `2026-09-14T16:01:32.231185600Z` ≠ fixture |
| `objective.declaredAt` | O mesmo fixture | Instante UTC da confirmação persistida (o submit com `intentionConfirmed=true`) | `2026-09-14T16:01:32.231185600Z` ≠ fixture |
| `sourceTimestamp` editorial | O mesmo fixture, misturado | Publicação imutável da fonte; rotulado à parte | URL familiar: `editorial=2026-09-13T12:00:00Z` |
| `sourceTimestamp` declarado | Inexistente / misturado | Igual a `createdAt` desta mensagem (não há captura anterior persistida) | Relato: `sourceTimestamp=2026-09-14T16:03:15.838888600Z`; `editorialSourceTimestamp=null` |

`createdAt` e `declaredAt` coincidem neste fluxo porque a confirmação é o mesmo clique de envio. Não se fabrica um horário de digitação não medido. Fixture editorial **não** preenche os três campos.

## Exemplos A/B (stack isolada, 14/09/2026)

| Entrada | `origin.sourceType` / `selectedContribution` | `scenarioKey` | Primeiro `code` | Capability / provider (Spider) |
|---|---|---|---|---|
| URL familiar + `UNDERSTAND_PROTECTION_OPTIONS` | `SATELLITE_GOVERNED` / `GOVERNED_SOURCE` | `SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1` | `ILLUSTRATIVE_FAMILY_CONTINUITY_CONVERSATION` | `BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO`; `preq-8236106b-…`; `ill-c1b3c367-…`; `spd-c6e8a1be-…`; contrato `1.1` |
| Relato renda + `COMPARE_COVERAGE_GAPS` | `USER_DECLARED` / `VISITOR_DECLARED` | `SEGSENSE_DECLARED_INCOME_INTERRUPTION_V1` | `ILLUSTRATIVE_INCOME_GAP_COMPARE` | mesma capability; `preq-44719a35-…`; `ill-f83697b2-…` |
| Relato familiar (sem URL) | `USER_DECLARED` | `SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1` | (READY) | Distinto do `sourceId` editorial |
| URL familiar + relato complementar mesmo tema | `USER_DECLARED` / `BOTH` (2 contribuições, ambas `used=true`) | `SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1` | READY | Mock recebeu a chave governada\|intenção |
| URL familiar + relato renda | — | — | `AMBIGUOUS`; `spiderDecisionId` vazio | Spider **não** chamada |
| Relato `asdf` / vazio | — | — | `MISSING_CONTEXT` | Spider **não** chamada |
| `REQUEST_BINDING_QUOTE` | `USER_DECLARED` | declarado familiar | `REJECTED`; `mockCalled=false`; 0 itens | Sem capability |
| Replay idêntico | — | — | mesmo `id` `b07ce4c4-…` | Fingerprint v2 |
| Mudança material na mesma chave | — | — | HTTP **409** | Sem projeção da tentativa anterior |
| Mock isolado parado | — | — | `MOCK_UNAVAILABLE`; 0 itens; `spd-3303c9d6-…` | Mock **reiniciado** depois; URL nova permanece no ar |

Chaves distintas observadas no Test Double (`recentExecutions`): três combinações `scenarioKey|objetivo`. SegSense **não** chamou o mock.

### Envelope 1.1 recebido pela Spider (não sensível)

Captura sanitizada de um POST público de relato familiar (sem texto bruto, sem credencial):

- `contractVersion=1.1`
- `objective.origin=USER_DECLARED`; `objective.text=UNDERSTAND_PROTECTION_OPTIONS`
- `provenance.sourceType=USER_DECLARED`; `sourceId=SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1`
- `captureMethod=SATELLITE_DECLARED`; `trustLevel=DECLARED`
- contribuição única `VISITOR_DECLARED` / `used=true` / `elements.theme=family_continuity` (sem `situation`/`need` editoriais)
- `spiderPath=SATELLITE_CONTRACT_V1_1_THEN_CAPABILITY_RESOLUTION`
- `capabilityId=BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO` (escolha da Spider, não do BFF)

Exemplo contratual versionado (sem PII): `spider/backend/src/main/resources/contracts/satellite/1.1/examples/declared-only.request.json` e `url-plus-declared.request.json`.

## URLs

| Papel | URL | Estado nesta sessão |
|---|---|---|
| **Versão nova (auditoria visual)** | `http://127.0.0.1:15178/demonstracao/mvp-integrado` | **Ativa** após a prova HTTP. Frontend isolado HTTP 200. BFF `:19088` `SEGSENSE`/`UP`. Spider `:19080` `UP`. Mock `:19095` `ok` (reiniciado com marcador do `runId` do ledger). Postgres `:15437` volume `segsense_pgdata_isolated_cor016` **não** apagado |
| Reunião (código antigo, sem ledger desta jornada) | `http://127.0.0.1:5178/demonstracao/mvp-integrado` | Ainda no ar (HTTP 200). **Não** é a jornada nova. Pids inalterados: mock **10688**, Spider **54468**, BFF **20736**, FE **47472**, Postgres **42872** |

Não anunciar `:5178` como PRM_017. Não matar a reunião.

Parada da isolada: `.\stop-mvp-demo.ps1 -LedgerPath (Join-Path $PWD '.mvp-logs\owned-run-cor016.json')`.

## Visual e ditado

Não há browser interativo (MCP) nesta sessão. HTTP 200 e Vitest **não** substituem inspeção humana.

| Viewport / gesto | Resultado |
|---|---|
| 1440×900 | **NÃO VERIFICADO** |
| 768×1024 | **NÃO VERIFICADO** |
| 390×844 | **NÃO VERIFICADO** |
| 320×568 | **NÃO VERIFICADO** |
| Zoom 200% | **NÃO VERIFICADO** |
| Teclado / foco | **NÃO VERIFICADO** |
| Impressão | **NÃO VERIFICADO** |
| Ditado: permissão negada / sem suporte | **NÃO VERIFICADO** em navegador real. jsdom: fallback “indisponível”; copy: o SegSense não recebe nem grava áudio; **não** afirma processamento local do navegador |
| Cenários A/B na UI | **NÃO VERIFICADO** visualmente; HTTP A/B **COMPROVADO** |

Pedido à auditoria humana: abrir a **URL nova ativa** e seguir `SEGSENSE_DEMO_RUN_001` v1.9 (primeira dobra: Fonte ou relato → Elementos → Intenção confirmada → envio; depois Possibilidades ilustrativas → Por que surgiram → O que ainda depende de corretora/seguradora).

## Gates

| Gate | Resultado |
|---|---|
| Frontend Vitest | **74/74** |
| Frontend eslint + `tsc -b` + `vite build` | ok |
| Mock `node --test` | **8/8** (inclui pertinência declarado vs governado) |
| Spider `SatelliteContractV1Test` + schema 1.1 | ok; exemplo 1.1 falha no schema 1.0 |
| SegSense `mvnw verify` | Flyway V1–**V15** em Testcontainers **vazio** (sem V16). Primeira passagem nesta sessão falhou por env da stack isolada (`SEGSENSE_PUBLIC_BASE_URL=:15178`) em `ContextLinkIT`/`SegSenseApplicationIT`; reexecução com essas variáveis nulas: **exit 0**. Não é regressão de produto |
| Volume isolado existente | Reutilizado `segsense_pgdata_isolated_cor016`; BFF subiu; **sem** migration nova nesta etapa |
| `prove-isolated-prm017.ps1` | **COMPROVADO** (`isolatedHttpProof=COMPROVADO`). Stack **deixada no ar**. Reunião inalterada |
| Preflight isolado | `preflight=ok mock=TEST_DOUBLE spider=SATELLITE_CONTRACT_V1 segsense=SEGSENSE` |
| Segredos em logs/chat | Não impressos |
| Commit / push / deploy | **Não** executados |
| Working tree Spider Experience Hub / screenshots | **Alheio**; não editado neste PRM |

## Implementado vs mock vs seguradora

| Camada | Evidência |
|---|---|
| Implementado | Entrada texto/ditado/link; contribuições 1.1; timestamps honestos; intenção `USER_DECLARED`; Spider escolhe capability; UI de causalidade (código); stack isolada no ar |
| Mock sintético | Itens `ILLUSTRATIVE_POSSIBILITY` / `ILLUSTRATIVE_NOT_ICATU_CONTRACT` segundo o `scenarioKey` recebido |
| Dependente de seguradora autorizada | Cotação, proposta, produto Icatu, elegibilidade, URL pública arbitrária, vida real do visitante |

## Limites regulatórios (DEMO ONLY)

- URL governada **não** prova a vida do visitante.
- Ditado **não** é consentimento nem intenção.
- Sem Icatu, R$, cobertura, apólice, produto novo ou composição automática.
- Watermark e Test Double permanecem.
- Sem chamada SegSense → mock.
- Sem áudio/PII/narrativa bruta no envelope ao provider.

## Alterações por aplicação

| Aplicação | O que mudou neste PRM |
|---|---|
| SegSense | Envelope 1.1 (`DemoSatelliteEnvelopeFactory`); assemble de contribuições; fingerprint v2; UI Fonte/Elementos/Intenção; painel distingue tempos e origens; `prove-isolated-prm017.ps1` |
| Spider | Schemas/exemplos **1.1**; parser/validação versionada; `declared-context-ids`; `DemoSliceRules` considera contribuições; V1 intacto |
| Insurance Provider Mock | Alias de `SEGSENSE_DECLARED_*`; pertinência “tema declarado estruturado” vs fonte editorial |

## Git

Sem commit. Diff relevante em `segsense/`, `spider/backend` (núcleo satélite + `contracts/satellite/1.1/`), `segsense-provider-mock/`, docs `SEGSENSE_*`, `.cursor/rules/ecosystem-focus.mdc`. Schemas `1.0/` sem diff. Experience Hub da Spider permanece dirty e **fora** deste escopo.

## Veredito

PRM_017 **executado** para auditoria. HTTP da versão nova **COMPROVADO**. URL nova **ativa**. Visual/ditado real **NÃO VERIFICADO**. Não autoaprovado. Sem PRM_018.

## COR_001 — aceite visual e linguagem humana

Único corretivo permitido. Não autoaprovado. Sem PRM_018. Sem segundo corretivo.

### Causa CSS

A regra global `form input { width: 100%; min-height: 2.5rem; padding: … }` em `index.css` aplica-se a radios e checkboxes. `form label { display: block }` coloca o controle numa linha própria. Na rota `/demonstracao/mvp-integrado` isso abria vazios enormes entre o controle e a frase. A correção é **local** a `.mvp-page`: `input[type=radio|checkbox]` com `width/height: 1.125rem`, `flex: none`, labels `.mvp-choice` em flex, alvo ≥44 px. Admin e `/c/{token}` não usam essas classes.

### Frases antes / depois

| Superfície | Antes | Depois |
|---|---|---|
| Navegação | “Apresentação SegSense” / aria “voltar à apresentação pública” | **Voltar à apresentação** (`/`) |
| CTA | Enviar ao SegSense | **Ver possibilidades ilustrativas** |
| Espera | aguardando resposta do SegSense | Solicitação enviada; aguardando o resultado desta tentativa |
| `explanation` (Spider) | `tema family_continuity` + `UNDERSTAND_PROTECTION_OPTIONS` + capability + `scenarioKey` | “A Spider aplicou regras explícitas ao contexto de continuidade familiar e à intenção de entender opções ilustrativas de proteção. O resultado permite encaminhar o pedido ao Test Double. Considerados: fonte editorial / relato declarado. Sem composição de seguro real.” |
| Público pós-resposta | `ILLUSTRATIVE_NOT_ICATU_CONTRACT` visível | Test Double; não é contrato Icatu. O código permanece em `details` |

### Visual COR_001

Chrome real (headless, canal `chrome`) na URL nova. Antes: controles da intenção desalinhados (captura alta 1440). Depois: capturas por viewport + dois fluxos. Teclado/foco e impressão: **NÃO VERIFICADO** de forma interativa nesta sessão (sem MCP de browser); o patrocinador deve conferir na URL ativa. Ditado real: **NÃO VERIFICADO**.

### Gates COR_001

| Gate | Resultado |
|---|---|
| Frontend Vitest | **74/74** |
| Frontend eslint + `tsc -b` | ok |
| Spider `SatelliteContractV1Test` | ok; `explanation` humana sem enums |
| Envelope 1.1 / contribuições / timestamps | Preservados |
| SegSense `mvnw verify` | exit 0; Flyway V1–V15 em Testcontainers vazio |
| Mock `node --test` | **8/8** |
| `prove-isolated-prm017.ps1` após restart pelo ledger | **COMPROVADO**. URL nova deixada no ar. Reunião inalterada (pids 10688 / 54468 / 20736 / 47472 / 42872) |
| Commit / push / deploy | Não executados |

Capturas: `segsense/documents/evidencias/SEGSENSE_PRM_017_COR_001/`.

