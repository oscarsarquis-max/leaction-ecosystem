# AF-ADR-004 — EXPERIENCE com operações locais próprias

## Controle

| Campo | Valor |
|---|---|
| Identificador | AF-ADR-004 |
| Versão | 0.1 |
| Status | PROPOSED |
| Data | 25/09/2026 |
| Dependências | ACTIONFINANCE_ARQ_001 §4.3; SAT-003 |

## Contexto

O contrato V1 distingue EXPERIENCE (objetivo, contexto, finalidade, apresentação) de PROVIDER (executar capability). O serviço vigente recusa `EXECUTE_CAPABILITY` e `CAPABILITY_RESULT` originados de EXPERIENCE.

O ActionFinance precisa registrar e consultar obrigações mesmo com a Spider indisponível.

## Decisão

Operações locais (rascunho, registro, consulta, correção auditada, cancelamento gerencial) pertencem ao ActionFinance: autorização e auditoria próprias.

Execução externa e dados de outros sistemas passam pela Spider. O frontend só fala com o backend ActionFinance. O backend não chama Panne, Hub, banco ou provider diretamente e não escolhe rota/provider no envelope EXPERIENCE.

Não implementar o produto também como PROVIDER só para contornar o contrato.

## Alternativas rejeitadas

1. Todo clique financeiro como interaction canônica.
2. ActionFinance-PROVIDER paralelo sem ADR de identidade.
3. UI chamando a Spider.

## Consequências

- Readiness local não inclui Spider.
- Integração efetiva espera contrato financeiro (AF-ADR-009).
