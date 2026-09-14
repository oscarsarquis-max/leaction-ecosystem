# SEGSENSE_ADR_007 — Cotação simulada versus oferta real; contratos versionados

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_ADR_007 |
| Status | Aceita nesta etapa |
| Data | 14/09/2026 |
| Relacionados | SEGSENSE_ADR_005, SEGSENSE_ADR_006, SPIDER-SATELLITE-CONTRACT-V1, Provider Contract 1.0/1.1 |

## Contexto

O patrocinador pediu um número de prêmio em R$ na jornada pública. Não há contrato nem API Icatu de seguro residencial autorizado. Uma “cotação Icatu” seria falsa.

## Decisão

1. Entregar **simulação demonstrativa** (`NON_BINDING_DEMO`) calculada no Insurance Provider Mock, capability `GENERATE_SYNTHETIC_HOME_QUOTE`. Watermark: `SIMULAÇÃO DEMONSTRATIVA — SEM VALIDADE COMERCIAL — NÃO É OFERTA ICATU NEM CONTRATAÇÃO`.
2. **Não** alterar schemas Satellite 1.0/1.1 silenciosamente. Campos de cotação cabem em `attributes` (máx. 8). Capital em centavos é valor livre (fora da lista YAML de enums).
3. **Provider Contract 1.1** versionado para inputs numéricos. Provider 1.0 permanece para a jornada ilustrativa. Proibido concatenar prêmio/capital em `scenarioKey`.
4. Contratação efetiva, assinatura, pagamento e emissão: recusa no BFF (`REQUEST_EFFECTIVE_CONTRACT`) sem chamar Spider/mock. `REQUEST_BINDING_QUOTE` na API antiga continua `REJECTED` na Spider.
5. Prêmio na UI só após `COMPLETED` + referência nesta execução. Provider indisponível: nenhum valor antigo, fallback ou preço no frontend.

## Consequências

- Taxas 18/22 bps são inventadas (`HOME_QUOTE_SYNTHETIC_V1`). Não calibram mercado.
- Incêndios próximos são fato editorial da jornada, não fator de preço.
- Trocar o mock por seguradora autorizada exige registro, adapter, contrato e autorização reais — não um rótulo na UI.

## Alternativas rejeitadas

- Hardcode de R$ no frontend.
- Esconder capital/prêmio em `scenarioKey`.
- Apresentar recusa técnica (“cotação vinculante”) como opção de menu.
- Inferir produto residencial Icatu a partir do site institucional de vida/previdência/capitalização.
