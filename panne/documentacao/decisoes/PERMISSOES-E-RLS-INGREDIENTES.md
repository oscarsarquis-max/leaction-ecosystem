# Permissões e RLS de ingredientes

Sem grupos Cognito e sem `legacy_role_label` como autorização.

## Permissões novas

`ingredient.read`, `ingredient.create`, `ingredient.update_draft`, `ingredient.publish`, `ingredient.retire`, `supplier.read`, `supplier.manage`, `supplier.price.record`.

## Menor privilégio

| Papel | Ingredientes | Fornecedores |
|---|---|---|
| viewer / production_manager | leitura | leitura |
| baker_operator | só `ingredient.read` | não |
| commercial | leitura | gerir + registrar compra |
| technical_responsible / owner / admin | ciclo completo | ciclo completo |
| restricted | nada | nada |

Publicação exige `ingredient.publish`. Padeiro não administra ingredientes por padrão.

## RLS

Tabelas de identidade, versão, composição, nutriente, alergênico, fornecedor, item e `ingredient_command` são organizacionais. `panne_runtime` vê só `panne_current_org_id()`. Catálogos globais (unidade, nutriente, alergênico, fonte) são somente leitura autenticada. Preço herda o isolamento do item.
