# CURSOR-004 — Retorno da execução

Data: 2026-08-22. Sem commit, push, deploy ou CURSOR-005. Aguarda revisão do arquiteto.

## 1. Somente leitura

Confirmado. Sessão MySQL: `SET SESSION TRANSACTION READ ONLY`, `START TRANSACTION READ ONLY`, consultas só a `information_schema` e `SHOW CREATE TABLE`, `ROLLBACK`. Cliente isolado. Variáveis de conexão só em memória de processo; limpas após a inspeção. Nenhuma credencial neste retorno nem nos documentos.

## 2. Tabelas analisadas

Núcleo de produto/ficha: `tbl_produto`, `tbl_produto_preco`, `tbl_ficha_tecnica`, `tbl_ficha_tecnica_ingrediente`, `tbl_ficha_tecnica_modo_preparo`, `tbl_ficha_tecnica_porcao`, `tbl_ficha_tecnica_porcao_ingrediente`.

Núcleo nutricional: `tbl_info_nutricional`, `tbl_info_nutricional_ingrediente`, `tbl_info_nutricional_descricao`, `tbl_info_nutricional_tabela`, `tbl_info_nutricional_observacao`.

Contexto já conhecido e revalidado por metadados: `tbl_ingrediente`, `tbl_medida`, `tbl_empresa`, `tbl_usuario`, `tbl_usuario_empresa`, `tbl_usuario_permissao`.

Periferia documental (para excluir do domínio): `tbl_pop*` (POP/inspeção), `tbl_lancamento_docs` (financeiro).

Catálogo do schema: 80 tabelas; 0 views; 0 triggers; 0 FKs declaradas.

## 3. Relações explícitas e inferidas

Explícitas: nenhuma.

Inferidas por `ID_*`: empresa/usuário → produto, ficha e info nutricional; produto → preço, ingrediente, ficha, info nutricional; ficha → linhas, preparo, porções; info nutricional → linhas, descrição, tabela, observação; `MC_MEDIDA` → `tbl_medida`. Ficha ↔ nutrição **só** pelo produto compartilhado.

## 4. Produto polimórfico

`USO_INGREDIENTE`, `USO_FICHA_TECNICA`, `USO_INFO_NUTRICIONAL` são flags independentes. O mesmo registro pode ser insumo, item de ficha e item de rotulagem. Filhos não referenciam os flags. Conceitos misturados: catálogo comercial, insumo, formulação e rótulo. **Não replicar.**

## 5. Estrutura da ficha técnica

Identidade + empresa/usuário/produto anuláveis; nome da receita; rendimentos (int + texto); tempos; pesos (total, real, bruto/líquido de insumos, porção, cozido); fator de cocção; perda/ganho; custos; `SITUACAO`/`BLOQUEADO`; cadastro e atualização. Sem versão, sem aprovação, sem unidade na linha, sem ordem.

## 6. Composição e preparo

Linhas com `ID_INGREDIENTE`, nome/código copiados, bruto, líquido, `FC`, custos. Preparo: `longtext` (PK com typo). Porção: cópia escalada (`CLIENTE`, artefato `QUANTIDADE__`), não versionamento.

## 7. Estrutura nutricional

Cabeçalho com totais, porção, rendimento final, medida caseira, macros em colunas, textos de ingredientes/alergênicos, validade/conservação/embalagem, responsável técnico em string, `OBSERVACAO` int. Segunda lista de ingredientes (sem PK) com `BASE_*`/`QTDE_*`. Descrição duplica textos e flags de glúten/lactose. Tabela impressa em `varchar`. Sem PDF.

## 8. Paralelismo ficha × rótulo

Duas composições, unidades e ordens ausentes, sem FK cruzada, sem evidência de cálculo. Rótulo pode divergir da ficha sem o banco detectar. Risco principal do legado.

## 9. Regras valiosas

Escopo por empresa; bruto/líquido/`FC`; rendimento e cocção; porção e medida caseira como parâmetros; distinção custo técnico vs preço comercial; situação/bloqueio; permissões de módulo; responsável (ainda que só textual).

## 10. Fragilidades

Zero FKs; `float`; polimorfismo; composições paralelas; textos e flags manuais; sem versão/aprovação/fonte/vigência; totais denormalizados; documentos fora do banco; charset `latin1`.

## 11. Matriz resumida

- **Preservar:** empresa, bruto/líquido/`FC`, rendimento/cocção, porção/medida caseira, ciclo de situação.
- **Repensar:** produto único, duas listas, nutrientes em colunas, custo na ficha, porção como cópia.
- **Descartar:** `USO_*`, `varchar` nutricional como fonte, POP/financeiro como ficha, artefatos, sobrescrita.
- **Criar:** formulação versionada, aprovação, evidência, cálculo derivado, snapshot de rótulo, trials.

## 12. Modelo conceitual proposto

Separar ingrediente (já existe), formulação + versão + item + etapas, produto técnico, cálculo nutricional derivado, documento preliminar/aprovado, rótulo snapshot, evidência, aprovação, escala e ensaio. Fonte única: `FormulationVersion` apontando `ingredient_version`.

## 13. Tabelas PostgreSQL propostas (não criadas)

Formulações: `technical_product`, `formulation`, `formulation_version`, `formulation_item`, `process_step`, `recipe_reference`, `scale_calculation`, `trial`, `trial_measurement`, `approval`.

Nutrição/docs: `nutrition_calculation`, `nutrition_calculation_item`, `calculation_evidence`, `technical_document`, `label_snapshot`, `label_declared_ingredient`, `label_allergen`.

Ligações ao núcleo existente: `organization`, `app_user`, `ingredient`/`ingredient_version`, `measurement_unit`, `nutrient_definition`, `allergen`, `data_source`, `audit_event`.

## 14. Questões pendentes (classes)

DDL fecha polimorfismo, ausência de FK/versão/PDF e flags manuais.  
Arquitetura fecha fonte única, imutabilidade e anti-polimorfismo.  
Proprietário fecha custo, papéis de aprovação, URI de PDF, IA.  
Especialista fecha piloto, baker’s %, farinha-base, perdas e forno.  
Regulatório fecha arredondamento, porção legal, normas e vigência.

## 15. Documentos criados

- `documentacao/legado/DDL-FICHAS-PRODUTOS-INVENTARIO.md`
- `documentacao/legado/DDL-FICHAS-PRODUTOS-RELACIONAMENTOS.md`
- `documentacao/legado/DDL-NUTRICAO-INVENTARIO.md`
- `documentacao/legado/DDL-NUTRICAO-RELACIONAMENTOS.md`
- `documentacao/arquitetura/MATRIZ-LEGADO-FICHAS-E-NUTRICAO.md`
- `documentacao/arquitetura/MODELO-CONCEITUAL-FORMULACOES.md`
- `documentacao/arquitetura/MODELO-CONCEITUAL-NUTRICAO-E-DOCUMENTOS.md`
- `documentacao/arquitetura/PROPOSTA-POSTGRESQL-FORMULACOES.md`
- `documentacao/arquitetura/PROPOSTA-POSTGRESQL-NUTRICAO-E-DOCUMENTOS.md`
- `documentacao/arquitetura/QUESTOES-FICHAS-E-NUTRICAO.md`
- `documentacao/prompts/CURSOR-004-analisar-fichas-produtos-nutricao.md`
- `documentacao/retornos/CURSOR-004-retorno-execucao.md`

## 16. Git

`git diff --check`: sem erro.

`git diff --stat` (rastreados; pré-existentes, não deste ciclo):

```
 infra/ecosystem-databases.sql     | 1 +
 leaction-ecosystem.code-workspace | 4 ++++
 2 files changed, 5 insertions(+)
```

`git status --short` (repo): `M` nos dois índices acima; `?? panne/` (pasta ainda não versionada); lixo pré-existente intacto (`diario-start.err`, logs, `phanton/database/_lan-sync/`).

Neste ciclo só nasceram os 12 markdowns listados no item 15. Backend, Alembic e frontend da Panne não foram editados.

## 17–19. Confirmações

- Nenhuma linha de negócio consultada.
- Nenhuma escrita no MySQL (só `ROLLBACK`).
- Nenhuma implementação antecipada: sem migração, sem tabela PostgreSQL nova, sem alteração de SQLAlchemy/API/frontend, sem seed, sem cálculo, sem commit/push/deploy.

## 20. Riscos e recomendações

Não portar as duas composições. Não tratar `varchar` nutricional nem flags de glúten como regra. Não avançar CURSOR-005 até o arquiteto fechar: obrigatoriedade de `technical_product`, baker’s %, materialização de preparação, e se custo entra em satélite. Manter MySQL somente leitura.
