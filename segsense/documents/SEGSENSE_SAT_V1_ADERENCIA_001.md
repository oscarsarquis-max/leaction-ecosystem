# SEGSENSE_SAT_V1_ADERENCIA_001 — Matriz de consumo do Satellite Contract V1

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_SAT_V1_ADERENCIA_001 |
| Data | 13/09/2026 |
| Natureza | Matriz de **consumo**. Não é contrato concorrente. |
| Fonte oficial | `SPIDER-SAT-003` / `spider/docs/architecture/SPIDER-SATELLITE-CONTRACT-V1.md` |
| Schemas | `spider/backend/src/main/resources/contracts/satellite/1.0/` |

## Fronteiras

```text
Browser  ↔  SegSense BFF (EXPERIENCE)
                ↓ POST /v1/satellites/interactions
              Spider (registry + policy + capability resolution)
                ↓ POST /v1/provider/capabilities/{capabilityId}/executions
              Insurance Provider Mock (TEST DOUBLE)
```

SegSense **não** chama o mock. O Core Spider **não** importa tipos SegSense. A fatia `/v1/demo/segsense/**` é deprecated e **não** é chamada pelo SegSense.

## Identificadores

`correlationId` → `decisionId` → `capabilityId` → `providerRequestId` → `providerReference`

`planId` e `executionId` **ausentes** (não há Data Plane nesta fatia; não inventar).

## Campos usados pelo BFF / UI

| Campo | Schema / artefato | Origem real | Classificação | Destinatário | Autorização | Exibição |
|---|---|---|---|---|---|---|
| `contractVersion=1.0` | interaction-request/response `const: 1.0` | Envelope V1 | INTERNAL | Spider; eco à UI | Registry `contractVersions` do ambiente demo | Detalhes técnicos se presente |
| `satelliteId=segsense` | request `pattern` + header `X-Spider-Satellite-Id` | Registry `spider.satellite.registry.segsense` | INTERNAL | Spider valida ≠ header | Role EXPERIENCE no YAML | Após 200, se a projeção tiver o trio identidade/papel/versão |
| `satelliteRole=EXPERIENCE` | enum request | Registry | INTERNAL | Spider ignora spoof do body se header não bater | `requireExperience` | Idem |
| `interactionType=REQUEST_DECISION` | enum request | BFF | INTERNAL | Spider | Allowlist do satélite | Não exibido como etapa |
| `purpose=INSURANCE_PROTECTION_ASSESSMENT` | enum request | BFF | INTERNAL | Spider | Allowlist de purposes | Não exibido como código |
| `objective.text` | request.objective | Formulário sintético via BFF | INTERNAL | Spider (não é Intent) | `allowed-objectives` | Texto humano na pré-proposta |
| `context.snapshot` | request contextSnapshot | `GovernedDemoOrigin` no servidor SegSense | INTERNAL / nonPersonal | Spider | `governed-context-ids` + attributes | Canal só se ecoado em `originProvenance` |
| `provenance.sourceType=SATELLITE_GOVERNED` | provenance def | BFF | INTERNAL | Spider | Rejeita PAGE_CONTEXT/DIRECT_ENTRY | Se ecoado |
| `idempotencyKey` | request + header | Browser UUID | INTERNAL | Spider + BFF | 409 se fingerprint divergir | Não exibido |
| `correlationId` | request + header | Browser / BFF | INTERNAL | Toda a cadeia | — | Detalhes técnicos |
| `dataClassification=INTERNAL` | enum | BFF | INTERNAL | Spider | Allowlist do satélite | Não exibido |
| `responseChannel=SYNC` | enum só SYNC | BFF | INTERNAL | Spider | V1 sem callback | UI espera uma resposta final |
| `status=READY` | response enum | Spider após capability | INTERNAL | BFF mapeia para `PRE_PROPOSAL_AVAILABLE` só com IDs | Policy não contornada | Pré-proposta só se confirmado |
| `decisionId` | response | Spider | INTERNAL | UI | — | Só se presente |
| `resultSummary.providerReference` | result schema | Mock | INTERNAL / ILLUSTRATIVE | UI como `mockResultId` | Capability registrada | Sem isto, nenhum item |
| `capabilityId` | response | Resolver Spider | INTERNAL | UI | Registry provider | Só READY confirmado |
| `providerRequestId` | response | Spider outbound | INTERNAL | UI | — | Só READY confirmado |
| `requiredAction` | response | Spider | INTERNAL | Persistido; UI não desenha fase extra | — | Não vira fase de progresso |
| `originProvenance` | response | Eco do snapshot aceito | INTERNAL | UI | — | Sem default local se omitido |
| Erros `UNAUTHENTICATED` … `POLICY_REJECTED` | error schema | Spider | INTERNAL | BFF | — | Alert humano; sem pré-proposta |

## O que existe no V1 local-demo

IMPLEMENTADO / DEMO ONLY: envelope, registry governado, EXPERIENCE + TEST DOUBLE, `REQUEST_DECISION` síncrono, provenance governada, idempotência, 409, errors canônicos, capability `BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO`.

## O que não existe (REQ_002 permanece parcial)

| Item | Estado |
|---|---|
| Preview sem execução | AUSENTE |
| Confirmação ligada a preview | AUSENTE |
| IdP / OIDC / mTLS de produção | AUSENTE (segredo local ≠ produção) |
| Callback / event bus | AUSENTE (`responseChannel=SYNC` somente) |
| Eligibility Gate completo | NÃO IMPLEMENTADO (campos preparados) |
| Intent Contract pleno / CTX-004 | NÃO INICIADO |
| Data Plane `planId`/`executionId` | AUSENTE |
| Icatu / ServiceNow / CAP-021 | FORA |

SAT-03 = **contrato V1 implementado em demo**. Não é certificação de produção nem encerramento dos 16 requisitos de `SEGSENSE_REQ_002`.

## Substituição futura de provedor

Trocar o Test Double por provider autorizado exige registro, adapter e contract tests **na Spider**. Não altera a semântica do BFF nem a UI SegSense.
