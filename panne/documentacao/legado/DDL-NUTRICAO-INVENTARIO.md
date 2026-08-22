# Inventário — informação nutricional e rotulagem (legado)

Fonte: `information_schema` + `SHOW CREATE TABLE`. Sessão somente leitura + `ROLLBACK`. Sem linhas de negócio. Sem credenciais.

Composição nutricional é **paralela** à da ficha. Sem FK. Sem views/triggers. Cálculo vs armazenamento: o DDL guarda valores; **não prova** se foram calculados.

---

## `tbl_info_nutricional`

1. Cabeçalho do documento de rotulagem por produto.  
2. PK `ID_INFO_NUTRICIONAL`.  
3. Empresa, usuário, produto (id/código/nome), `PESO_TOTAL`, `PORCAO`, `RENDIMENTO_FINAL`, `MC_QUANTIDADE`, `MC_MEDIDA`, macros (`VALOR_ENERGETICO` … `SODIO`), `PESO_LIQUIDO_VENDA`, `VALIDADE`, `CONSERVACAO`, `EMBALAGEM`, `INGREDIENTES`, `ALERGENICOS`, `OBSERVACAO` (`int`), `RESPONSAVEL_TECNICO`, bloqueio, situação, cadastro.  
4. Massas `float(9,3)`; macros `float`; textos `varchar`/`longtext`; `OBSERVACAO` **int**.  
5–6. Quase tudo anulável.  
7–9. Só PK; sem FK.  
10. **Inferência:** empresa, produto; `MC_MEDIDA` → `tbl_medida`; filhos nas `tbl_info_nutricional_*`.  
11–12. `ID_EMPRESA`; `ID_USUARIO`.  
13. `BLOQUEADO`, `SITUACAO`.  
14. Só cadastro. Sem `DATA_ATUALIZACAO`.  
15. Sem versão.  
16. `PESO_TOTAL`, `PESO_LIQUIDO_VENDA`.  
17. `PORCAO`, `MC_QUANTIDADE`, `RENDIMENTO_FINAL`.  
18. Medida caseira por id inferido; unidade da porção ausente.  
19. `RENDIMENTO_FINAL`.  
20–21. Ausentes (estão na ficha).  
22. `PORCAO` + medida caseira.  
23. Macros em colunas fixas (não catálogo).  
24. `INGREDIENTES` texto livre **e** tabela filha.  
25. `ALERGENICOS` texto livre.  
26. Não neste cabeçalho (estão na descrição).  
27–28. Conservação, embalagem, validade, observação opaca.  
29. PDF **ausente no DDL**.

## `tbl_info_nutricional_ingrediente`

1. Segunda lista de ingredientes (composição do rótulo).  
2. **Sem PK.**  
3. `ID_INFO_NUTRICIONAL`, `ID_INGREDIENTE`, código/nome, `QUANTIDADE`, `PERCENTUAL`, `BASE_*` e `QTDE_*` para energia e macros.  
4. `float`.  
5. Tudo anulável.  
6. Sem defaults.  
7–9. Sem índice, sem unique, sem FK.  
10. **Inferência:** info nutricional + ingrediente.  
11. Via cabeçalho.  
12–15. Sem usuário, sem situação, sem versão.  
16–17. Quantidade e percentual.  
18. Ausente.  
19–22. Não.  
23. Nutrientes **por linha** (base + qtde) — sugere valor armazenado e valor escalado; **não comprovado**.  
24. Esta tabela **é** a lista estruturada.  
25–29. Não.

## `tbl_info_nutricional_descricao`

1. Textos de declaração + flags manuais de glúten/lactose.  
2. PK `ID_INFO_NUTRICIONAL_DESCRICAO`.  
3. `ID_INFO_NUTRICIONAL`, `INGREDIENTES`, `ALERGENICOS`, `CONTEM_GLUTEN`, `CONTEM_LACTOSE` (`enum F/T`), situação, cadastro.  
4. `longtext` + enum.  
7–9. Só PK.  
10. **Inferência:** 0..N descrições por info (sem unique).  
15. Duplicata textual do cabeçalho.  
24–26. Sim — declaração e flags **manuais**.  
27–29. Texto livre; sem PDF.

## `tbl_info_nutricional_tabela`

1. Linhas da tabela nutricional impressa.  
2. PK `ID_INFO_NUTRICIONAL_TABELA`.  
3. `ID_INFO_NUTRICIONAL`, `NUTRIENTE` (texto), `KCAL`, `KJ`, `PERC_VD` — os três **`varchar`**.  
7–9. Só PK; sem ordem explícita (só inserção).  
23. Nutriente como string, não catálogo.  
kcal/kJ/%VD como texto: arredondamento e formato **não validáveis pelo DDL** (questão normativa).

## `tbl_info_nutricional_observacao`

1. Observações ligadas ao documento.  
2. PK `ID_INFO_NUTRICIONAL_OBSERVACAO`.  
3. `ID_INFO_NUTRICIONAL`, `OBSERVACAO` **int**, situação, cadastro.  
O tipo int é opaco: catálogo? código? **Inferência fraca.**

## `tbl_medida`

Nome/plural. Sem conversão. Ligação inferida: `MC_MEDIDA`.

## Permissão e impressão

`tbl_usuario_permissao.PER_ROTULAGEM_NUTRICIONAL`. `tbl_usuario.DADOS_IMPRESSAO` — flag, não armazenamento de PDF.

`tbl_pop*` e `tbl_lancamento_docs` **não** são o PDF de rótulo.

## Ausências normativas (não tratar texto legado como regra)

Base 100 g vs porção vs rendimento; regra de arredondamento ANVISA; ordem legal de ingredientes; declaração automática de alergênicos; vigência de RDC; responsável técnico com registro profissional; snapshot de norma.
