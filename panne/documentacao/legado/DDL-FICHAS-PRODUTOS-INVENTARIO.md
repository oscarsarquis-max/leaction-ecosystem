# Inventário — produtos e fichas técnicas (legado)

Fonte: `information_schema` + `SHOW CREATE TABLE`.  
Sessão: `SET SESSION TRANSACTION READ ONLY` + `START TRANSACTION READ ONLY` + `ROLLBACK`.  
Nenhuma linha de negócio. Nenhuma escrita. Sem credenciais neste arquivo.

80 tabelas no schema. Views: nenhuma. Triggers: nenhum. **Nenhuma FK declarada** no núcleo. Ligações por `ID_*` são **inferência**.

Padrões: `SITUACAO` `CADASTRADO`/`CANCELADO`; `BLOQUEADO` `F`/`T`; massas e custos em `float`; charset `latin1` predominante. Só PK como índice, salvo quando indicado.

Para cada tabela: os 29 pontos pedidos. “Ausente no DDL” significa que o domínio pode esperar o conceito, mas o banco não o guarda.

---

## `tbl_produto`

1. Item de catálogo polimórfico da empresa (insumo e/ou ficha e/ou rotulagem).  
2. PK `ID_PRODUTO`.  
3. Empresa, usuário, `CODIGO_PRODUTO`, `PRODUTO`, grade `PRECO_CUSTO_*` / `VD_*` / `BC_*`, flags `USO_INGREDIENTE`, `USO_FICHA_TECNICA`, `USO_INFO_NUTRICIONAL`, cancelamento, bloqueio, situação, cadastro.  
4. Preços `float(9,2)`; flags `enum('F','T') NOT NULL`.  
5. Só PK e `USO_*` obrigatórios.  
6. Sem defaults além de NULL.  
7–8. Só PK. Sem unique de código por empresa.  
9. Nenhuma FK.  
10. **Inferência:** `ID_EMPRESA` → empresa; `USO_*` habilitam `tbl_ingrediente`, `tbl_ficha_tecnica`, `tbl_info_nutricional` via `ID_PRODUTO`.  
11. `ID_EMPRESA` anulável.  
12. `ID_USUARIO`, cadastro, cancelamento.  
13. `SITUACAO`, `BLOQUEADO`, `DATA_CANCELAMENTO`.  
14. Só `DATA_CADASTRO`.  
15. Sem versão.  
16–22. Sem pesos/rendimento/cocção/porção no produto.  
17. Sem quantidade técnica.  
18. Sem unidade.  
23–26. Não.  
27. Nome e código.  
28. Não.  
29. `DADOS_IMPRESSAO` está em `tbl_usuario`, não aqui. Sem tabela de PDF da ficha.

## `tbl_produto_preco`

1. Preço comercial por modalidade e tipo.  
2. PK `ID_PRODUTO_PRECO`.  
3. `ID_PRODUTO`, `MODALIDADE` (`VENDA DIRETA`/`VENDA BALCÃO`), `TIPO_PRECO` (`KG/UNIT`/`PORCAO`), custos/venda, situação, cadastro.  
4. `float(9,2)`.  
5–6. Quase tudo anulável.  
7–9. Só PK; sem FK.  
10. **Inferência:** `ID_PRODUTO` → produto.  
11–12. Empresa via produto; `ID_USUARIO_CADASTRO`.  
13–15. `SITUACAO`; sem vigência.  
16–26. Não (porção aqui é tipo de preço, não porção nutricional).  
27–29. Não.

## `tbl_ficha_tecnica`

1. Cabeçalho da receita: totais, rendimento, cocção, custos.  
2. PK `ID_FICHA_TECNICA`.  
3. Empresa, usuário, produto (id/código/nome), `NOME_RECEITA`, `RENDIMENTO`, `RENDIMENTO_RECEITA` (texto), custos, `TEMPO_PREPARO`, `TEMPO_COCCAO`, `PESO_PORCAO`, `PESO_COZIDO`, `FATOR_COCCAO`, `PERDA_GANHO`, `PESO_TOTAL`, `PESO_REAL`, `PESO_BRUTO_ING`, `PESO_LIQUIDO_ING`, `CUSTOS_DIVERSOS`, `CUSTOS_PRODUTOS`, atualização, bloqueio, situação, cadastro.  
4. Massas `float(9,3)`; custos `float(9,2)`; `RENDIMENTO` `int`; tempos `time`.  
5–6. Quase tudo anulável.  
7–9. Só PK; sem FK.  
10. **Inferência:** empresa, produto, usuário; filhos nas `tbl_ficha_tecnica_*`.  
11–12. `ID_EMPRESA`; vários `ID_USUARIO*`.  
13. `BLOQUEADO`, `SITUACAO`.  
14. Cadastro e `DATA_ATUALIZACAO`.  
15. Sobrescrita; sem número de versão; sem aprovação.  
16. Totais bruto/líquido/real/cozido/porção.  
17. `RENDIMENTO` como inteiro (unidades?).  
18. Unidade da linha **ausente** (peso implícito).  
19. `RENDIMENTO` e `RENDIMENTO_RECEITA`.  
20. `PERDA_GANHO`.  
21. `TEMPO_COCCAO`, `FATOR_COCCAO`, `PESO_COZIDO`.  
22. `PESO_PORCAO`; porções detalhadas em tabela filha.  
23–26. Não na ficha.  
27. Nome da receita e rendimento textual.  
28. No modo de preparo.  
29. Geração de documento **ausente no DDL**.

## `tbl_ficha_tecnica_ingrediente`

1. Linha da composição da ficha.  
2. PK `ID_FICHA_TECNICA_INGREDIENTE`.  
3. `ID_FICHA_TECNICA`, `ID_INGREDIENTE`, código/nome copiados, `PESO_BRUTO`, `PESO_LIQUIDO`, `FC`, `PESO_TOTAL`, custos, `DATA_CADASTRO`.  
4. `FC` `float(9,1)`; pesos `float(9,3)`; custos `float(9,2)`.  
5–9. Só PK; sem FK; sem ordem.  
10. **Inferência:** ficha + ingrediente.  
11. Via ficha.  
12. Não na linha.  
13. Sem `SITUACAO` na linha.  
14. Só cadastro.  
15. Snapshot de custo, não versão do insumo.  
16–17. Bruto, líquido, total.  
18. Ausente.  
19–22. Não (estão no cabeçalho).  
23–26. Não.  
27. Nome denormalizado.  
28–29. Não.

## `tbl_ficha_tecnica_modo_preparo`

1. Texto de preparo e observação.  
2. PK `ID_FICHA_TECNIA_MODO_PREPARO` (typo).  
3. `ID_FICHA_TECNICA`, `MODO_PREPARO`, `OBSERVACAO` `longtext`.  
4–9. Só PK; sem FK; sem ordem de etapas.  
10. **Inferência:** 0..N por ficha.  
15. Não.  
16–26. Não.  
27–28. Todo o conteúdo é texto livre.  
29. Não.

## `tbl_ficha_tecnica_porcao` e `tbl_ficha_tecnica_porcao_ingrediente`

1. Escala da ficha para um “cliente”/quantidade, com cópia das linhas.  
2. PKs próprias.  
3. Cabeçalho: `CLIENTE`, `QUANTIDADE`, `QUANTIDADE_ESCRITA`, `QUANTIDADE__`, totais, `RENDIMENTO_PORCAO`, situação, cadastro. Linha: ids, nome, `PESO`, bruto/líquido, situação.  
4. `float` / `varchar` / `int`.  
5. `SITUACAO` da linha é `NOT NULL`.  
7–9. Só PKs.  
10. **Inferência:** porção → ficha; linha → porção + ingrediente.  
15. Não é versão; é cópia.  
16–19. Pesos e rendimento da escala.  
18. Unidade ausente.  
23–29. Não.

## `tbl_medida`

Catálogo global de nome/plural de medida. PK `ID_MEDIDA`. Sem fator. **Inferência:** usada por `tbl_info_nutricional.MC_MEDIDA`, não pela ficha.

## `tbl_empresa` / `tbl_usuario` / `tbl_usuario_empresa` / `tbl_usuario_permissao`

Escopo e permissões `PER_FICHA_TECNICA` e `PER_ROTULAGEM_NUTRICIONAL`. Associativa usuário–empresa sem PK. Há colunas de acesso em `tbl_usuario` (incl. impressão `DADOS_IMPRESSAO`) — **não reutilizar** no modelo de identidade da Panne.

## Periferia documental (não é ficha/rótulo)

- `tbl_pop*` — inspeção/POP operacional (arquivos, fotos, treinamento). Não é ficha técnica nem rótulo.  
- `tbl_lancamento_docs` / backup — anexo financeiro.  
Nenhuma tabela de PDF de ficha ou rótulo no DDL.

## O que o domínio espera e o DDL não tem

Ordem de declaração; baker’s %; farinha como base; aprovação; histórico de versão da ficha; unidade na linha; vínculo ficha↔info nutricional; responsável técnico formal; evidência de cálculo.
