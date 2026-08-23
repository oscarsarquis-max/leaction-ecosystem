# ADR — Modo operacional do padeiro

A UI operacional vive em `/producao/ordens/:orderId/executar`. O backend permanece soberano: permissões, estados, tolerâncias, conversões, conclusão e idempotência.

- Sem planejamento administrativo completo
- Sem estoque, custos, balança, offline, PWA, WebSocket ou IA
- Catálogos vêm de `GET /production/catalog`
- A projeção operacional vem de `GET /orders/{id}/execution`
- Polling de 20 s só nesta tela, pausado se a aba estiver oculta ou o formulário estiver em edição
