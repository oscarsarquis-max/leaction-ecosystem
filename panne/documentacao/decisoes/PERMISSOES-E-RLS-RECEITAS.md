# Permissões e RLS — receitas

Papéis internos apenas. Sem grupos Cognito e sem `legacy_role_label`.

| Código | Dono / admin / técnico | Regulatório | Padeiro / produção / visualizador |
|---|---|---|---|
| `recipe.read` | sim | sim | sim |
| `recipe.create` | sim | não | não |
| `recipe.update_draft` | sim | não | não |
| `recipe.version.create` | sim | não | não |
| `recipe.scale` | sim | não | não |
| `recipe.trial.manage` | sim | não | não |
| `recipe.review` | sim | sim | não |
| `recipe.approve` | sim | sim | não |
| `recipe.publish` | sim | não | não |
| `recipe.retire` | sim | não | não |
| `recipe.reference.manage` | sim | não | não |
| `recipe.technical_sheet.read` | sim | sim | sim |

Padeiro lê receita **publicada** e a ficha derivada. Listagens sem `update_draft`/`review`/`approve`/`publish` filtram `published_only`. RLS de organização permanece; `formulation_command` entra no inventário `FORMULATION_HTTP_TABLES`.
