# Cadastro de produtos — Loja de Pães

Área: https://lojadepaes.com.br/admin/produtos (mesmo login do cabeçalho). Em desenvolvimento local: http://127.0.0.1:5175/admin/produtos.

## Onde escrever o resumo da vitrine

No editor, logo abaixo de **Nome do pão**, use **Descrição curta da vitrine**.

Esse texto é o resumo comercial do pão: sabor, textura e características. Ele aparece **abaixo do nome** no cartão em **Nossos pães** e também no detalhe do produto. Limite: 280 caracteres. Salvar rascunho ou republicar atualiza a vitrine sem novo build.

Não é receita técnica nem rótulo. Não invente características: escreva o que o pão realmente é.

## Texto da foto: acessibilidade e legenda visível

São dois campos distintos:

1. **Texto alternativo da imagem** — obrigatório para publicar. Serve a leitores de tela (`alt`). O navegador **não** mostra esse texto abaixo da fotografia.
2. **Legenda da foto — aparece na vitrine** — opcional, até 200 caracteres. Este é o texto visível imediatamente abaixo da foto no cartão e no detalhe. Se estiver vazio, a vitrine não reserva espaço nem inventa uma frase.

O editor não copia o texto alternativo para a legenda. Se quiser reutilizar, use **Usar também como legenda**.

## Ingredientes básicos (composição)

A lista **Ingredientes básicos** do cadastro é a composição comercial do pão, na ordem em que o cliente deve lê-la. Ela aparece no cartão da página inicial com o rótulo **Ingredientes** e também no detalhe. Listas longas no cartão começam com um resumo e o controle **Ver ingredientes**.

Essa lista não é rotulagem nutricional, receita técnica nem vínculo com o Panne.

## Passo a passo

1. Entre pelo acesso compacto do cabeçalho (`admin@lojadepaes.com.br`).
2. Abra **Produtos** e **Novo produto**, ou o pão já cadastrado.
3. Preencha **Nome do pão** e, em seguida, **Descrição curta da vitrine**.
4. A **descrição detalhada** é opcional e só aparece na página do produto, abaixo do resumo. Não é preciso repetir o mesmo texto.
5. Envie a foto destacada (JPEG, PNG ou WebP, até 8 MB). Preencha o **texto alternativo da imagem** e, se quiser texto visível, a **legenda da foto**.
6. Liste os **ingredientes básicos** na ordem em que o cliente deve lê-los (composição comercial, sem quantidades).
7. Crie as opções de venda: peso (500 g, 800 g) ou unidade/pacote. O preço é da opção inteira, no formato `24,90`.
8. **Salvar rascunho** guarda sem aparecer na vitrine. **Publicar produto** exige foto, texto alternativo, descrição curta da vitrine, ingredientes e ao menos uma opção ativa com preço. A legenda visível não é obrigatória. O pão publicado ocupa a primeira posição livre das dez da vitrine.
9. Na página principal, **Nossos pães** mostra as posições preenchidas. Se a vitrine já tiver dez pães, um novo publicado fica no catálogo, mas fora da vitrine, até você trocar uma posição. Se ficar temporariamente sem venda, desmarque a disponibilidade: ele permanece visível, sem compra.
10. **Apagar** remove rascunho e arquivado, da lista e do editor, e não pode ser desfeito. Publicado não apaga: primeiro arquive. Cadastro que já entrou em pedido também não apaga.

## Receita completa e rotulagem — fora deste cadastro

A receita completa (proporções, preparo, rendimento, custos) e a rotulagem nutricional ficarão em **panne.ia.br**, em uma etapa futura. Não cadastre isso aqui e não espere um vínculo automático com o Panne para preencher a vitrine.

A seção **Configuração de produção** (agrupamento da agenda) é só um agrupamento interno para contar bases distintas na fornada. Não é a receita do Panne. Não é obrigatória para salvar o resumo, a foto ou os preços. Pedidos, quando forem abertos, ainda podem exigir esse agrupamento na operação de produção — isso não bloqueia o cadastro editorial.

O editor reorganiza ingredientes, variações e a barra de publicação em telas estreitas (a partir de 320 px). Subir/descer e o envio de foto por seletor de arquivo precisam continuar usáveis no celular, sem depender de arrastar.

Rascunhos e arquivados nunca aparecem para o cliente. Pedidos e pagamentos permanecem desligados nesta fase protegida.
