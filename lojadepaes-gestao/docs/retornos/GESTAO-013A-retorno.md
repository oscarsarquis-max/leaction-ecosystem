# GESTAO-013A — retorno

Branch `feat/gestao-013a-rendimento`, a partir de `540ef6c9`. A aba Rendimento deixa de pedir quantidade e unidade. As unidades saem da massa e do modelo de perdas, e o que fica gravado acompanha essa conta. Sem migração.

## Checklist

1. **Feito.** `docs/evidence/gestao-013a-local/rendimento-1280.png` e `rendimento-390.png`. O Pão de Canela local, forma enriquecida e 500 g, mostra processo e cocção lado a lado, o percentual num campo estreito com "%" dentro, e a origem no selo. A cocção está em "referência · forma enriquecida 400–600 g". O processo foi mudado à mão para 8: o selo virou "ajuste manual", o motivo "Forno da casa" apareceu ali, e "Voltar ao padrão" desfaz. "Peças de 568 g" fica numa linha, com "divida a massa assim" embaixo. As contas seguem 2 unidades e 5.981 g. Os campos antigos Quantidade e Unidade saíram. Nenhuma das duas capturas tem rolagem horizontal.

2. **Feito.** `padroes-perdas-1280.png` e `padroes-perdas-390.png`. O formato usa o mesmo rótulo da aba Rendimento: "Forma enriquecida", "Assadeira", "Qualquer formato". Na coluna Fonte, o link é "Busby's Bakery" e o `title` guarda o título inteiro.

3. **Feito.** As quatro provas do item 0, em `docs/evidence/gestao-013a-local/`.
   - O editor do Pão com calda agrupa por função. A Massa com açúcar (a base leva açúcar) fica em Massa, e o açúcar da calda fica em Cobertura. `editor-funcoes-1280.png` e `editor-funcoes-390.png`.
   - A aba Revisar usa o cartão com recuo, os avisos na lista de avisos, e o Publicar fica desabilitado até marcar "Publicar mesmo assim, sem fermento". O script marcou a caixa, o botão habilitou, e ao desmarcar voltou a ficar desabilitado. A captura é o estado desabilitado: `revisar-1280.png` e `revisar-390.png`.
   - O aviso de sal na mesma tela é "Sal total 5,4 % (2,0 % da massa-base + 3,4 % desta receita)."
   - O sal clássico a 2 % fica com confiança média. `test_sal_a_2_porcento_fica_media_e_nao_baixa` exige média mesmo quando o modelo disse baixa ou alta e a linha não foi descrita. Quem chama é o `_acertar`, com `classico=sal_classico(linha.get("nome"), percentual)`.

4. **Feito.** Backend 278 testes. Frontend 83. Imagem `lojadepaes-gestao:013a-20261106`, só o `gestao-api` recriado. O Alembic continua em `0009_perdas`. `https://lojadepaes.com.br` responde 200. `https://gestao.lojadepaes.com.br/` responde 200 e serve `index-Cqm0WdHx.js`, SHA-256 `f8dd36b1aea9a2a786e0ad8cb9385682785caa466dddf51d9d38a0e0f605046f`, igual ao pacote da imagem. A Loja não mudou: media_assets 16/0/0, product_variants 16/6/6, products 16/35/6, showcase_slots 10/16/0.

5. **Feito.** Este arquivo e as capturas entram no mesmo commit. A regra de SSH aberta para este ciclo foi fechada; ficaram as 29 que já existiam. 80 e 443 seguem públicos.

A imagem anterior, para voltar, é `lojadepaes-gestao:013-20261106`.
