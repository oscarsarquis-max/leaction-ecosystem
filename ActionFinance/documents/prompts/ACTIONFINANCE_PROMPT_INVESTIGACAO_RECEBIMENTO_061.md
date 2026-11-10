# ACTIONFINANCE — Prompt 061 · Investigação: o que chega de cada recebimento (somente leitura)

## Objetivo
O detalhe do recebimento integrado está fraco e mostra **"Pagador não identificado"** numa venda da Loja de Pães que tem cliente conhecido (exemplo: R$ 70,00, criada em 27/10, atualizada em 10/11, "Checkout avulso por valor", card, Mercado Pago). Antes de redesenhar a tela, descobrir **quais dados existem em cada etapa** e onde se perdem. **Não corrigir nada.**

## Regras
- Somente leitura. Não alterar código, banco, Spider, Loja nem Hub. Não chamar endpoint que grave nada.
- Dados pessoais: no relato, mostrar só o **nome do campo**, se vem preenchido ou não e um exemplo **mascarado** (ex.: `j***@g***.com`, `***.123.***-**`). Nunca o valor real.
- Sem deploy e sem testes.

## Passos
1. **No Finance (banco de produção, só leitura):** para esse recebimento, listar todos os campos gravados e o payload bruto guardado, se houver. Marcar o que está vazio.
2. **Contrato 1.4 (`LIST_EXTERNAL_PAYMENTS`):** no código do Finance e na documentação do contrato, listar os campos que a resposta pode trazer. Destacar pagador (nome, e-mail, documento), pedido da loja, itens, parcelas, taxa, valor líquido, data de liberação e ID da transação no Mercado Pago.
3. **Mapeamento do Finance:** apontar onde cada campo da resposta é lido. Algum campo chega e é descartado? Por que "Pagador não identificado" (campo ausente na resposta ou identidade técnica no lugar do contato, como dizia a lacuna do relato 028)?
4. **Do lado do Pay, só leitura de código** (sem alterar o Hub): o que `LIST_PAYMENT_TRANSACTIONS` devolve para uma venda da Loja, e se ela conhece pagador, número do pedido e taxa do Mercado Pago.

## Entrega
`documents/reviews/ACTIONFINANCE_REV_INVESTIGACAO_RECEBIMENTO_061.md`, com uma tabela **Dado | Na Loja/Pay | Na resposta da Spider | Gravado no Finance | Exibido na tela**, cobrindo: pagador, pedido, itens, método e parcelas, taxa, líquido, data de liberação, ID MP e situação.
Fechar com uma conclusão de 5 linhas: o que dá para corrigir só no Finance e o que depende do Pay ou da Spider.

Copiar este prompt para `documents/prompts/`. Commit e push só dos dois arquivos.

## Aceite
Tabela completa com evidência, nenhum dado pessoal exposto e nada alterado.
