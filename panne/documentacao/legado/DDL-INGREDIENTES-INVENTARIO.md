# Inventário estrutural — ingredientes (legado MySQL)

Fonte: catálogo `information_schema` e `SHOW CREATE TABLE`.  
Sessão: `SET SESSION TRANSACTION READ ONLY` + `START TRANSACTION READ ONLY` + `ROLLBACK`.  
Nenhuma linha de negócio foi lida. Nenhuma escrita. Credenciais e endpoint não são registrados aqui.

O banco legado contém 80 tabelas. A descoberta por nome/coluna selecionou 52. Este inventário detalha o **núcleo de ingredientes, ficha, nutrição, medida, produto e escopo empresa/usuário**. Tabelas financeiras, POP, planos e backups entram só como periferia (puxadas pelo critério `ID_USUARIO` / `custo`).

Não há views nem triggers no conjunto selecionado.

Convenção de situação recorrente: `enum('CADASTRADO','CANCELADO')`. Bloqueio: `enum('F','T')`.  
Charset predominante: `latin1`; algumas tabelas `utf8`. Tipos monetários e de massa: `float`, não `decimal`.

**Nenhuma chave estrangeira está declarada** nas estruturas abaixo. Toda ligação por `ID_*` é **inferência**.

---

## Núcleo

### `tbl_ingrediente`

1. **Nome técnico:** `tbl_ingrediente`
2. **Finalidade aparente:** cadastro do item usado em ficha e rotulagem; mistura identidade, compra atual e situação.
3. **Colunas relevantes:** `ID_INGREDIENTE`, `ID_USUARIO`, `ID_EMPRESA`, `ID_PRODUTO`, `CODIGO_INGREDIENTE`, `INGREDIENTE`, `ADITIVO`, `UNIDADE`, `QTDE_COMPRADA`, `PRECO`, `PRECO_UNIDADE`, `DATA_COMPRA`, cancelamento, `BLOQUEADO`, `SITUACAO`, cadastro.
4. **PK:** `ID_INGREDIENTE` (`int` auto_increment).
5. **FKs declaradas:** nenhuma.
6. **Relações inferidas:** `ID_EMPRESA` → `tbl_empresa`; `ID_USUARIO` / `ID_USUARIO_CADASTRO` / `ID_USUARIO_CANCELAMENTO` → `tbl_usuario`; `ID_PRODUTO` → `tbl_produto` (item de catálogo que também pode ser ingrediente).
7. **Índices / unicidade:** só PK. Sem unique de `(empresa, código)` ou nome.
8. **Nulabilidade:** só a PK é `NOT NULL`.
9. **Padrões:** nenhum `DEFAULT` além de `NULL`.
10. **Tipos:** nome e unidade `varchar(255)`; quantidades `float(9,3)`; preços `float(9,2)`; `ADITIVO` `enum('F','T')`.
11. **Empresa / usuário:** `ID_EMPRESA`, `ID_USUARIO`, usuários de cadastro e cancelamento.
12. **Situação:** `SITUACAO`, `BLOQUEADO`, `DATA_CANCELAMENTO`.
13. **Criação / atualização:** `DATA_CADASTRO`; sem `DATA_ATUALIZACAO`.
14. **Versionamento:** ausente; estado atual sobrescrito. Histórico de preço em tabela irmã.
15. **Ficha:** usado por `tbl_ficha_tecnica_ingrediente` e `tbl_ficha_tecnica_porcao_ingrediente` (**inferência**).
16. **Nutrição:** `tbl_ingrediente_info_nutricional` e `tbl_info_nutricional_ingrediente` (**inferência**).
17. **Riscos:** unidade livre, sem FK para `tbl_medida`; preço e quantidade de compra no mesmo registro da identidade; `float`; isolamento multiempresa só por coluna anulável, sem unique.

### `tbl_ingrediente_compra`

1. **Nome:** `tbl_ingrediente_compra`
2. **Finalidade:** histórico de compras/preços do ingrediente.
3. **Colunas:** `ID_INGREDIENTE_COMPRA`, `ID_INGREDIENTE`, `UNIDADE`, `QTDE_COMPRADA`, `PRECO`, `PRECO_UNIDADE`, `DATA_COMPRA`, `SITUACAO`, cadastro.
4. **PK:** `ID_INGREDIENTE_COMPRA`.
5. **FKs:** nenhuma.
6. **Inferência:** `ID_INGREDIENTE` → `tbl_ingrediente`. Sem fornecedor.
7. **Índices:** só PK.
8. **Nulabilidade:** só PK obrigatória.
9. **Padrões:** nenhum.
10. **Tipos:** iguais aos campos de compra do cadastro (`float` + `varchar` de unidade).
11. **Empresa / usuário:** só `ID_USUARIO_CADASTRO` (empresa vem do ingrediente, **inferência**).
12. **Situação:** `CADASTRADO` / `CANCELADO`.
13. **Auditoria:** `DATA_CADASTRO`.
14. **Versionamento:** histórico de preço, não de ficha técnica do ingrediente.
15. **Ficha:** indireta, via ingrediente.
16. **Nutrição:** nenhuma.
17. **Riscos:** duplica colunas do cadastro; sem unique `(ingrediente, data)`; sem vínculo a `tbl_pessoa.FORNECEDOR`.

### `tbl_ingrediente_info_nutricional`

1. **Nome:** `tbl_ingrediente_info_nutricional`
2. **Finalidade:** nutrientes fixos do ingrediente (colunas, não catálogo).
3. **Colunas:** `ID_INGREDIENTE`, `CARBOIDRATO`, `PROTEINA`, `GORDURA_TOTAL`, `GORDURA_SATURADA`, `GORDURA_TRANS`, `FIBRA_ALIMENTAR`, `SODIO`, `SITUACAO`, cadastro.
4. **PK:** **ausente**.
5. **FKs:** nenhuma.
6. **Inferência:** 0..1 (ou N) linhas por `ID_INGREDIENTE`.
7. **Índices:** nenhum.
8. **Nulabilidade:** todas anuláveis, inclusive o identificador.
9. **Padrões:** nenhum.
10. **Tipos:** `float(9,2)` para nutrientes.
11. **Usuário:** `ID_USUARIO_CADASTRO`. Sem empresa própria.
12. **Situação:** `SITUACAO`.
13. **Auditoria:** `DATA_CADASTRO`. Sem atualização.
14. **Versionamento:** sobrescrita; sem fonte nem vigência.
15. **Ficha:** indireta.
16. **Nutrição:** é o dossiê nutricional do ingrediente. Base (100 g vs porção) **não está no DDL**.
17. **Riscos:** sem PK/unique; conjunto de nutrientes rígido; sem energia (kcal/kJ); charset `utf8` distinto do cadastro `latin1`.

### `tbl_medida`

1. **Nome:** `tbl_medida`
2. **Finalidade:** catálogo curto de nomes de medida (singular/plural).
3. **Colunas:** `ID_MEDIDA`, `MEDIDA`, `MEDIDA_PLURAL`, `BLOQUEADO`, `SITUACAO`.
4. **PK:** `ID_MEDIDA`.
5. **FKs:** nenhuma.
6. **Inferência:** `tbl_info_nutricional.MC_MEDIDA` aponta para cá. `tbl_ingrediente.UNIDADE` **não** usa este id.
7. **Índices:** só PK.
8. **Nulabilidade:** só PK obrigatória.
9. **Padrões:** nenhum.
10. **Tipos:** `varchar(255)` + enums de situação.
11. **Empresa / usuário:** nenhum — aparenta catálogo global.
12. **Situação:** `BLOQUEADO`, `SITUACAO`.
13. **Auditoria:** nenhuma.
14. **Versionamento:** nenhum.
15. **Ficha:** não referenciada no DDL da ficha.
16. **Nutrição:** medida caseira da rotulagem (**inferência**).
17. **Riscos:** sem dimensão (massa/volume), sem símbolo, sem fator para grama/ml.

### `tbl_produto`

1. **Nome:** `tbl_produto`
2. **Finalidade:** item de catálogo da empresa que pode ser ingrediente, ficha e/ou rotulagem.
3. **Colunas relevantes:** `ID_PRODUTO`, `ID_EMPRESA`, `ID_USUARIO`, `CODIGO_PRODUTO`, `PRODUTO`, preços/markups (`PRECO_CUSTO_*`, `VD_*`, `BC_*`), `USO_INGREDIENTE`, `USO_FICHA_TECNICA`, `USO_INFO_NUTRICIONAL`, situação/bloqueio/cancelamento, cadastro.
4. **PK:** `ID_PRODUTO`.
5. **FKs:** nenhuma.
6. **Inferência:** `ID_EMPRESA` → empresa; flags `USO_*` ligam o mesmo produto aos três módulos; `tbl_ingrediente.ID_PRODUTO` reusa este cadastro.
7. **Índices:** só PK. Sem unique de código por empresa.
8. **Nulabilidade:** `USO_*` são `NOT NULL`; demais (exceto PK) anuláveis.
9. **Padrões:** nenhum.
10. **Tipos:** preços `float(9,2)`; usos `enum('F','T')`.
11. **Empresa / usuário:** ambos, mais cancelamento.
12. **Situação:** `SITUACAO`, `BLOQUEADO`, cancelamento.
13. **Auditoria:** `DATA_CADASTRO`; sem atualização.
14. **Versionamento:** nenhum.
15. **Ficha:** `USO_FICHA_TECNICA` + `tbl_ficha_tecnica.ID_PRODUTO` (**inferência**).
16. **Nutrição:** `USO_INFO_NUTRICIONAL` + `tbl_info_nutricional.ID_PRODUTO` (**inferência**).
17. **Riscos:** um registro polimórfico; preços de venda no mesmo lugar da identidade técnica; `float`.

### `tbl_produto_preco`

1. **Nome:** `tbl_produto_preco`
2. **Finalidade:** preço por modalidade (`VENDA DIRETA` / `VENDA BALCÃO`) e tipo (`KG/UNIT` / `PORCAO`).
3. **Colunas:** ids, `MODALIDADE`, `TIPO_PRECO`, `PRECO_CUSTO`, `PRECO_VENDA`, situação, cadastro.
4. **PK:** `ID_PRODUTO_PRECO`.
5. **FKs:** nenhuma.
6. **Inferência:** `ID_PRODUTO` → `tbl_produto`.
7. **Índices:** só PK.
8–10. Quase tudo anulável; `float(9,2)`; enums de modalidade.
11. Só usuário de cadastro.
12. `SITUACAO`.
13. `DATA_CADASTRO`.
14. Sem vigência de preço (sem `valid_from`).
15–16. Indireto, via produto.
17. Duplica a grade de markups já existente em `tbl_produto`.

### `tbl_ficha_tecnica`

1. **Nome:** `tbl_ficha_tecnica`
2. **Finalidade:** cabeçalho da receita/ficha: rendimentos, pesos, fator de cocção, custos agregados.
3. **Colunas relevantes:** `ID_FICHA_TECNICA`, empresa, usuário, produto, `NOME_RECEITA`, `RENDIMENTO`, `RENDIMENTO_RECEITA`, tempos, `PESO_PORCAO`, `PESO_COZIDO`, `FATOR_COCCAO`, `PERDA_GANHO`, `PESO_TOTAL`, `PESO_REAL`, `PESO_BRUTO_ING`, `PESO_LIQUIDO_ING`, custos, bloqueio, situação, cadastro/atualização.
4. **PK:** `ID_FICHA_TECNICA`.
5. **FKs:** nenhuma.
6. **Inferência:** empresa, usuário, produto; filhos nas tabelas `tbl_ficha_tecnica_*`.
7. **Índices:** só PK.
8–10. Quase tudo anulável; massas `float(9,3)`; custos `float(9,2)`; `RENDIMENTO` `int`; `RENDIMENTO_RECEITA` texto.
11. `ID_EMPRESA`, vários `ID_USUARIO*`.
12. `BLOQUEADO`, `SITUACAO`.
13. `DATA_CADASTRO`, `DATA_ATUALIZACAO`.
14. Sobrescrita do estado atual; sem número de versão.
15. É a ficha.
16. Sem FK para info nutricional; encontro seria via `ID_PRODUTO` (**inferência**).
17. Totais desnormalizados; dois campos de rendimento com tipos diferentes.

### `tbl_ficha_tecnica_ingrediente`

1. **Nome:** `tbl_ficha_tecnica_ingrediente`
2. **Finalidade:** linha da ficha: bruto, líquido, fator de correção (`FC`), custos.
3. **Colunas:** ids, `CODIGO_INGREDIENTE`, `INGREDIENTE` (nome copiado), `PESO_BRUTO`, `PESO_LIQUIDO`, `FC`, `PESO_TOTAL`, `CUSTO_POR_INGREDIENTE`, `PRECO_KG`, `CUSTO_UNITARIO`, `DATA_CADASTRO`.
4. **PK:** `ID_FICHA_TECNICA_INGREDIENTE`.
5. **FKs:** nenhuma.
6. **Inferência:** `ID_FICHA_TECNICA` → ficha; `ID_INGREDIENTE` → ingrediente. Nome/código denormalizados.
7. **Índices:** só PK. Sem unique da linha. Sem coluna de ordem.
8–10. Quase tudo anulável; `FC` `float(9,1)`; pesos `float(9,3)`.
11. Sem empresa própria.
12. Sem `SITUACAO` na linha.
13. Só `DATA_CADASTRO`.
14. Nenhum.
15. Associação direta ficha↔ingrediente.
16. Nenhuma na linha.
17. Sem unidade na linha (peso implícito); sem ordem, etapa ou % baker; snapshot de custo sem vigência.

### `tbl_ficha_tecnica_modo_preparo`

1. **Nome:** `tbl_ficha_tecnica_modo_preparo`
2. **Finalidade:** texto de modo de preparo e observação.
3. **Colunas:** `ID_FICHA_TECNIA_MODO_PREPARO` (typo no nome), `ID_FICHA_TECNICA`, `MODO_PREPARO`, `OBSERVACAO`.
4. **PK:** o id com typo.
5. **FKs:** nenhuma.
6. **Inferência:** 0..N textos por ficha (cardinalidade real só na aplicação).
7–14. Sem índices extras, sem situação, sem auditoria.
15. Filho da ficha.
16. Nenhuma.
17. Typo no identificador; `longtext` sem estrutura de passos.

### `tbl_ficha_tecnica_porcao` e `tbl_ficha_tecnica_porcao_ingrediente`

1. **Nomes:** escala da ficha para um “cliente” / quantidade, com linhas de peso por ingrediente.
2. **Finalidade:** redimensionar a receita.
3. **Colunas (porção):** `CLIENTE`, `QUANTIDADE`, `QUANTIDADE_ESCRITA`, `QUANTIDADE__` (nome instável), pesos agregados, `RENDIMENTO_PORCAO`, situação, cadastro.
4. **PKs:** ids próprios.
5. **FKs:** nenhuma.
6. **Inferência:** porção → ficha; linha → porção + ingrediente. Nome do ingrediente denormalizado.
7. Só PKs.
8. Na linha, `SITUACAO` é `NOT NULL` (exceção).
9–10. `float` / `varchar`.
11. Usuário só no cabeçalho da porção.
12. `SITUACAO` nos dois.
13. Cadastro só no cabeçalho.
14. Nenhum.
15. Dependem da ficha.
16. Nenhuma.
17. Coluna `QUANTIDADE__`; cópia da composição em vez de fator único de escala.

### `tbl_info_nutricional`

1. **Nome:** `tbl_info_nutricional`
2. **Finalidade:** rotulagem do produto: porção, totais nutricionais, textos livres.
3. **Colunas relevantes:** empresa, usuário, produto, `PESO_TOTAL`, `PORCAO`, `RENDIMENTO_FINAL`, `MC_QUANTIDADE`, `MC_MEDIDA`, `QTDE_*` (macro nutrientes), `DESCRICAO_PORCAO`, `INFO_INGREDIENTES`, `INFO_ALERGENICOS`, validade, conservação, peso líquido de venda, situação.
4. **PK:** `ID_INFO_NUTRICIONAL`.
5. **FKs:** nenhuma.
6. **Inferência:** produto/empresa; `MC_MEDIDA` → `tbl_medida`; filhos nas tabelas `tbl_info_nutricional_*`.
7. Só PK.
8–10. Totais `float(9,2)`; textos `longtext`; `MC_MEDIDA` `int`.
11. Empresa e usuários de cadastro/atualização.
12. `BLOQUEADO`, `SITUACAO`.
13. Cadastro e atualização.
14. Sobrescrita; sem fonte oficial nem vigência regulatória.
15. Ligação com ficha só via produto (**inferência**).
16. É o documento nutricional do produto. Base dos `QTDE_*` (porção vs 100 g) **não está nomeada no DDL**.
17. Alergênicos e lista de ingredientes como texto livre no cabeçalho, duplicados na descrição.

### `tbl_info_nutricional_descricao`

1. **Nome:** `tbl_info_nutricional_descricao`
2. **Finalidade:** textos de rótulo + flags manuais de glúten e lactose.
3. **Colunas:** `ID_INFO_NUTRICIONAL`, `INGREDIENTES`, `ALERGENICOS`, `CONTEM_GLUTEN`, `CONTEM_LACTOSE`, validade, conservação, embalagem, peso líquido, observação, atualização.
4. **PK:** **ausente**.
5. **FKs:** nenhuma.
6. **Inferência:** 0..1 por info nutricional.
7. Sem índices.
8–10. Flags `enum('NAO','SIM')`; textos longos.
11. `ID_USUARIO_ATUALIZACAO`.
12. Nenhum `SITUACAO`.
13. `DATA_ATUALIZACAO`.
14. Nenhum.
15. Indireta.
16. Complemento da rotulagem.
17. Glúten/lactose manuais; sem catálogo de alergênicos; duplica `INFO_*` do cabeçalho.

### `tbl_info_nutricional_ingrediente`

1. **Nome:** `tbl_info_nutricional_ingrediente`
2. **Finalidade:** composição da rotulagem com % e nutrientes por linha (valor base + `QTDE_*` calculada).
3. **Colunas:** ids, código/nome, `QUANTIDADE`, `PERC_QUANTIDADE`, pares `CARBOIDRATO`/`QTDE_CARBOIDRATO` (e equivalentes), atualização.
4. **PK:** **ausente**.
5. **FKs:** nenhuma.
6. **Inferência:** info nutricional + ingrediente; nome denormalizado.
7. Sem índices. Sem ordem.
8–10. Tudo anulável; `float(9,2)`.
11. Usuário de atualização.
12. Sem situação.
13. `DATA_ATUALIZACAO`.
14. Nenhum.
15. Paralela à ficha, não compartilhada.
16. Direta.
17. Dois mundos de composição (ficha vs rótulo); sem ordem de declaração.

### `tbl_info_nutricional_tabela`

1. **Nome:** `tbl_info_nutricional_tabela`
2. **Finalidade:** linhas da tabela nutricional de apresentação (`TIPO`, `KCAL`, `KJ`, `PERC_VD`).
3. **PK:** **ausente**.
4–6. Sem FK; `TIPO` `varchar` — **inferência:** distinção 100 g / porção / VD.
7–10. `KCAL`, `KJ`, `PERC_VD` são **varchar**, não numéricos.
11. Usuário de atualização.
14. Nenhum.
16. Apresentação, não dossiê científico.
17. Perde precisão; `TIPO` sem enum.

### `tbl_info_nutricional_observacao`

1. **Nome:** `tbl_info_nutricional_observacao`
2. **Finalidade:** ambígua. `OBSERVACAO` é `int`, não texto.
3. **PK / FK / índices:** ausentes.
6. **Inferência:** código de observação pré-definido (lookup inexistente no DDL) ou flag.
17. Não usar como modelo; esclarecer na aplicação legado se necessário, sem ler dados.

---

## Escopo (empresa / usuário / fornecedor)

### `tbl_empresa`

Cadastro da organização (`ID_EMPRESA` PK). Ingrediente, produto, ficha e info nutricional carregam `ID_EMPRESA` anulável. Sem unique de CNPJ no DDL. Situação `CADASTRADO`/`CANCELADO`. Colunas de contato e responsável existem; não são reproduzidas aqui.

### `tbl_usuario`

Identidade de acesso. `TIPO` `CONSULTOR` | `EMPRESA`. Há coluna de senha no legado — **não reutilizar**. Relação com empresa via `tbl_usuario_empresa` (associativa **sem PK**).

### `tbl_usuario_permissao`

Flags `PER_EMPRESA`, `PER_FICHA_TECNICA`, `PER_ROTULAGEM_NUTRICIONAL`. Sem PK declarada (`ID_USUARIO` `NOT NULL` mas sem constraint PRIMARY no dump de constraints).

### `tbl_pessoa`

Cadastro de pessoa com `FORNECEDOR` `SIM`/`NAO`. **Não há coluna ligando pessoa/fornecedor a `tbl_ingrediente`.**

---

## Periferia excluída do detalhe

Selecionadas só por `ID_USUARIO`, `PRECO` ou `custo`: lançamentos e backups, POP, planos/mensalidade, recibos, log, centro de custo. Fora do domínio de ingredientes da Panne.

---

## Padrões transversais do legado

| Tema | O que o DDL mostra |
|---|---|
| Integridade referencial | Nenhuma FK no núcleo |
| Unicidade de negócio | Ausente |
| Precisão | `float` para massa, nutriente e dinheiro |
| Multiempresa | `ID_EMPRESA` anulável, sem unique composto |
| Exclusão | lógica via `SITUACAO` / `BLOQUEADO` |
| Versão | timestamps de atualização; sem `versao` |
| Denormalização | nome e código copiados nas linhas |
| Catálogo nutricional | colunas fixas, não entidades |
| Alergênicos | texto + flags manuais |
