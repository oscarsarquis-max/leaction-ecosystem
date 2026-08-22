# Matriz legado → Panne (ingredientes)

Classificação a partir do DDL, sem copiar tabelas. Itens marcados como inferência no inventário não viram regra confirmada.

## Preservar

Conceitos e relações válidos que devem continuar no domínio.

| Conceito legado | Por que preservar |
|---|---|
| Ingrediente como item de composição da ficha | Núcleo do produto |
| Pertinência à empresa | Isolamento multiempresa (hoje só por coluna) |
| Situação ativa / cancelada e bloqueio | Ciclo de vida |
| Distinção peso bruto × peso líquido | Padaria / ficha técnica |
| Fator de correção na linha (`FC`) | Perda de preparação do insumo |
| Rendimento, fator de cocção, perda/ganho na ficha | Fronteira com `calculation_engine` / `formula_lab` |
| Histórico de compra/preço separado do cadastro | Rastreio comercial |
| Produto com papéis (insumo / ficha / rótulo) | Um item pode ser preparação e também insumo |
| Perfil nutricional do insumo distinto do rótulo do produto | Dois agregados |
| Porção e medida caseira no rótulo | Rotulagem |
| Flags explícitas de glúten e lactose no rótulo | Exigência de declaração — no novo modelo, com origem |
| Auditoria de quem cadastrou / atualizou | Rastreabilidade humana |
| Aditivo como classificação do insumo | Informação de rotulagem |
| Catálogo de medidas (nome + plural) | Base para `MeasurementUnit` |
| Associativa usuário–empresa e permissão por módulo | Identidade (fora desta entrega) |

## Repensar

Conhecimento valioso, modelagem atual insuficiente.

| Legado | Limitação | Direção Panne |
|---|---|---|
| `ID_EMPRESA` anulável, sem unique | Isolamento frágil | `organization_id` obrigatório no item operacional + unique de negócio |
| `tbl_produto` polimórfico + `tbl_ingrediente.ID_PRODUTO` | Identidade duplicada | Identidade técnica versionada; papéis explícitos |
| Nutrientes em colunas fixas | Sem novos nutrientes, sem unidade/base | `nutrient_definition` + linhas `ingredient_nutrient` |
| Unidade `varchar` no ingrediente e `tbl_medida` à parte | Duas linguagens de medida | Unidade canônica + conversões |
| Preço vigente no mesmo row da identidade | Sobrescrita | Identidade ≠ versão técnica ≠ evento de custo |
| Linha da ficha com nome/código copiados | Drift | Referência a `ingredient_version` + snapshot explícito e datado |
| Ficha e rótulo com composições paralelas | Duas verdades | Uma composição versionada; rótulo como projeção |
| `float` para massa, nutriente e dinheiro | Erro de arredondamento | `numeric` com escala |
| Glúten/lactose manuais | Podem divergir da composição | Derivação + override justificado |
| Alergênicos em `longtext` | Sem lista controlada | Catálogo + relação tipada |
| Sem ordem na linha | Declaração de ingredientes | `sort_order` obrigatório na composição / fórmula |
| Sem FK | Integridade na aplicação | FK e checks no PostgreSQL |
| Tabelas sem PK (`*_info_nutricional` filhos) | Linhas fantasma | Toda entidade com UUID |
| `tbl_info_nutricional_tabela` em varchar | Apresentação misturada a dado | Dado numérico + view/projeção de rótulo |
| Porção como cópia da receita | Escala ad hoc | Fator de escala sobre versão da fórmula (futuro) |
| Charset misturado `latin1`/`utf8` | Acentos | UTF-8 único |
| `datetime` sem fuso | Ambiguidade | `timestamptz` UTC |

## Descartar

Circunstancial, obsoleto ou incompatível com a Panne.

| Item | Motivo |
|---|---|
| Copiar nomes físicos `tbl_*`, `ID_*` em maiúsculas | Convenção MySQL do legado |
| `float(9,n)` | Precisão inadequada |
| Coluna `QUANTIDADE__` | Artefato instável |
| Typo `ID_FICHA_TECNIA_MODO_PREPARO` | Não reproduzir |
| Grade `VD_*` / `BC_*` no produto | Precificação comercial, não dossiê de ingrediente |
| `tbl_produto_preco` no agregado de ingrediente | Outro bounded context |
| Lançamentos, POP, planos, recibos, backups | Fora do domínio |
| Senha e token em `tbl_usuario` | Auth nova, não este modelo |
| `tbl_info_nutricional_observacao.OBSERVACAO int` | Semântica opaca; não portar às cegas |
| Duplicar `INFO_INGREDIENTES` no cabeçalho e na descrição | Uma projeção de texto gerada |
| Persistência de totais só como fonte da verdade | Recalcular a partir das linhas |
| charset `latin1` | Não portar |

## Criar

Ausentes no legado e necessários à Panne.

| Conceito | Motivo |
|---|---|
| `ingredient_version` | Vigência, não sobrescrita |
| `data_source` | Origem (TACO, rótulo, laudo, fabricante, IBGE, RDC) |
| Evidência / citação na versão | Grounding e conformidade |
| `ingredient_composition` | Compostos e preparação-como-insumo, acíclico |
| `nutrient_definition` | Catálogo estável de nutrientes e unidades |
| Base nutricional explícita (`per_100g`, etc.) | O legado não declara a base |
| `allergen` + `ingredient_allergen` | Presença / traços / ausência |
| `unit_conversion` | `tbl_medida` não converte |
| Isolamento multiempresa com unique | `organization_ingredient` |
| `supplier_item` | Fornecedor existe em `tbl_pessoa` mas não se liga ao insumo |
| Precisão `numeric` e UUID | PostgreSQL / auditoria |
| Preparação para `formula_ingredient` | Fronteira com ficha, sem implementar ficha agora |
| Revisão humana e status de publicação da versão | Conformidade |
| Energia (kcal/kJ) no dossiê do insumo | Só aparece na tabela-apresentação do rótulo |
| Ordem de declaração | Rotulagem |
| Idempotência de código interno por organização | Operação |
