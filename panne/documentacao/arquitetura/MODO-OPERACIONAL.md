# Modo operacional

Rota: `/producao/ordens/:orderId/executar`.

Fluxo da tela: batelada → pesagem → etapas → consumo e ocorrências → rendimento → encerramento → ficha.

Leituras: `GET /orders/{id}/execution` e `GET /catalog`. Comandos usam as rotas já existentes da API com `Idempotency-Key`, `X-Correlation-Id` e `If-Match`.
