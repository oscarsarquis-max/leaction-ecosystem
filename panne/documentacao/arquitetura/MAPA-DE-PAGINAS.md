# Mapa de páginas

| Rota | Página | Permissão |
|---|---|---|
| `/entrar` | autenticação | pública |
| `/callback` | retorno OIDC | pública |
| `/organizacao` | seleção de organização | autenticado |
| `/producao` | quadro | `production.board.read` |
| `/planejamento` | lista de planos | `production.plan.read` |
| `/planejamento/:id` | detalhe do plano | `production.plan.read` |
| `/ordens` | lista de ordens | `production.order.read` |
| `/ordens/:id` | detalhe operacional | `production.order.read` |
| `/ordens/:id/fichas/:issueId` | ficha imprimível | `production.order.read` |
| `/rastreabilidade` | busca | `production.traceability.read` |
| `/rastreabilidade/:id` | rastreio | `production.traceability.read` (negado ≠ vazio) |

Módulos futuros não aparecem como links.
