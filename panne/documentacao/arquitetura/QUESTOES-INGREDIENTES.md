# Questões fundamentais — ingredientes

Respostas **somente quando o DDL permite**. Inferência não é regra.

| Questão | O que o DDL permite afirmar |
|---|---|
| O ingrediente é global, da empresa ou híbrido? | **Da empresa, de forma fraca.** Há `ID_EMPRESA` e `ID_USUARIO` anuláveis. Sem unique por empresa. Não há catálogo global de insumos. |
| Ingrediente e matéria-prima são o mesmo conceito? | **Não há tabela `materia_prima`.** O papel de insumo está em `tbl_ingrediente` e na flag `tbl_produto.USO_INGREDIENTE`. Matéria-prima e ingrediente coincidem no cadastro. |
| Existem ingredientes compostos? | **Não há tabela de composição do insumo.** Compostos, se existirem, estão na aplicação ou via produto que também tem ficha. **Inferência**, não regra. |
| Preparação pode ser ingrediente de outra ficha? | O DDL **permite** o apontamento: produto com `USO_FICHA_TECNICA` e `USO_INGREDIENTE`, e `tbl_ingrediente.ID_PRODUTO`. Não há constraint que imponha ou proíba. |
| Como unidades e medidas são representadas? | Ingrediente: `UNIDADE varchar(255)`. Rótulo: `MC_MEDIDA int` + `tbl_medida` (nome/plural). Duas representações. |
| Existem fatores de conversão? | **Não.** `tbl_medida` não tem fator. |
| Peso bruto e líquido? | Na **linha da ficha** (`PESO_BRUTO`, `PESO_LIQUIDO`) e totais no cabeçalho (`PESO_BRUTO_ING`, `PESO_LIQUIDO_ING`). Também na porção. Não no cadastro do ingrediente. |
| Perdas e rendimento? | Ficha: `RENDIMENTO`, `RENDIMENTO_RECEITA` (texto), `FATOR_COCCAO`, `PERDA_GANHO`. Linha: `FC`. Porção: `RENDIMENTO_PORCAO`. |
| Onde ficam os nutrientes? | (1) colunas em `tbl_ingrediente_info_nutricional`; (2) totais em `tbl_info_nutricional`; (3) base + `QTDE_*` em `tbl_info_nutricional_ingrediente`; (4) kcal/kJ/VD em `tbl_info_nutricional_tabela` como texto. |
| Nutrientes por 100 g, porção ou outra base? | **Não declarado.** Há `PORCAO`, `PESO_TOTAL` e linhas `TIPO` na tabela de apresentação. Inferir 100 g vs porção **sem ler dados** é especulação. |
| Fonte ou versão do dado nutricional? | **Não.** Só timestamps e usuário. Sem norma, tabela TACO, laudo ou vigência. |
| Como alergênicos ligam ao ingrediente? | **Não ligam.** Texto `INFO_ALERGENICOS` / `ALERGENICOS` no rótulo. Sem catálogo nem N:N com insumo. |
| Glúten e lactose: manuais ou derivados? | **Manuais** (`CONTEM_GLUTEN`, `CONTEM_LACTOSE` `NAO`/`SIM`) na descrição do rótulo. |
| Como a ficha usa ingredientes? | `tbl_ficha_tecnica_ingrediente` com ids + nome/código copiados + pesos + `FC` + custos. Sem FK. |
| Ordem de declaração? | **Não há coluna de ordem.** Se existir, está fora do banco. |
| Compostos na rotulagem? | Lista em `longtext` (`INFO_INGREDIENTES` / `INGREDIENTES`). Sem árvore de compostos. |
| Custo e histórico de preço? | Preço vigente no cadastro; histórico em `tbl_ingrediente_compra`; snapshot na linha da ficha; grade comercial no produto. Sem fornecedor na compra. |
| Empresa e usuário no cadastro? | `ID_EMPRESA`, `ID_USUARIO`, cadastro/cancelamento/atualização. Permissões `PER_FICHA_TECNICA` e `PER_ROTULAGEM_NUTRICIONAL`. Associativa usuário–empresa sem PK. |
| Versões ou sobrescrita? | **Sobrescrita** do estado atual + histórico de compra. Sem número de versão do dossiê. |
| Decisões só fora do banco? | Integridade referencial; unicidade de código; ordem das linhas; cálculo de `FC`, totais e `QTDE_*`; consistência ficha↔rótulo; base nutricional; composição aninhada; conversão de unidades; isolamento real multiempresa; fonte do dado. |

## Riscos para a Panne

- Portar colunas `float` e textos de rótulo como fonte da verdade.
- Tratar inferências (preparação-como-insumo, base 100 g, `MC_MEDIDA`) como fechadas.
- Implementar ficha ou rótulo antes de fechar identidade + versão do insumo.
- Ligar custo comercial ao mesmo agregado da conformidade.

## Decisões na realização

Fechadas ao realizar `PROPOSTA-POSTGRESQL-INGREDIENTES.md` (migração `0002_ingredient_catalog`).

| Pendência | Decisão |
|---|---|
| Catálogo global na v1? | **Híbrido controlado.** Unidades, nutrientes, alergênicos e fontes oficiais são globais. O insumo operacional é **só da organização**. Não há catálogo global de ingredientes nesta etapa. |
| Preparação reutilizada? | **Capacidade no banco.** `ingredient_composition` aceita `role = 'preparation'`. Não há ficha/`formula_ingredient`. Ciclo N níveis continua na aplicação. |
| Precisão `numeric`? | `numeric(14,6)` massa, quantidade e nutriente; `numeric(20,10)` fatores; `numeric(14,4)` preço unitário. |
| `organization_ingredient`? | **Atributo, não tabela.** `ingredient.organization_id` obrigatório. Unique de código ativo por organização. |
| Base nutricional oficial? | **`per_100g` é a base canônica** do dossiê. `per_100ml`, `per_portion` e `per_unit` existem no check, sem serem a fonte da conformidade. |

Respostas de produto alinhadas a essas decisões:

- Ingrediente na Panne: **organizacional**, com isolamento por `organization_id` e unique de código ativo.
- Ingrediente e matéria-prima: **o mesmo conceito** (`ingredient`).
- Compostos: **sim**, via `ingredient_composition` (`constituent`).
- Unidades: `measurement_unit` + `unit_conversion` (não `varchar`).
- Nutrientes: linhas `ingredient_nutrient` + `nutrient_definition`, com `basis` explícita.
- Fonte/versão: `data_source` + `ingredient_version` imutável após `published`.
- Alergênicos: `allergen` + `ingredient_allergen` (`contains` / `may_contain` / `absent` / `unknown`).
- Glúten e lactose: códigos do catálogo; override exige `override_reason`.
- Ordem: `sort_order` na composição.
- Custo: `supplier_item` + `supplier_item_price`, fora do dossiê técnico.
- Ficha: ainda fora; `formula_ingredient` continua só fronteira.

## Pendências que permanecem

1. Ciclo de composição em profundidade (só check de pai ≠ filho no SQL).
2. FK de `organization_id` e `supplier_party_id` quando `identity_organization` existir.
3. Semente oficial de unidades, nutrientes e alergênicos (esta realização não carrega dados).
4. Regra de derivação automática de glúten/lactose a partir da composição.
5. Autorização de `published_by` / revisão humana (sem módulo de identidade).
