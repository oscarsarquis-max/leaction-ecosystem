# SEGSENSE_JRN_EVID_001 — Evidência de estados da jornada MVP

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_JRN_EVID_001 |
| Versão | 1.8 |
| Data | 14/09/2026 |
| Rota | `/demonstracao/mvp-integrado` |
| Contrato | Consumo de `SPIDER-SAT-003` (DEMO ONLY). Não é contrato concorrente. |
| Ajuste | PRM_019: intenção livre, perguntas e cotação simulada. Radios e checkboxes redundantes saíram da superfície pública. |

Regra: texto apresentado como **ocorrência** exige fonte observável. Expectativa e configuração usam outro registro. Ordem visual de cartões **não** é cronologia auditável. Possibilidade na UI **nunca** vem de array local.

## Matriz

| Frase / cartão | Fato | Fonte exata | Identificador / timestamp disponível | Condição de exibição | Se ausente |
|---|---|---|---|---|---|
| `Voltar à apresentação` | Ação do cliente | `Link` para `/` | — | Cabeçalho da rota nova | — |
| Badge `MVP integrado sintético` | Configuração local | Copy da página | — | Sempre | — |
| `ainda não houve envio nesta página` | Ação do cliente ainda não ocorreu | `phase=form` | — | Só antes do submit | Some após envio |
| `Descreva o contexto` | Ação do cliente | Textarea | texto local até o POST | Sempre no bloco 1 | — |
| `Ditar contexto` / `Ouvindo…` | Ação do cliente | `speechRecognitionCtor` | — | Botão; `unsupported`/`denied` com copy própria | Texto permanece utilizável. O SegSense não recebe/grava áudio. **Não** afirma que o navegador processa localmente |
| `Usar contexto de um link` | Ação do cliente | Input + `POST /context-sources/resolve` | URL de referência técnica | Resolve só fontes governadas; geração aborta resolve anterior | Erro `INVALID_CONTEXT_URL` / `REVOKED_CONTEXT_SOURCE`. Troca A→B ignora `resolved` tardio |
| `A tentativa anterior foi descartada…` | Ação do cliente após READY | Inputs da jornada atual mudaram | nova chave UUID | Relato, URL, fonte, conflito, intenção ou campos de simulação depois de `phase=done` | Resultado anterior some da jornada atual |
| `Cancelar esta tentativa` | Ação do cliente | Abort + serial da request | nova chave | Só em `awaiting` | Resposta tardia da request cancelada é ignorada |
| `Usar contexto de um link` | Ação do cliente | Input + `POST /context-sources/resolve` | URL de referência técnica | Resolve só fontes governadas | Erro `INVALID_CONTEXT_URL` / `REVOKED_CONTEXT_SOURCE` |
| `1. Fonte ou relato` | Ação do cliente | textarea + URL | — | Primeira dobra | — |
| `2. Elementos extraídos ou declarados` | Registro SegSense e/ou parser limitado | Resolve + `declaredThemeFromText` | `sourceId`, versão, `USER_DECLARED` vs `SATELLITE_GOVERNED` | Há texto mapeável e/ou fonte resolvida | “Ainda não há elementos”. **Não** atribui interpretação à Spider |
| `3. Sua intenção` / `O que você quer fazer?` | Ação do cliente | textarea + interpretação local limitada | código classificado no POST | Bloco 3 | Intenção **não** deriva do link. Sem radios técnicos |
| Interpretação “Entendi que você quer…” | Classificação limitada do SegSense | `classifyIntention` / `DemoIntentionClassifier` | código | Há texto | Sem default se não reconhecer |
| `Gerar cotação simulada` | Intenção de POST ao BFF | Submit após revisão | — | Intenção residencial | Frase: simulação ≠ contratação |
| Perguntas (tipo de imóvel, capital, período) | `MISSING_CONTEXT` da Spider ecoado | `missingQuestions` da projeção | códigos `dwelling_type` etc. | Só após resposta Spider/BFF | Não chamar provider |
| Bloco **Cotação simulada** | Resposta confirmada desta tentativa | `simulatedQuote.premiumAnnualCents` **somente** se `SIMULATED_QUOTE_AVAILABLE` + `quoteReference` | `qte-…` | `isConfirmedSimulatedQuote` | Sem R$ antigo, sem fallback |
| `Como este valor foi calculado` | Resultado do mock ecoado | `humanCalculation` / `premises` | `ratingRuleVersion` nos detalhes | Cotação confirmada | Omitido se provider falhou |
| Conflito fonte × relato | Comparação local + persistência `AMBIGUOUS` se enviado sem escolha | `theme` da fonte vs relato | — | Temas diferentes | Nada sobrescrito |
| `Ver possibilidades ilustrativas` | Intenção de POST ao BFF | Submit quando o texto mapeia entender/comparar | — | Botão; desabilitado em `awaiting` | Ainda válido para a jornada ilustrativa |
| `Solicitação enviada; aguardando o resultado desta tentativa…` | Ação do cliente: `fetch` iniciado | `phase=awaiting` | início local do POST | Só enquanto pendente | Some na resposta/erro |
| Bloco **3 Possibilidades** | Resposta BFF confirmada desta tentativa | `items` da projeção **somente** se `PRE_PROPOSAL_AVAILABLE` + `decisionId` + `mockResultId` | `ill-…` | `isConfirmedPreProposal` | “Nenhuma possibilidade ilustrativa nesta tentativa” |
| Título / pertinência / limites de cada possibilidade | Resultado do Test Double ecoado | campos do item; pertinência **não** inventada no FE | `code` | Campo presente no item | Linha omitida |
| Bloco **4 Por que…** | Decisão Spider | `explanation` + `pendingForBroker` | `spd-…` | Projeção presente | Sem reescrita local da explicação |
| `Detalhes técnicos desta tentativa` | Resposta BFF | `details` + painel de evidências | correlação / satélite / chave de idempotência | `phase=done` | Recolhido; não lidera a dobra |
| Tentativa corrente / chave de idempotência | Ação do cliente | UUID gerado no navegador | chave local | No `details` | Nova tentativa gera outra chave |
| `Registrado no SegSense em …` | Resposta BFF | `generatedAt` | ISO do BFF | Só se o campo vier na projeção | Cartão omite a linha |
| Contexto sintético governado | Decisão Spider sobre snapshot | `originProvenance` ecoado | `sourceId`; `sourceTimestamp` editorial = publicação do registro (não o `createdAt` da mensagem) | Só se canal/`sourceType` existirem na projeção | Cartão omitido. **Não** verifica a vida real |
| Relato mapeado no SegSense | Parser limitado + eco 1.1 | contribuição `VISITOR_DECLARED` | `SEGSENSE_DECLARED_*`; `USER_DECLARED` | Há tema mapeado sem fonte, ou combinação | **Não** “a Spider interpretou o texto original” |
| Objetivo enviado | Resposta BFF | `declaredObjective` persistido | — | Campo presente | Cartão omitido |
| Capability despachada | Decisão Spider + despacho confirmado com provedor | `capabilityId` + `providerRequestId` na projeção confirmada | `preq-…` | Pré-proposta confirmada | Ausente em REJECTED / mock down / incompleto / MISSING_CONTEXT / AMBIGUOUS |
| `Fora desta demonstração` | Configuração / lacuna | Nota estática | — | Sempre no `details` desta tentativa | — |
| `Contexto insuficiente` | Validação SegSense e/ou Spider | `MISSING_CONTEXT` | `id` da jornada | Status correspondente | Sem itens |
| `Contexto ou intenção ambíguos` | Validação SegSense e/ou Spider | `AMBIGUOUS` | `id` | Status correspondente | Sem itens |
| `Spider indisponível` | Resposta BFF ou timeout | `SPIDER_UNAVAILABLE` ou `fetch` rejeitado | correlação local | Após erro | Sem cartões da tentativa anterior |
| `Provedor ilustrativo indisponível` | Decisão Spider | `PROVIDER_UNAVAILABLE` → `MOCK_UNAVAILABLE` | `decisionId` se houver | Status correspondente | Sem Test Double |
| `Objetivo não permitido` | Decisão Spider | `REJECTED` | `decisionId` | Status correspondente | Sem capability / itens; mock não chamado |
| `Nova tentativa (nova chave)` | Ação do cliente | Novo UUID; limpa projeção | nova chave | `phase=done` | — |

## Classes de fato

| Classe | Exemplos |
|---|---|
| Configuração | Badge, watermark, nota “Fora desta demonstração”, esquema limitado de tema, lista de intenções sintéticas |
| Ação do cliente | Texto, ditado local, resolve de URL, envio, espera, nova chave, impressão; checkbox só em conflito de contexto |
| Resposta BFF | `id`, `generatedAt`, `declaredObjective`, `status`, persistência, quadro persistido |
| Decisão Spider | `decisionId`, `explanation` de allowlist, `originProvenance` ecoado, eventos operacionais `SATELLITE_*` |
| Resultado do Test Double | `providerReference`, itens `ILLUSTRATIVE_POSSIBILITY`, pertinência, pendências |

## O que a UI **não** mostra como fato

| Ausência | Motivo |
|---|---|
| `Aguardando resposta da Spider…` / `Spider recebeu às…` | O cliente só observa o `fetch` ao BFF |
| Linha do tempo animada / subetapas de `READY` | V1 é resposta síncrona única |
| `planId` / `executionId` | Não existem nesta fatia |
| Array de possibilidades no bundle do frontend | Proibido; higiene e teste de fonte |
| Itens de tentativa anterior após nova tentativa, falha, cancelamento ou edição pós-READY | Estado React zerado; serial/AbortController; nova chave |
| Combinação impressa de entradas atuais com resultado antigo | `@media print` oculta o formulário; resultado some ao editar |
| Chamada SegSense → mock ou `/v1/demo/segsense/**` | Independência + deprecated |
| Artigo integral da fonte | Sem licença; só título, fonte, versão, excerto autorizado |

## Home `/` e `/demonstracao/icatu`

Posicionamento e editorial. Não disparam o V1. Sem jornada contextual canônica.
