# GESTAO-014B — retorno

Base: `feat/gestao-016-cultura-viva` (`ca2664e3`). Branch: `feat/gestao-014b-comanda`. Sem migração. O Gestão continua no mesmo host da Loja.

## Checklist

1. **Feito.** Testes só da área. `tests/test_comanda_014b.py`: 2 passaram. O bloco de 100 programadas + 12 da Loja fica com 112 unidades e a farinha e o inóculo na escala de 112. As duas ordens continuam no banco e as duas ficam `impressa`. A resposta não contém `NOME-SINTETICO` nem `sintetico@example.invalid`, e lista `LPA39746B92A` (2) e `SD10X9` (10). `36.648 g` vira `36,65 kg`; `7,34 g` vira `7,3 g`. No frontend, `comanda014b.test.tsx`: 1 passou. O HTML tem as referências e não tem nome nem e-mail.

2. **Feito.** Capturas em `docs/evidence/gestao-014b-local/`: `calendario-1280.png`, `calendario-390.png`, `dia-1280.png`, `dia-390.png`. Uma linha por produto, soma 112, e em cinza "100 programadas · 12 da Loja". No Dia o produto está em destaque, "Peças de 568 g" e a massa não quebram no meio, e o ⋯ é o botão de ícone.

3. **Feito.** `comanda-a4.pdf` e `comanda-80mm.pdf`. Os dois trazem "112 un (100 programadas + 12 da Loja)", `LPA39746B92A (2)`, `SD10X9 (10)` e "Levain · inóculo". No A4 são duas páginas, as duas com conteúdo: a segunda começa no bloco seguinte e na pesagem, que não coube na primeira. No 80 mm é uma página só, na altura do conteúdo.

4. **Feito.** Imagem `lojadepaes-gestao:014b-20261111`, sem Alembic. Só o `gestao-api` foi recriado. `https://gestao.lojadepaes.com.br/` responde 200 e serve `index-ByS3QUpC.js`, SHA-256 `e22b6ac113fa6f3bffc165b5106e0c23f9c2f42c34dff2fa57abe1705b48c57b`, igual ao pacote da imagem. `https://lojadepaes.com.br` responde 200, com o JavaScript da vitrine que já estava no ar (`index-BPpk5tJI.js`). A contagem da Loja ficou igual antes e depois: `media_assets` 17/0/0, `product_variants` 16/6/6, `products` 16/35/6, `showcase_slots` 10/16/0. O Alembic continua em `0012_cultura_viva`. A porta 22 aberta neste ciclo foi fechada. O grupo do Hub não foi alterado.

5. **Feito.** O commit desta branch leva o código, este retorno, as capturas e os PDFs.

A imagem anterior, para voltar, é `lojadepaes-gestao:016-20261111`. O banco não mudou.

A caixa de "Cultura viva" perdeu a margem padrão do navegador, para alinhar com o texto de "Componente".
