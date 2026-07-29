---
title: PRD Checkout e Pagamentos
tipo: PRD
---

# Visao do produto

Este PRD descreve o fluxo de checkout e cobranca online para pedidos no ecommerce B2B.
O objetivo e reduzir abandono de carrinho e garantir confirmacao de pagamento de forma confiavel.

## Jornada de checkout

O comprador revisa o carrinho, escolhe endereco de entrega, seleciona metodo de pagamento
(cartao, boleto ou PIX) e confirma o pedido. Apos a autorizacao, o sistema emite o recibo
e dispara a reserva de estoque.

### Metodos de pagamento

Cartao de credito com captura em duas etapas, PIX com QR Code expiravel e boleto bancario
com vencimento em tres dias uteis. Falhas de gateway devem permitir retry sem duplicar cobranca.

## Regras de negocio

Idempotencia por `payment_intent_id`, estorno parcial, antifraude basico e conciliacao
diaria com o provedor de pagamento. Metricas: taxa de conversao do checkout e tempo medio
ate confirmacao do pagamento.
