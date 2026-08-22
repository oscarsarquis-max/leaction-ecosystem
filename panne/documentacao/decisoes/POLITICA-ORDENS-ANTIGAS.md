# Adoção de política em ordens antigas

Comando `production.order.policy_adopt`.

Permitido somente quando:

- a ordem está `released` ou `on_hold`
- não há política congelada (ausente ou não congelada)
- não há pesagem, consumo, etapa iniciada, rendimento ou ocorrência
- o ator tem a permissão
- política completa e motivo são informados

O comando congela a política, gera hash e evento `execution.policy_adopted`. É idempotente. Não cria fatos retroativos de execução.
