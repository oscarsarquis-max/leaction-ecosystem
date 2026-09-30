# AF-ADR-006 — Empresa explícita e isolamento no backend

## Controle

| Campo | Valor |
|---|---|
| Identificador | AF-ADR-006 |
| Versão | 0.1 |
| Status | PROPOSED |
| Data | 25/09/2026 |
| Dependências | ACTIONFINANCE_ARQ_001 §7.3 e §9 |

## Contexto

O produto é comum ao grupo. Um seletor de empresa na UI não é controle de acesso. Contraparte, categoria, centro e unidade de outra empresa não podem ser ligados a um título.

## Decisão

Toda entidade financeira pertence a uma empresa. Toda leitura, gravação e exportação valida principal autenticado e associação autorizada.

Relações de cadastro devem ser da mesma empresa, na aplicação e, quando aplicável, por chave composta/constraint PostgreSQL.

Não oferecer “Todas as empresas” até existir autorização e agregação definidas. Troca de empresa recarrega dados e limpa seleções.

`actorId` no corpo da requisição não é identidade.

## Alternativas rejeitadas

1. Confiar no companyId enviado pela UI.
2. Filtro opcional de empresa sem enforce no servidor.

## Consequências

- Contrato de identidade demo é pré-requisito da fundação utilizável.
- Deny-by-default; sem profile, API financeira permanece bloqueada.
