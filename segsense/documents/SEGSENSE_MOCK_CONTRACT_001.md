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

## Provider Contract 1.1 (cotação sintética)

Capability `GENERATE_SYNTHETIC_HOME_QUOTE`. Contrato versionado; **não** substitui o 1.0. Inputs: `scenarioKey`, `dwellingType` (`APARTMENT`|`HOUSE`), `insuredAmountCents` (5_000_000–200_000_000), `coverPeriodMonths=12`, `ratingRuleVersion=HOME_QUOTE_SYNTHETIC_V1`. **Proibido** enviar `premium` ou concatenar capital/prêmio em `scenarioKey`.

Regra `HOME_QUOTE_SYNTHETIC_V1` (inventada; não mercado; não Icatu; incêndios **não** entram):

`premiumAnnualCents = round_half_up(insuredAmountCents * dwellingBps / 10000)` — apartamento 18 bps, casa 22 bps.

Resposta: `status=COMPLETED`, `origin=NON_BINDING_DEMO`, `providerReference` (`qte-…`), `calculatedAt`, `insuredAmountCents`, `premiumAnnualCents`, premissas. Sem parcelamento, impostos, franquia nesta versão.

Schemas: `spider/backend/src/main/resources/contracts/provider/1.1/`. Documentação de produto: `SEGSENSE_FUN_004`, `SEGSENSE_ADR_007`.
