# GESTAO-013 — retorno

Branch `feat/gestao-013-perdas`, a partir de `b78faf39`. A perda deixa de ser um campo solto e deixa de ser decisão do Gigio. O valor que a tela mostra vem de uma medição, do padrão da casa ou da referência, e o ajuste manual só entra com motivo.

## O que ficou de fora do zero

A coluna antiga `perda_percentual` continua. Só valor **maior que zero** foi copiado para a perda de processo, com origem `manual` e o motivo "Valor informado antes do modelo de perdas." Zero não é decisão do padeiro: a receita segue na resolução (medido, padrão, referência). No banco de produção não havia perda maior que zero, então nenhuma receita ficou travada em manual.

`peso_unidade_g` é o peso final por unidade. Não nasceu coluna duplicada.

## Checklist

1. **Feito.** Dump em `/opt/lojadepaes-gestao/backups/gestao-pre013.dump` (97.910 bytes) antes da migração `0009_perdas`, que só adiciona. `carregar-perdas`: 7 inseridas, versão 1; a segunda execução, 0 alteradas e 7 iguais. O `carregar-catalogo` não rodou.
2. **Feito.** Backend 277 testes. Frontend 83. Os nove novos cobrem a função da linha, a publicação sem fermento, as três contas, a prioridade, o Gigio e a carga com isolamento.
3. **Feito.** Dezoito capturas em `docs/evidence/gestao-013-local/`, nas larguras 320, 390, 768, 960, 1280 e 1440. Nenhuma com rolagem horizontal nem controle abaixo da altura. O Pão de Canela local ficou em forma enriquecida, 500 g: processo "5 % · padrão da casa", cocção "12 % · referência (forma enriquecida, 400–600 g)", peça crua de 568 g, 2 unidades na massa de 1.400 g e 5.981 g para 10 unidades. O "ver de onde vem" abre a faixa, a fonte e a nota. Padrões › Perdas mostra a semente e a referência.
4. **Feito.** Imagem `lojadepaes-gestao:013-20261106`. `https://lojadepaes.com.br` responde 200. `https://gestao.lojadepaes.com.br/` responde 200 e serve `index-bdr2MPsd.js`, SHA-256 `43590e4584c35955a2389248671ea89fcf1ac76978cababfd419918124d86afa`, igual ao pacote local. A semente de 5 % está na `boulangerie` ("informado pelo Oscar, 06/11"). Sete referências. Nenhuma outra organização. A Loja não mudou: media_assets 16/0/0, product_variants 16/6/6, products 16/35/6, showcase_slots 10/16/0, antes e depois.
5. **Feito.** Este arquivo e as capturas entram no mesmo commit. A regra de SSH aberta para este ciclo foi fechada; ficaram as 29 que já existiam. 80 e 443 seguem públicos.

A imagem anterior, para voltar, é `lojadepaes-gestao:012b-20261106`.
