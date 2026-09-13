# SEGSENSE_DEMO_CONTRACT_001 — Contrato mínimo de demonstração SegSense ↔ Spider

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_DEMO_CONTRACT_001 |
| Versão | segsense-demo-contract-v1 |
| Data | 13/09/2026 |
| Natureza | Anti-corrupção **deprecated**. O caminho canônico é `SPIDER-SAT-003`. |

## Operação

`POST /v1/satellites/interactions` (canônico, SPIDER-SAT-003). A fatia `POST /v1/demo/segsense/protection-decisions` permanece como anti-corrupção deprecated.

Somente profile Spring `local-demo` e `spider.demo.segsense.enabled=true`. Bind efetivo da fatia: loopback. Pedido fora de loopback → 403.

### Autenticação

A identidade **não** é o segredo.

| Item | Valor |
|---|---|
| Identidade pública | `applicationId=SEGSENSE` no corpo; header `X-Spider-Credential-Ref: local-demo-segsense` |
| Segredo | header `X-SEGSENSE-Demo-Application-Secret`, valor **somente** em variável local não versionada `SPIDER_SEGSENSE_DEMO_APPLICATION_SECRET` |
| Visitante | Não autenticado na Spider |
| Sem identidade, sem segredo, identidade errada ou segredo errado | 401, sem detalhe interno |
| Segredo ausente no runtime | fail-closed (401). Não há default versionado |
| Esta identidade **não** autentica `/v1/canonical/**` nem `/v1/context/**` | |

Não registrar o valor do segredo em log, script versionado, documentação ou Git. Rotação: `segsense/scripts/setup-mvp-demo-secrets.ps1`.

### Correlação e idempotência

- `X-Correlation-ID`: UUID
- `Idempotency-Key`: UUID; mesma chave + mesmo fingerprint → mesma `decisionId`; fingerprint diferente (objetivo **ou** `originSnapshot`) → 409
- O fingerprint inclui contrato, aplicação, cenário, objetivo e os campos do `originSnapshot`
- Timeout Spider→mock: 3s; SegSense→Spider: 5s

### `originSnapshot` (obrigatório)

Tipado, versionado, **não pessoal**. O SegSense obtém os valores do registro governado do cenário (`GovernedDemoOrigin`), não do navegador, URL, `Referer` ou token.

```json
{
  "schemaVersion": "origin-snapshot-v1",
  "channel": "SEGSENSE_PUBLIC_DEMO",
  "editorialPieceKey": "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1",
  "editorialPieceVersion": "demo-editorial-v1",
  "purposeVersion": "demo-purpose-v1",
  "purpose": "Apresentar jornada ilustrativa de proteção familiar, sem cotação.",
  "capturedAt": "2026-09-13T12:00:00Z",
  "nonPersonal": true
}
```

A Spider valida versão, canal, peça, finalidade, instante e `nonPersonal=true`. Ausente/inválido → 400 **antes** do mock. A regra é determinística e pequena: não personaliza seguro real.

### Request (máx. 8 KiB)

Além do snapshot: `contractVersion`, `applicationId`, `scenarioKey`, `declaredObjective`.

Não enviar token de link, credencial de instância, notice, CPF, nome, e-mail, telefone, renda ou saúde.

### Objetivos

| Código | Decisão Spider |
|---|---|
| `UNDERSTAND_FAMILY_PROTECTION_OPTIONS` | Permitido, **depois** da validação de contexto → chama mock |
| Qualquer outro | `REJECTED` (contexto válido; sem chamada ao mock) |

### Response

IDs **somente** dos subsistemas realmente executados: `decisionId` e, se o mock respondeu, `mock.resultId`. Sem `planId`/`executionId`.

`originProvenance` ecoa o snapshot validado. `spiderPath=VALIDATED_SYNTHETIC_CONTEXT_THEN_ILLUSTRATIVE_PROVIDER`. `decisionProvenance=SPIDER_DETERMINISTIC_DEMO`. Sem segredo.

Estados: `PRE_PROPOSAL_READY`, `REJECTED`, `MOCK_UNAVAILABLE`.

### Erros

| HTTP | code | Quando |
|---|---|---|
| 401 | AUTHENTICATION_REQUIRED | Sem identidade/segredo válidos |
| 403 | ACCESS_DENIED | Origem de rede não loopback |
| 400 | VALIDATION_ERROR | Payload/contexto inválido |
| 409 | IDEMPOTENCY_CONFLICT | Mesma chave, fingerprint diferente |
| 200 | status MOCK_UNAVAILABLE | Mock caiu/timeout |

## O que este contrato não é

Não implementa os 16 itens de `SEGSENSE_REQ_002`. Não é preview/confirmação canônica. Não altera Contextual Link, SpiderBank nem a governança de seguro real. O mock **não** recebe `originSnapshot`.
