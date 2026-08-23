# Completude do dossiê

Projeção determinística. Completude ≠ conformidade.

| Código | Bloqueia publicação | Origem |
|---|---|---|
| `identificacao` | sim | código / nome |
| `identidade_inativa` | sim | `ingredient.status` |
| `base_nutricional` | sim | base 100 g |
| `composicao` | sim | composto/preparação sem linhas |
| `nutricao` / `nutricao_incompleta` / `nutricao_loq` | não | nutrientes |
| `alergenico_pendente` | não | alergênicos |
| `fonte_pendente` | não | fonte da versão |
| `fornecedor` | não | item ativo |

Cada item explica rótulo e origem. `ready_to_publish` ignora alertas. `complete_dossier` exige zero pendências.
