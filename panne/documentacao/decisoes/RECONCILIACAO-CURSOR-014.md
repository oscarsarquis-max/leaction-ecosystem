# Reconciliação CURSOR-014

Registrada antes da migração `0012_production_api_roles`.

| Tema | Estado 013 | Decisão 014 |
|---|---|---|
| Papel único por associação | `organization_membership.role` NOT NULL | Relação `organization_membership_role` é a fonte da autorização. A coluna `role` permanece como rótulo primário (compatibilidade 0009). |
| `/me` | `roles` com um item | Lista de papéis ativos e união de permissões da associação selecionada. |
| Quantidade de pesagem/consumo | `quantity` na unidade informada, somada crua | `quantity` = informada; canônica em gramas; projeções somam canônico. |
| Ordem liberada sem política | Execução bloqueada; sem backfill | Comando `adopt_execution_policy` se `released`/`on_hold` e sem fatos. |
| `scrapped` | Catálogo de batelada; sem comando | Reservado/depreciado. Sem comando `scrap`. |
| CORS / OpenAPI | só GET; `docs_url=None` | Métodos de escrita no FE local; `/openapi.json` publicado. |
| Autorização Cognito | grupos não autorizam | Inalterado. |

Incompatibilidades não bloqueantes: estação/área não existe no modelo físico — o filtro do quadro busca texto limitado no código público.
