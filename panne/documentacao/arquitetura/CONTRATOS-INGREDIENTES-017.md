# Contratos HTTP de ingredientes — CURSOR-017

Prefixo autenticado: `/api/v1/organizations/{organization_id}`.
Sessão runtime + RLS. Sem `organization_id` no corpo. Erros `{code, message}` em português.

## Leituras

| Método | Caminho | Permissão |
|---|---|---|
| GET | `/ingredients` | `ingredient.read` |
| GET | `/ingredients/{id}` | `ingredient.read` |
| GET | `/ingredients/{id}/versions` | `ingredient.read` |
| GET | `/ingredients/{id}/versions/{vid}` | `ingredient.read` |
| GET | `/ingredients/{id}/versions/{vid}/completeness` | `ingredient.read` |
| GET | `/ingredients/{id}/items` | `supplier.read` |
| GET | `/suppliers` | `supplier.read` |
| GET | `/items/{id}/prices` | `supplier.read` |
| GET | `/catalog/units\|nutrients\|allergens\|sources` | `ingredient.read` |

Lista: `q`, `status`, `version_status`, `allergen_id`, `supplier_id`, `limit` (1–50), `offset`. A lista não carrega o dossiê.

## Comandos

| Método | Caminho | Permissão | Idempotência | If-Match |
|---|---|---|---|---|
| POST | `/ingredients` | `ingredient.create` | sim | não |
| PATCH | `/ingredients/{id}` | `ingredient.update_draft` | — | sim |
| POST | `/ingredients/{id}/versions` | `ingredient.update_draft` | sim | não |
| PATCH | `.../versions/{vid}` | `ingredient.update_draft` | — | sim |
| POST | `.../publish` | `ingredient.publish` | sim | opcional |
| POST | `.../retire` | `ingredient.retire` | sim | opcional |
| POST/DELETE | `.../composition` | `ingredient.update_draft` | — | sim |
| POST | `.../nutrients` | `ingredient.update_draft` | — | sim |
| POST | `.../allergens` | `ingredient.update_draft` | — | sim |
| POST | `/suppliers` | `supplier.manage` | sim | não |
| PATCH | `/suppliers/{id}` | `supplier.manage` | — | sim |
| POST | `/suppliers/{id}/items` | `supplier.manage` | sim | não |
| POST | `/items/{id}/prices` | `supplier.price.record` | sim | não |

Decimais viajam como string. `unit_price` é valor de compra observado, não preço de venda.
