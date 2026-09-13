# SPIDER-SAT-003 — Satellite Contract V1

| Campo | Valor |
|---|---|
| Identificador | SPIDER-SAT-003 |
| Documento | SPIDER-SATELLITE-CONTRACT-V1 |
| Natureza | Contrato canônico IMPLEMENTADO (local-demo) |
| Boundary | SIMULATED_INFRASTRUCTURE / MOCK_ONLY |
| Predecessor | SEGSENSE_PRM_013_COR_001 |
| Estado | IMPLEMENTADO / DEMO ONLY |

Este documento **é** o Satellite Contract V1 da plataforma Spider. Não é uma API do SegSense. Não criar `SPIDER-ARCH-018`: ARCH-017 permanece a arquitetura de referência de satélites e aponta para este contrato.

## 1. Missão

O contrato descreve **como uma aplicação participa do ecossistema Spider**, não como um produto chama um endpoint próprio.

```text
SATELLITE
  ↓
SATELLITE CONTRACT V1
  ↓
SPIDER CONTROL PLANE
  ↓
Capability Resolution
  ↓
PROVIDER CONTRACT
  ↓
EXECUTOR (TEST DOUBLE ou provider futuro)
```

## 2. Papéis (V1)

| Papel | Responsabilidade | Não faz |
|---|---|---|
| EXPERIENCE | objetivo, contexto governado, finalidade, apresentação | escolher provider, route, adapter |
| PROVIDER | executar capability delegada | conhecer a jornada |

Papéis futuros (OPERATIONAL, DATA_PROVIDER, HUMAN_WORKFLOW) não são implementados.

## 3. Endpoint canônico

`POST /v1/satellites/interactions`

Profile `local-demo`. Sem “segsense” no path.

Identidade: `X-Spider-Satellite-Id` (não é segredo).
Credencial: `X-Spider-Satellite-Secret` (env local, não versionado).
Loopback é **controle de ambiente**, não regra do contrato.

A fatia `POST /v1/demo/segsense/protection-decisions` permanece **deprecated** e traduz internamente para este contrato (uma só lógica de decisão).

## 4. Envelope

`contractVersion: "1.0"` viaja no payload. Não inferir versão pelo URL.

Campos: messageId, correlationId, satelliteId, satelliteRole, interactionType, createdAt, idempotencyKey, purpose, objective, context (contextRef ou snapshot), dataClassification, responseChannel=SYNC, metadata pequena.

**Não** viajam: intent, provider, route, adapter, mock, icatuProductId, segsenseCampaignType, PII, segredo.

Schemas: `backend/src/main/resources/contracts/satellite/1.0/`.

## 5. Context / Provenance

Experience deve enviar `SATELLITE_GOVERNED` + `trustLevel=GOVERNED` + `captureMethod=SERVER_REGISTRY`.
Não aceitar PAGE_CONTEXT nem DIRECT_ENTRY como prova governada.
`contextRef` (`ctx-…`) evita retransmitir o snapshot.

Aprendizado do COR_001: contexto vem de registro governado no servidor, não do DOM.

## 6. Objective vs Intent

O satélite declara `objective`. O Intent Contract continua responsabilidade da Spider. V1 não inicia CTX-004 nem um interpretador específico de produto.

## 7. Provider Contract

Outbound da Spider:

`POST {providerBaseUrl}/v1/provider/capabilities/{capabilityId}/executions`

Inputs mínimos: scenarioKey derivado do `sourceId`. Sem originSnapshot, objective original, Intent ou Execution Plan.

V1 registra `insurance-provider-mock` como **TEST DOUBLE**, capabilities:

- BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO (usada)
- GET_INSURANCE_OPTIONS (declarada, não despachada neste incremento)

Icatu: NOT_IMPLEMENTED. ServiceNow: fora. CAP-021: não iniciado.

## 8. Idempotência

Mesma chave + mesmo fingerprint semântico → mesma decisionId.
Mesma chave + fingerprint diferente → 409 IDEMPOTENCY_CONFLICT.
Fingerprint não inclui segredo nem timestamp volátil.

## 9. Erros

UNAUTHENTICATED, UNAUTHORIZED_SATELLITE, INVALID_CONTRACT_VERSION, INVALID_PAYLOAD, MISSING_CONTEXT, AMBIGUOUS_OBJECTIVE, IDEMPOTENCY_CONFLICT, CAPABILITY_NOT_AVAILABLE, PROVIDER_UNAVAILABLE, POLICY_REJECTED.

## 10. Diagrama

```text
SEGSENSE (Experience Satellite)
        ↓  Satellite Contract V1
SPIDER  (objetivo + contexto → policy → capability)
        ↓  Provider Contract
Insurance Provider Mock (TEST DOUBLE / ILLUSTRATIVE / NOT ICATU)
        ↓
SPIDER
        ↓
SEGSENSE (pré-proposta demonstrativa)
```

## 11. Substituição

Trocar o Test Double por um provider real autorizado **não** exige alterar a UI nem a semântica do BFF SegSense. Exige registro, adapter e contract tests do provider.
