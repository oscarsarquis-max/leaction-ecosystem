# GESTAO-015 — retorno

Base: `feat/gestao-014a-foto` (`2c4865e9`). Branch: `feat/gestao-015-receita`. O Gestão em produção está no mesmo host da Loja, não na instância do Hub.

A receita grava o rascunho sozinha, a observação fica na linha e na comanda, e uma cultura viva (levain, massa madre, PFF) pode usar uma porção do preparo anterior. Isso não é ciclo. Qualquer outra auto-referência, e qualquer ciclo entre produtos diferentes, continua recusado.

## Checklist

1. **Feito.** Dump `/opt/lojadepaes-gestao/backups/gestao-pre015.dump` (153.503 bytes, SHA-256 `38f7edddbf15af41a0caa8eeb268f1961ca0c64224ba6ac82922a2ada7a201f8`, modo 600) antes do Alembic. `pg_restore --list`: 243 linhas. A migração `0011_produto_foto -> 0012_cultura_viva` só adiciona `produtos.cultura_viva` (falso por omissão) e aceita a função `inoculo` na linha. Em produção o Alembic ficou em `0012_cultura_viva`. O catálogo rodou no deploy e não mudou nada: 0 inseridos, 0 alterados, 71 iguais.

2. **Feito.** Backend 294 testes, incluindo `backend/tests/test_inoculo.py`. Com cultura viva, a linha de inóculo do próprio Levain entra e o custo fica em R$ 0,005 por grama no caso farinha 100 g a R$ 0,01/g, água 100 g sem custo e inóculo 50 g. Sem a marca, a mesma linha responde 422 `ciclo_receita`. Auto-referência que não é inóculo responde 422. Levain → Pão X → Levain responde 422 com a frase "Levain usa Pão X, que usa Levain." Inóculo maior ou igual à massa responde "O inóculo não pode ser maior que a massa." A comanda traz "Inóculo: … de Levain do preparo anterior" e a observação. O teste antigo de ciclo continua valendo. Frontend 89 testes, incluindo `receitas015.test.tsx` (gravação, erro na linha, confirmação ao sair, observação na tabela e na comanda) e `Produtos.form.test.tsx`.

3. **Feito.** Capturas em `docs/evidence/gestao-015-local/`, em 1280 e 390.
   - Grupo Inóculo, com "Levain · porção do preparo anterior": `inoculo-1280.png`, `inoculo-390.png`.
   - Indicador "Salvando…": `salvando-1280.png`, `salvando-390.png`.
   - "Tudo salvo": `salvo-1280.png`, `salvo-390.png`.
   - Erro na linha e "1 linha não salva · ver": `erro-linha-1280.png`, `erro-linha-390.png`.
   - Observação aberta na tabela, embaixo da linha: `observacao-1280.png`, `observacao-390.png`.
   - Comanda com a observação "peneirar" e "Inóculo: 50 g de Levain do preparo anterior": `comanda-1280.png`, `comanda-390.png`.
   - Adendo, Editar produto do Levain: `produto-levain-1280.png`, `produto-levain-390.png`. Componente marcado, "Cultura viva" visível, recuada e marcada, texto "Levain, massa madre, PFF", sem "Unidade de venda".

4. **Feito.** Imagem `lojadepaes-gestao:015-20261111`. Só o `gestao-api` foi recriado; `infra-api-1`, `infra-caddy-1` e `infra-db-1` seguem de pé desde antes deste ciclo. `https://gestao.lojadepaes.com.br/` responde 200 e serve `index-tiN3sXbE.js`, SHA-256 `27e97ade80a9b6936eeec0f2c2b45692f3f7b701f43ab31065e626655e0a3838`, igual ao pacote da imagem. `https://lojadepaes.com.br` responde 200, com o JavaScript da vitrine que já estava no ar. A contagem da Loja ficou igual antes e depois: `media_assets` 17/0/0, `product_variants` 16/6/6, `products` 16/35/6, `showcase_slots` 10/16/0. Nenhum dado de teste em produção. Nenhuma baixa de estoque.

5. **Feito.** Este arquivo e as capturas entram no mesmo commit. A porta 22 aberta neste ciclo, só para esta máquina, foi fechada: o host ficou sem regra de SSH. O grupo do Hub não foi alterado. 80 e 443 seguem públicos.

A imagem anterior, para voltar, é `lojadepaes-gestao:014a-20261107`. O banco volta pelo dump. A coluna nova pode ficar: a imagem anterior não a usa.

## Adendo — formulário Novo/Editar produto

No mesmo ciclo, sem migração além da `0012` e sem dado de teste.

1. **Feito.** "Cultura viva (usa uma porção do preparo anterior)" fica logo abaixo de Componente, recuada, e só aparece com Componente marcado. Embaixo, em cinza: "Levain, massa madre, PFF". Grava `produto.cultura_viva`. Desmarcar Componente esconde a caixa e não apaga o valor. Evidência: `produto-levain-1280.png` e `produto-levain-390.png`.

2. **Feito.** "Unidade de venda" só aparece com Venda marcada. No Levain, só componente, ela não está na tela. O valor guardado continua no estado e segue no envio. O teste `Produtos.form.test.tsx` cobre os dois: só Componente esconde a unidade de venda; desmarcar Componente esconde "Cultura viva" e, ao marcar de novo, a caixa volta marcada.
