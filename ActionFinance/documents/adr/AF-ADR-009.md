# AF-ADR-009 — Integração financeira bloqueada até contrato Spider próprio

## Controle

| Campo | Valor |
|---|---|
| Identificador | AF-ADR-009 |
| Versão | 0.1 |
| Status | PROPOSED |
| Data | 25/09/2026 |
| Dependências | ACTIONFINANCE_ARQ_001 §8; schema Satellite 1.2; SAT-003 |

## Contexto

O schema 1.2 restringe `purpose` a avaliação de seguros e de capital de giro. `responseChannel` aceita só `SYNC`. EXPERIENCE não envia execução nem resultado de capability. Não há purpose financeiro genérico.

## Decisão

Não escolher versão de contrato financeiro agora. Não colocar dados financeiros em `metadata` nem em `extensions` de seguros/crédito.

A evolução (PRM_005) deve tratar: finalidade, contexto empresarial autorizado, referências de negócio, envelope financeiro permitido, classificação, resposta síncrona, acompanhamento e resultado assíncrono — com compatibilidade dos satélites existentes.

ActionFinance não implementa webhook fictício rotulado como integração pronta. Não há provider bancário aprovado.

## Alternativas rejeitadas

1. Reusar `WORKING_CAPITAL_ASSESSMENT` para contas a pagar.
2. Dual-role EXPERIENCE+PROVIDER sem ADR.
3. Client direto a banco/adquirente/Panne/Hub.

## Consequências

- PRM_002–004 avançam só no recorte local.
- 200/202 de transporte nunca significa liquidação.
