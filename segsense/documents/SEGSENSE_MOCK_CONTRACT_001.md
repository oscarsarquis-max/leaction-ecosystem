# SEGSENSE_MOCK_CONTRACT_001 — Contrato do Insurance Provider Mock

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_MOCK_CONTRACT_001 |
| Versão | segsense-mock-contract-v1 |
| Data | 13/09/2026 |
| Runtime | `segsense-provider-mock/` na raiz do monorepo; porta **8095**; bind **127.0.0.1** |

## Quem chama

**Somente a Spider** (profile `local-demo`). O SegSense não possui client para este processo. Isto **não** é um “Provider Satellite” certificado: essa categoria não existe no contrato Spider.

## Autenticação

Header `X-SEGSENSE-Mock-Credential` comparado ao segredo local `SEGSENSE_MOCK_CREDENTIAL`. Sem default versionado: o processo **não inicia** se a variável estiver vazia. Material distinto da identidade `local-demo-segsense` e do segredo SegSense↔Spider. Não imprimir o valor.

## O que **não** atravessa esta fronteira

`originSnapshot`, finalidade editorial, identidade da aplicação SegSense, `X-Spider-Credential-Ref`, o segredo SegSense↔Spider, token de link, notice, PII.

### Request

```json
{
  "contractVersion": "segsense-mock-contract-v1",
  "correlationId": "<uuid>",
  "decisionId": "<id da decisão Spider>",
  "scenarioKey": "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1",
  "declaredObjective": "UNDERSTAND_FAMILY_PROTECTION_OPTIONS"
}
```

### Response

`providerId=SEGSENSE_PROVIDER_MOCK`, `origin=ILLUSTRATIVE_NOT_ICATU_CONTRACT`, itens de jornada `notOfferable`, pendências humanas, watermark. Sem valores monetários. Sem nomes de produto Icatu.

## Falhas testáveis

| Sinal | Efeito |
|---|---|
| Header ausente/errado | 401 |
| Corpo inválido | 400 |
| `X-SEGSENSE-Mock-Force: unavailable` | 503 |
| `X-SEGSENSE-Mock-Force: timeout` | atraso > timeout da Spider |
| Sem internet | o processo **não** faz fetch externo |

`GET /health` → `{ "status": "ok", "providerId": "SEGSENSE_PROVIDER_MOCK" }`
