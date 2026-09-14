# SEGSENSE_ADR_006 — Proveniência fiel e versão contratual 1.1 (DEMO ONLY)

## Controle

- Projeto: SegSense
- Categoria: decisão arquitetural
- Versão: 1.0
- Data: 14/09/2026
- Estado: vigente nesta etapa; **não** autoaprovada
- Relacionados: `SEGSENSE_ADR_005`, `SPIDER-SAT-003`, `SEGSENSE_PRM_017`

## Decisão

1. O identificador `SEGSENSE_PRM_017` deixa de designar hardening amplo nesta execução. A etapa fecha **fidelidade de proveniência** e **experiência demonstrável**. Segurança/conformidade completa **permanece adiada** (`SEGSENSE_PLN_001`). Sem renumeração silenciosa: o trabalho original de hardening **não** passou a ser o PRM_018.
2. O Satellite Contract **1.0 permanece intacto** (schemas em `contracts/satellite/1.0/`, clientes EXPERIENCE existentes, rota legado SegSense). A jornada pública nova envia **`contractVersion: 1.1`**.
3. Não se sobrecarrega `SATELLITE_GOVERNED` para texto/ditado do visitante. Texto mapeado no SegSense viaja como contribuição `USER_DECLARED`. URL governada viaja como contribuição `SATELLITE_GOVERNED`. Combinação = duas contribuições identificáveis.
4. `message.createdAt` e `objective.declaredAt` são instantes UTC da interação corrente. `sourceTimestamp` editorial é o timestamp imutável da publicação no registro. Os três não compartilham `GovernedDemoOrigin.CAPTURED_AT`.

## Por que V1 não basta

O schema `1.0` tem `additionalProperties: false` e **uma** provenance no snapshot. A política EXPERIENCE 1.0 só aceita `SATELLITE_GOVERNED` + `GOVERNED` + `SERVER_REGISTRY` + `governed-context-ids`. Atribuir o relato a `family()`/`interrupcao-renda` com `sourceType=SATELLITE_GOVERNED` faz a UI sugerir que a Spider processou a fonte editorial quando o BFF só reconheceu palavras-chave. Isso falha o gate de proveniência do PRM_017.

## Versão 1.1 (compatível, DEMO ONLY)

| Artefato | 1.0 | 1.1 |
|---|---|---|
| Path de schema | `contracts/satellite/1.0/` | `contracts/satellite/1.1/` (novo) |
| `contractVersion` | const `1.0` | const `1.1` |
| Snapshot `schemaVersion` | const `1.0` | const `1.1` |
| `contributions[]` | ausente | obrigatório, 1–4 |
| Headline `provenance` | única fonte do snapshot | eco da contribuição principal; não mistura origens |
| Clientes 1.0 | inalterados | recusados pelo schema 1.1; aceitos pela Spider se `contractVersion=1.0` |
| Rota legado SegSense | envelope 1.0 governado | inalterada |

A Spider aceita **1.0 e 1.1**. Validação de schema é versionada. Resposta ecoa a versão do pedido.

## Matriz campo da UI → captura → estruturação → envelope → decisão Spider → provider → resposta

Documentada **antes** da edição de código desta etapa. Colunas: o que o visitante vê; o que é capturado; o que o SegSense estrutura; o que atravessa o envelope; o que a Spider decide; o que o Test Double devolve; o que a UI pode afirmar.

| Campo / gesto na UI | Captura | Estruturação no SegSense | Envelope (1.1 público / 1.0 legado) | Decisão Spider | Provider (Test Double) | Resposta / o que a UI pode dizer |
|---|---|---|---|---|---|---|
| Textarea “Descreva o contexto” | Texto visível; ditado só vira texto após revisão | Parser limitado: tema `family_continuity` / `income_interruption` / conflito / vazio. **Não** envia narrativa bruta, áudio nem PII | Contribuição `VISITOR_DECLARED` + `sourceType=USER_DECLARED` + `sourceId` `SEGSENSE_DECLARED_*` + `elements.theme` somente o que foi mapeado | Valida contribuição declarada contra `declared-context-ids`; aplica allowlist ao tema estruturado **e** à intenção | Não interpreta URL nem texto; recebe só `scenarioKey` | “Relato mapeado no SegSense”; **não** “a Spider interpretou o texto original” |
| Ditado | Transcrição editável no mesmo campo | Igual ao texto, depois da edição humana | Idem `USER_DECLARED` | Não recebe áudio | Não recebe áudio | Só: o SegSense não recebe/grava áudio. Sem afirmação de processamento local do navegador |
| URL governada | Path allowlist; resolve no registro; sem fetch da URL | Snapshot editorial do registry (`theme/situation/need/horizon/constraint`) | Contribuição `GOVERNED_SOURCE` + `SATELLITE_GOVERNED` + `sourceId` sintético + `sourceTimestamp` = `capturedAt` do registro | Valida contra `governed-context-ids` | `scenarioKey` do `sourceId` governado (\| objetivo no público) | “Fonte editorial governada”; URL **não** prova a vida real |
| URL + relato mesmo tema | Duas capturas | Duas contribuições; `selectedContribution=BOTH` | Headline `USER_DECLARED` (o visitante participou) + contribuições governada e declarada, ambas `used=true` | Considera as duas; `scenarioKey` do id governado (caso de registro) + intenção | Itens do cenário governado\|intenção | Mostrar as duas origens; pertinência só se vier do provider/Spider |
| URL + relato temas distintos, sem escolha | Conflito visível | `AMBIGUOUS` local; **não** chama Spider | Não enviado | — | — | Conflito; nada sobrescrito; sem possibilidades |
| URL + relato distintos, escolha “usar a fonte” | Escolha humana | Ambas contribuições; declarada `used=false`; `selectedContribution=GOVERNED_SOURCE` | Headline `SATELLITE_GOVERNED`; contribuição declarada marcada não usada | Usa tema da fonte; explica o que não usou | Cenário da fonte | Não atribuir o relato não usado à decisão |
| Intenção (radios + checkbox) | Confirmação no submit | `objective.origin=USER_DECLARED`; SegSense **não** escolhe capability | `objective.text` allowlist; `declaredAt` = instante UTC da confirmação efetiva (submit com `intentionConfirmed=true`) | Valida objetivo; escolhe capability; despacha ou recusa | Só é chamado se READY | Intenção confirmada pelo visitante; capability/provider = Spider |
| `Enviar ao SegSense` | POST BFF | Fingerprint canônico **sem** timestamps voláteis e **sem** relato bruto | `createdAt` = criação da mensagem efetiva (UTC) | Idempotência sem `createdAt`/`declaredAt` | — | Não fabricar precisão além do instante capturado |
| Timestamp editorial na UI | — | Registry `capturedAt` | `contribution.sourceTimestamp` da contribuição governada | Eco em `originProvenance` | Não usa o instante da interação | Rotulado “publicação da fonte”, separado de `createdAt`/`declaredAt` |
| Possibilidades | — | — | — | Capability `BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO` | Itens ilustrativos + `pertinence` ligados ao `scenarioKey` recebido | Só itens da resposta; sem array local; sem Icatu/R$ |
| Por que surgiram | — | — | — | `explanation` de allowlist + contribuições consideradas/não usadas | `pertinence`/`limits` do item | Eco; se o contrato não trouxer o dado, a UI omite |
| O que depende de corretora | — | — | — | — | `pendingForHumanReview` | Eco; watermark e Test Double visíveis |
| Sequência técnica | — | — | IDs reais | Eventos `SATELLITE_*` / `CAPABILITY_DISPATCHED` | `providerRequestId` | Painel técnico; resumo público só com IDs/eventos verdadeiros. Sem fase animada |

### O que cada origem **é** (não misturar)

| Origem | Quem produziu | Quem **não** fez |
|---|---|---|
| Editorial governada | Registro SegSense / peça sintética | Spider não leu o artigo; visitante não “provou” a situação |
| Declarado pelo visitante | Texto/ditado revisado | BFF não é a Spider; parser de palavras-chave ≠ interpretação semântica |
| Mapeamento determinístico SegSense | Palavras-chave → tema do esquema limitado | Não é decisão de capability/provider |
| Decisão Spider | Allowlist, capability, despacho ou recusa | Não escolhe a intenção; não interpreta URL bruta |
| Test Double | Possibilidades ilustrativas do `scenarioKey` | Não escolhe intenção; não interpreta URL |

## Timestamps (UTC)

| Campo | Semântica | Fonte honesta | Proibido |
|---|---|---|---|
| `message.createdAt` | Criação da mensagem efetiva | `Instant.now(UTC)` no submit que monta o envelope | Fixture `CAPTURED_AT` |
| `objective.declaredAt` | Confirmação da intenção efetiva | Mesmo submit com `intentionConfirmed=true` (é o clique de confirmação persistido) | Usar o instante editorial |
| `sourceTimestamp` editorial | Publicação imutável da fonte | `GovernedDemoSource.capturedAt` | Instantes da interação |
| `sourceTimestamp` declarado | Momento em que os elementos estruturados foram enviados | Igual a `createdAt` desta mensagem (não há captura anterior persistida) | Fingir um horário de digitação não medido |

Se um detalhe não foi capturado, a UI **omite**. Não fabrica precisão.

## Reprogramação do plano (sem silêncio)

| Identificador | Antes (PLN 1.21) | Nesta execução |
|---|---|---|
| PRM_016 | Jornada contextual; COR_001 | Encerrado aprovado com ressalvas |
| PRM_017 | Segurança e conformidade | Proveniência fiel + demo visual; hardening **adiado** |
| PRM_018 | Testes ponta a ponta e piloto | Permanece o identificador de E2E/piloto; **não** iniciado |
| Indicadores (ex-016) | Adiados | Continuam adiados |
| Hardening (ex-017) | Era o PRM_017 | Adiado; não virou PRM_018 |

## O que isto não autoriza

- Alterar bytes dos schemas `1.0` para clientes existentes.
- URL pública arbitrária, SSRF, PII, áudio, Icatu, cotação, apólice, IA.
- Chamada SegSense → mock.
- Commit, push, deploy, parada da reunião sem ledger, apagar volumes.
- Autoaprovação ou início do PRM_018.

## Consequência operacional

A prova e a auditoria visual usam a **stack isolada** (`:15178` frontend, `:19088` BFF, `:19080` Spider, `:19095` mock, Postgres `:15437` volume `segsense_pgdata_isolated_cor016`). A reunião `:5178/:8088/:8080/:8095` permanece código antigo se ainda no ar e **não** é anunciada como jornada nova.
