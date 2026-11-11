# GESTAO-016 — retorno

Base: `feat/gestao-015-receita` (`bc6ffd71`). Branch: `feat/gestao-016-cultura-viva`. Sem migração. O Gestão continua no mesmo host da Loja.

## Checklist

1. **Feito.** `git apply --check` do patch `GESTAO-016-cultura-viva-alinhamento.patch` terminou limpo, e o `git apply` entrou só em `Produtos.tsx` e `fluxo.css`. O teste `Produtos.form.test.tsx` passou: o nome acessível continua contendo "Cultura viva", e o texto novo é "Usa uma porção do preparo anterior: levain, massa madre, PFF".

2. **Feito.** Capturas em `docs/evidence/gestao-016-local/`: `produto-levain-1280.png` e `produto-levain-390.png`. Componente e Cultura viva marcados. A caixa fica sob o texto "Componente", o título é "Cultura viva" e a explicação começa na mesma coluna.

3. **Feito.** Componente vendido por peso, ou sem peso final, sai na comanda como massa: "Levain · 250 g". "un" e "Peças" ficam para o produto com peso final por unidade. O título "Quantidade" da tabela fica à direita, como os valores. Evidência: `comanda-a4.png` e `comanda-a4.pdf` (A4). O teste `test_comanda_de_componente_por_peso_mostra_a_massa` confirma `por_unidade` falso, sem "Peças" e massa "250 g". O pão com peso final por unidade continua com "Peças".

4. **Feito.** Conferência, sem dado de teste.

   1. **Barra lateral.** Não é defeito. As capturas do 015 foram feitas com a API interceptada, e o mock de `/fluxo` devolvia só Receitas e Produtos. Em produção, para `admin@lojadepaes.com.br` na Boulangerie, o fluxo calculado no banco tem as 5 etapas nesta ordem, todas com endereço: Entradas, Ingredientes, Produtos, Receitas, Produção. Nada foi alterado no menu.

   2. **"Levain usa Levain".** Foi erro forçado para a captura. O mock respondia 422 com `linha: 1` em qualquer gravação daquele modo. A farinha é a primeira linha enviada, então o texto caía nela, embora o grupo Inóculo apareça primeiro na tela. Com `cultura_viva` e a linha de inóculo, editar a farinha grava 200 (`test_editar_a_farinha_com_inoculo_salva`). O índice segue a ordem enviada, não a ordem visual dos grupos: um 422 na linha 3 marca o inóculo e não a farinha (`receitas015.test.tsx`).

   3. **Levain da Boulangerie.** Existe o produto "Levain (fermento natural líquido)": componente, não é venda, unidade de venda kg, `cultura_viva` desmarcado. A receita existe, situação rascunho, 0 linhas, sem peso final.

5. **Feito.** Imagem `lojadepaes-gestao:016-20261111`, sem Alembic. Só o `gestao-api` foi recriado. `https://gestao.lojadepaes.com.br/` responde 200 e serve `index-zxBlet51.js`, SHA-256 `d3b877e48c81978ba34bc5be0a94d24d957f325fc291a1595daea4b796820b84`, igual ao pacote da imagem. `https://lojadepaes.com.br` responde 200, com o JavaScript da vitrine que já estava no ar. A contagem da Loja ficou igual: `media_assets` 17/0/0, `product_variants` 16/6/6, `products` 16/35/6, `showcase_slots` 10/16/0. O Alembic continua em `0012_cultura_viva`. A porta 22 aberta neste ciclo foi fechada. O grupo do Hub não foi alterado.

A imagem anterior, para voltar, é `lojadepaes-gestao:015-20261111`. O banco não mudou.
