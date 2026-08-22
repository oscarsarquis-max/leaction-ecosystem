# Matriz endpoint × permissão × RLS

Toda rota autenticada usa `panne_runtime` + `panne_current_org_id()`. Recurso de outra organização é invisível (404) ou a rota é recusada (403 se a associação não existe).

| Família | Permissão mínima | RLS |
|---|---|---|
| Planos | `production.plan.read` / `.manage` | `organization_id` |
| Ordens e bateladas | `production.order.read` / `.manage` / `.release` / `.cancel` | `organization_id` |
| Quadro | `production.board.read` | `organization_id` |
| Pesagem | `.weighing.record` / `.verify` | `organization_id` |
| Consumo / etapa / ocorrência | permissões 013 | `organization_id` |
| Conclusão / short_close / ficha | permissões 013 | `organization_id` |
| Rastreabilidade | `production.traceability.read` | `organization_id` |
| Adoção de política | `production.order.policy_adopt` | `organization_id` |
| Papéis | `membership.role.manage` | org na escrita; leitura própria sem org para `/me` |
| `/me` | `identity.read_me` | memberships do usuário |
| `/health` `/ready` | nenhuma | prontidão administrativa só em `/ready` |
