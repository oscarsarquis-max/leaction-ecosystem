# SEGSENSE_JRN_EVID_001 — Evidência de estados da jornada MVP

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_JRN_EVID_001 |
| Data | 13/09/2026 |
| Rota | `/demonstracao/mvp-integrado` |
| Contrato | Consumo de `SPIDER-SAT-003` (DEMO ONLY). Não é contrato concorrente. |

Regra: texto apresentado como **ocorrência** exige fonte observável. Expectativa e configuração usam outro registro.

## Matriz

| Texto / estado da UI | Fato técnico | Fonte | Timestamp / ID | Condição de exibição |
|---|---|---|---|---|
| Watermark `DEMONSTRAÇÃO — SEM VALOR COMERCIAL — …` | Configuração da peça demonstrativa | Constante local SegSense + eco `watermark` da resposta V1 | — | Sempre visível na rota e na impressão |
| Badge `MVP integrado sintético` | Nome da **configuração** local | Copy da página | — | Sempre; não afirma que uma chamada já ocorreu |
| `ainda não houve envio nesta página` | Nenhum POST do browser nesta sessão | Estado React `phase=form` | — | Só antes do submit |
| Objetivo “entender opções ilustrativas…” | Objetivo sintético escolhido nesta reunião | Formulário local; valor enviado = `UNDERSTAND_FAMILY_PROTECTION_OPTIONS` | — | Copy do formulário (dado sintético nomeado) |
| Checkbox de confirmação | Ação local do visitante | Checkbox React | instante do clique | Obrigatório para habilitar o envio |
| `Enviar à Spider` | Intenção de POST ao BFF | Submit do formulário | — | Botão; desabilitado em `awaiting` |
| `Aguardando resposta da Spider…` | Request HTTP do browser ainda pendente | `fetch` sem resposta | início do POST local | Somente enquanto `phase=awaiting`. **Não** afirma que a Spider recebeu ou analisa |
| `Pré-proposta demonstrativa` | BFF persistiu projeção `PRE_PROPOSAL_AVAILABLE` | `POST /api/v1/public/demo/protection-journeys` → resposta persistida | `id`, `generatedAt` | Só se `decisionId` e `mockResultId` (`providerReference`) vierem na resposta canônica |
| Contexto `SEGSENSE_PUBLIC_DEMO` / `SATELLITE_GOVERNED` | Provenance ecoada pela Spider | `originProvenance` da resposta V1 (schema interaction-response) | `sourceTimestamp` da evidência | Só se o campo existir na resposta; sem fallback local |
| Explicação da Spider | Campo `explanation` da resposta V1 | Spider `SatelliteInteractionService` | `decisionId` | Só após 200 canônico persistido |
| Itens ilustrativos | Resultado da capability | `resultSummary.items` + `providerReference` | `mockResultId` | Só com `providerReference` confirmado |
| Pendências humanas | `pendingForHumanReview` do Test Double | `resultSummary` | `providerReference` | Só com retorno de provedor confirmado |
| `Decisão Spider` | `decisionId` | Envelope de resposta V1 | `spd-…` | Detalhes técnicos; só se o campo existir |
| `Referência do provedor` | `resultSummary.providerReference` | Provider Contract result | `ill-…` | Só se confirmado |
| `Capability despachada` | `capabilityId` | Resposta V1 | `BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO` | Só após READY confirmado |
| `Pedido ao provedor` | `providerRequestId` | Resposta V1 | `preq-…` | Só após READY confirmado |
| Satélite `segsense · EXPERIENCE · contrato 1.0` | Identidade e versão usadas neste envio | Projeção BFF após 200 (`satelliteId`, `satelliteRole`, `contractVersion`) | `correlationId` | Só se os três campos existirem na projeção |
| `Spider indisponível` | BFF não obteve HTTP 200 canônico | Timeout/rede/status ≠ 200 | `correlationId` local | Alert; **sem** pré-proposta |
| `Provedor ilustrativo indisponível` | Spider devolveu `PROVIDER_UNAVAILABLE` | Resposta V1 | `decisionId` se houver | Alert; **sem** itens |
| `Objetivo não permitido` | Spider recusou objetivo (`REJECTED`) | Resposta V1 | `decisionId` | Alert; mock não despachado |
| `A resposta da Spider não confirmou decisão e retorno de provedor` | Envelope 200 sem `decisionId`+`providerReference` | `CanonicalJourneyMapper` | `correlationId` | Alert; **sem** pré-proposta |
| Erro de validação / 409 | Envelope rejeitado pela Spider | HTTP 400/409 | — | Alert do BFF; sem pré-proposta |

## O que a UI **não** mostra como fato

| Ausência | Motivo |
|---|---|
| `Em análise na Spider` após 400 ms | Não há evento intermediário no V1 (resposta síncrona única). Timer removido. |
| Barra de progresso em fases | V1 não emite eventos de jornada ao usuário |
| `capabilityId` / `decisionId` / itens a partir de default do frontend | Proibidos; só da projeção persistida |
| Preview, confirmação, callback, Intent Contract, Eligibility Gate | Não existem no V1 local-demo (`SEGSENSE_REQ_002`) |
| Chamada ao mock pelo SegSense | SegSense não chama o mock |
| Chamada à fatia `/v1/demo/segsense/**` | Deprecated; BFF usa `/v1/satellites/interactions` |

## Home `/` e `/demonstracao/icatu`

| Superfície | Registro |
|---|---|
| Home | Posicionamento. Informa que o V1 existe em local-demo e que **esta página não dispara** a chamada. |
| Icatu | Editorial local. Badges: capacidade existente (manifestação local), **esta página não chama a Spider**, hipótese futura de provider autorizado. Diagrama: Spider/mock “não usada(o) aqui”. |
