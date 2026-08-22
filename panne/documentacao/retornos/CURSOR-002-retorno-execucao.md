# CURSOR-002 — Retorno da execução

Data: 2026-08-22. Sem commit, push, deploy ou CURSOR-003.

## 1. Somente leitura

Confirmado. Sessão MySQL: `SET SESSION TRANSACTION READ ONLY`, `START TRANSACTION READ ONLY`, consultas só a `information_schema` e `SHOW CREATE TABLE`, `ROLLBACK`. Cliente isolado em container. Sem `SELECT` de linhas de negócio.

## 2. Consultas estruturais (sem credenciais)

- `information_schema.tables`, `columns`, `table_constraints`, `key_column_usage`, `statistics`, `referential_constraints`, `views`, `triggers`
- `SHOW CREATE TABLE` das tabelas selecionadas por nome/coluna
- Nenhuma view ou trigger no núcleo

## 3. Tabelas legadas analisadas (núcleo)

`tbl_ingrediente`, `tbl_ingrediente_compra`, `tbl_ingrediente_info_nutricional`, `tbl_medida`, `tbl_produto`, `tbl_produto_preco`, `tbl_ficha_tecnica`, `tbl_ficha_tecnica_ingrediente`, `tbl_ficha_tecnica_modo_preparo`, `tbl_ficha_tecnica_porcao`, `tbl_ficha_tecnica_porcao_ingrediente`, `tbl_info_nutricional`, `tbl_info_nutricional_descricao`, `tbl_info_nutricional_ingrediente`, `tbl_info_nutricional_observacao`, `tbl_info_nutricional_tabela`, `tbl_empresa`, `tbl_usuario`, `tbl_usuario_empresa`, `tbl_usuario_permissao`, `tbl_pessoa`.

Catálogo do schema: 80 tabelas; 52 casaram critérios amplos (inclui financeiro/POP por `ID_USUARIO`). Essas periféricas não foram inventariadas em detalhe.

## 4. Relacionamentos

Nenhuma FK declarada no núcleo. Ligações por `ID_EMPRESA`, `ID_PRODUTO`, `ID_INGREDIENTE`, `ID_FICHA_TECNICA`, `ID_INFO_NUTRICIONAL`, `MC_MEDIDA` são **inferência**. Produto polimórfico (`USO_*`). Composições de ficha e de rótulo são paralelas.

## 5. Decisões valiosas

Empresa no cadastro; bruto/líquido e `FC`; rendimento e cocção na ficha; histórico de compra separado; papéis do produto (insumo/ficha/rótulo); situação/bloqueio; auditoria de usuário; perfil nutricional do insumo distinto do rótulo; medida caseira no rótulo.

## 6. Fragilidades

Sem FK/unique; `float`; unidade livre; nutrientes em colunas; alergênicos em texto; glúten/lactose manuais; sem versão/fonte/vigência; sem ordem; tabelas sem PK; totais desnormalizados; fornecedor desligado do insumo.

## 7. Matriz (resumo)

- **Preservar:** identidade do insumo, empresa, bruto/líquido, FC, histórico de preço, papéis, situação.
- **Repensar:** isolamento, nutrientes, unidades, preço na identidade, ficha vs rótulo, precisão.
- **Descartar:** nomes `tbl_*`, `float`, grade comercial no dossiê, senha de usuário, artefatos (`QUANTIDADE__`).
- **Criar:** versão, fonte, composição, catálogos, alergênicos tipados, conversão, evidência, `formula_ingredient` só como fronteira.

## 8. Modelo conceitual

`Ingredient` + `IngredientVersion` (agregado), `IngredientComposition`, `IngredientNutrient`, `NutrientDefinition`, `MeasurementUnit`, `UnitConversion`, `Allergen`, `IngredientAllergen`, `DataSource`, `OrganizationIngredient`, `SupplierItem`. `FormulaIngredient` só fronteira.

## 9. Tabelas PostgreSQL propostas (não criadas)

`measurement_unit`, `unit_conversion`, `nutrient_definition`, `allergen`, `data_source`, `ingredient`, `ingredient_version`, `ingredient_composition`, `ingredient_nutrient`, `ingredient_allergen`, `organization_ingredient`, `supplier_item`.

## 10. Documentos

- `documentacao/legado/DDL-INGREDIENTES-INVENTARIO.md`
- `documentacao/legado/DDL-INGREDIENTES-RELACIONAMENTOS.md`
- `documentacao/arquitetura/MATRIZ-LEGADO-INGREDIENTES.md`
- `documentacao/arquitetura/MODELO-CONCEITUAL-INGREDIENTES.md`
- `documentacao/arquitetura/PROPOSTA-POSTGRESQL-INGREDIENTES.md`
- `documentacao/arquitetura/QUESTOES-INGREDIENTES.md`
- `documentacao/prompts/CURSOR-002-analisar-ddl-ingredientes.md`
- `documentacao/retornos/CURSOR-002-retorno-execucao.md`

## 11. Python 3.12

Container isolado `python:3.12-slim-bookworm` (imagem oficial; sem install global; sem alterar outras apps). Runtime do container: **Python 3.12.14**.

| Checagem | Resultado |
|---|---|
| pytest | 1 passed |
| ruff check / format | ok |
| inicialização (`TestClient` `GET /health`) | 200, contrato estável |

## 12. Git

`git diff --check`: sem erro.  
`git diff --stat` (rastreados): só índices já da fundação (`ecosystem-databases.sql`, `.code-workspace`).  
`git status --short`: `M` nesses dois; `?? panne/`; lixo pré-existente intacto.

## 13–15. Confirmações

- Nenhuma linha de negócio consultada.
- Nenhuma escrita no legado.
- Nenhuma tabela ou migração criada na Panne. Alembic e SQLAlchemy intactos.

## 16. Riscos e pendências

- Inferências (preparação-como-insumo, base 100 g, `MC_MEDIDA`) não estão fechadas.
- `organization_ingredient` pode colapsar em `ingredient` na v1.
- Credenciais usadas só em variáveis de processo; não gravadas no repositório nem nestes documentos.
- Dump completo do legado não foi gerado nem versionado.
