# SEGSENSE_FUN_003 — Modelo contexto, intenção e possibilidade ilustrativa

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_FUN_003 |
| Título | Modelo de contexto, intenção declarada e possibilidade ilustrativa (demo local) |
| Categoria | FUN — fundamentos |
| Versão | 1.2 |
| Status | Vigente nesta etapa; não é catálogo comercial |
| Data | 14/09/2026 |

## 1. Separação de camadas

| Camada | O que é | O que não é |
|---|---|---|
| **Implementado** nesta fatia | Entrada de contexto (texto/ditado/link governado), confirmação de intenção, envelope V1, regras explícitas de allowlist na Spider, Test Double com possibilidades sintéticas, UI em quatro blocos | Personalização da vida real do visitante |
| **Mock sintético** | `ILLUSTRATIVE_POSSIBILITY` com título, necessidade, pertinência e limites ligados ao `scenarioKey` | Serviço, produto, cobertura, preço, disponibilidade |
| **Dependente de seguradora autorizada** | Qualquer afirmação de elegibilidade, cotação, proposta, apólice ou catálogo Icatu | Fora desta demonstração |

## 2. Contexto (esquema limitado)

Campos desta demo: **tema**, **situação**, **necessidade**, **horizonte**, **restrição**. Não há inferência ilimitada nem leitura da vida do visitante a partir do artigo.

| Origem | Papel | Proveniência |
|---|---|---|
| Relato escrito ou transcrição editável de ditado | Declaração humana. O SegSense não recebe nem grava arquivo de áudio. A transcrição é revisável no mesmo campo. | `USER_DECLARED` / contribuição `VISITOR_DECLARED`; o texto original **não** atravessa a fronteira |
| Link governado | Fonte editorial. Não é intenção nem prova de enquadramento. | `SATELLITE_GOVERNED` / contribuição `GOVERNED_SOURCE`; `sourceTimestamp` = publicação do registro |
| Combinação URL + relato | Duas contribuições identificáveis | Headline não mistura origens; `selectedContribution` `BOTH` / `GOVERNED_SOURCE` / `VISITOR_DECLARED` |

Fontes sintéticas desta etapa:

| ID | Slug | Tema |
|---|---|---|
| `SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1` | `continuidade-familiar` | `family_continuity` |
| `SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1` | `interrupcao-renda` | `income_interruption` |
| `SEGSENSE_REVOKED_SYNTHETIC_V1` | `revogada` | revogada (resolve 409) |

URL aceita `http://127.0.0.1:{porta}/demonstracao/fontes/{slug}` ou `localhost` no mesmo path, sem query, fragmento, userinfo ou host privado. Porta padrão da reunião: `5178`. A stack isolada COR_001 também aceita `15178` quando configurada em `SEGSENSE_DEMO_GOVERNED_PORTS`. Aquisição de URL pública arbitrária é etapa futura de governança; **não** está anunciada.

O fluxo público **não** escolhe a fonte familiar quando URL e relato estão vazios: o BFF responde `MISSING_CONTEXT` e não chama a Spider. A prova HTTP legada permanece só em `POST /api/v1/public/demo/legacy-protection-journeys` (rotulada, perfis `local`/`test`).

PII óbvia no relato é rejeitada **antes** do fingerprint (`PERSONAL_DATA_NOT_ALLOWED`). O fingerprint SHA-256 (v2) cobre fluxo, intenção, confirmação, escolha, URL, `sourceId`/versão, tema declarado, hash do texto, classificação, `primarySourceType` e papéis das contribuições. **Não** inclui `createdAt`/`declaredAt`. O texto bruto **não** é persistido. Replay da mesma chave exige o mesmo fingerprint; mudança material → 409. Linhas anteriores à V15 (fingerprint nulo) também conflitam (fail-closed).

O fluxo público envia Satellite Contract **1.1**. A rota legado rotulada permanece **1.0** `SATELLITE_GOVERNED`. `message.createdAt` e `objective.declaredAt` são UTC da interação corrente; o timestamp editorial da fonte é rotulado à parte.

Conflito entre fonte e relato é mostrado. Nada é sobrescrito em silêncio. Texto que não mapeia o esquema → `MISSING_CONTEXT`. Ambos os temas no mesmo relato, ou fonte ≠ relato sem escolha → `AMBIGUOUS`.

## 3. Intenção

O SegSense pergunta “O que você quer entender ou fazer?”. A intenção **não** deriva do clique no link. Envio exige confirmação explícita.

| Código | Destino | Efeito observável |
|---|---|---|
| `UNDERSTAND_PROTECTION_OPTIONS` | Spider → Test Double | Possibilidades de “entender opções” no tema escolhido |
| `COMPARE_COVERAGE_GAPS` | Spider → Test Double | Possibilidades de “comparar lacunas” no mesmo tema |
| `REQUEST_BINDING_QUOTE` | Spider recusa (`REJECTED`) | Sem capability, sem chamada ao mock |
| `UNDERSTAND_FAMILY_PROTECTION_OPTIONS` | Somente a rota legado rotulada | `scenarioKey` = só o `sourceId` familiar; não é o fluxo público |

O SegSense estrutura e registra. A Spider decide allowlist, capability e se o provider é acionado.

## 4. Possibilidade ilustrativa

Só existe depois de resposta real com `providerReference`. Marcação: `ILLUSTRATIVE_NOT_ICATU_CONTRACT`, `notOfferable=true`. Pertinência, se existir, vem do Test Double; o frontend **não** inventa motivo.

## 5. Critérios determinísticos da Spider (allowlist)

1. Satélite EXPERIENCE autenticado; finalidade e tipo de interação na lista.
2. Snapshot 1.1: contribuições na allowlist (`governed-context-ids` e/ou `declared-context-ids`). Snapshot 1.0: só `SATELLITE_GOVERNED`.
3. Objetivo na lista permitida; senão `REJECTED` sem provider.
4. `constraint=unresolved_conflict` → `AMBIGUOUS` sem provider.
5. `constraint=missing_context` ou tema ausente → `MISSING_CONTEXT` sem provider.
6. Caso contrário `READY`: capability `BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO`; `scenarioKey` conforme ADR_005.

Isto **não** é IA, atuarial, elegibilidade nem composição de apólice.
