# Investigação — 109F (SDDB6BA3CD × LPA39746B92A)

Leitura em produção (`lojadepaes:prod-20261102b`) dentro de `BEGIN TRANSACTION READ ONLY … ROLLBACK`, com `scripts/p109f-read.py`. Sem nome, e-mail ou texto de cliente.

1. A solicitação SDDB6BA3CD tem `cart_context` (1 linha: Rolled Bread de Pepperoni, 500 g × 1), foi criada em 03/11 às 14:24 para 04/11, e o pedido LPA39746B92A (vitrine, 14:26) é confirmado, pago, com produção em 04/11: mesma data, mesmo pão.
2. A quarta, 04/11, estava aberta na vitrine às 14:24: sem fechamento por período, antecedência mínima de 0 h, limite físico 15 com 0 pães comprometidos antes do pedido. A única ressalva é a ficha do pão sem `physical_units` (motivo `unknown_units`), que o calendário trata como selecionável ("dá para enviar o pedido nesta data").
3. A cliente chega à solicitação só pelo formulário "Precisa de outra data?", que o `BakeCalendar` monta abaixo do calendário na vitrine (`ProductShelf`), no checkout, no construtor de pão e no painel de fidelidade; o campo de data é livre, já vem preenchido com o dia escolhido no calendário, e o carrinho vai junto como `cart_context`.
4. Sim, é possível pedir por solicitação uma data que a vitrine vende: o formulário aparece sempre, e `create_date_request` só barra data passada ou fechada, sem conferir se a data está disponível para a seleção.
5. Proposta (não aplicada): quando a data do campo for selecionável no calendário (`isDaySelectable`), o formulário troca o envio por "Esta data está disponível: finalize o pedido", e `create_date_request` recusa data elegível para a seleção do carrinho, mantendo a solicitação para dias fechados, completos ou de hoje.
