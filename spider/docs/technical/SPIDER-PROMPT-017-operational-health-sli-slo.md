# SPIDER-PROMPT-017 — Saúde, SLIs, SLOs Provisórios e Cockpit Operacional

## Baseline

- Produto: **0.17.0** · boundary **MOCK_ONLY**
- Predecessor: SPIDER-PROMPT-016 VERIFIED
- Flags: `spider.operational-health.enabled` (default **false**); exige `spider.telemetry.enabled=true` quando ativo
- Janelas allowlist: `PT15M`, `PT1H`, `PT24H`, `P7D`

## Conceito

| Camada | Papel |
|--------|--------|
| Operational Events (016) | Observam fatos |
| SLI | Medem a partir de fontes reais |
| SLO provisório | Avaliam contra referência Mock não contratual |
| Cockpit | Explica a leitura |
| Engine | Continua decidindo só a execução |

Saúde **não** controla a Engine. Divisão por zero / amostra zero → `INSUFFICIENT_DATA` / `UNKNOWN`, nunca falso `100%` saudável.

## Modelo

`OperationalHealthSnapshot` (`schemaVersion=1`): janela, `overallStatus`, dimensões, `slis[]`, `sloEvaluations[]`, `errorBudgets[]`, `dataQuality`, `provisional=true`, `integrationLevel=MOCK_ONLY`.

Estados: `HEALTHY | DEGRADED | UNHEALTHY | UNKNOWN | INSUFFICIENT_DATA`.

## SLIs mínimos

1. Confiabilidade técnica (SUCCEEDED / terminações técnicas; outcome de negócio separado)
2. Latência p95 (ms)
3. Waits envelhecidos (razão acima do limiar)
4. Confirmação de callback
5. Aceitação de signal
6. Cobertura de telemetria

Definições: `implementation/sli-definitions-v1.json`  
Perfil: `implementation/provisional-slo-profile-v1.json`

## Error budget

Para ratios de sucesso: `consumed = (1-observed) / (1-target)` com estados `AVAILABLE|AT_RISK|EXHAUSTED|NOT_APPLICABLE|…`.

## API

- `GET /v1/console/operational-health?window=PT24H` — ação `VIEW_OPERATIONAL_HEALTH`
- `GET /v1/console/operational-health/definitions`
- DenyAll / console off → 404

## Console

Nav **Cockpit Operacional** (`OperationalCockpit.jsx`): banner permanente MOCK_ONLY / SLOs provisórios; cards SLI; error budget; estados loading/disabled/error/parcial.

## Relação 018

Failure Lab / fault injection / runbooks **não** fazem parte deste incremento.

## Referências

- ARCH-010 (health/SLI/SLO)
- ARCH-013 (cockpit)
- ARCH-014 (linguagem de negócio)
- Manifesto CAP-017
