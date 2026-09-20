# Integração financeira futura — ActionHub

A Loja de Pães **gestiona pedidos** e guarda o estado financeiro informado pela integração. Não processa cartão, não cria cobrança e não chama o Hub nesta etapa.

O Hub, no ecossistema, hoje orquestra checkout Mercado Pago e webhooks S2S para satélites (`app_registry`, `webhook_secret`, outbox JWT). Esse contrato é do Hub para apps como o Inove; **não** está confirmado para a Loja de Pães. Nada abaixo inventa URL, evento, assinatura ou status externos.

## Já implementado (interno)

- `payment_records`: tentativas por pedido, `provider='actionhub'`, referência externa opcional única no provedor, chave de idempotência opcional única, `expected_cents` + `BRL`, estados internos `pending|paid|failed|cancelled|partially_refunded|refunded|unknown`, valores pagos/estornados anuláveis (desconhecido ≠ zero), datas de confirmação e sincronização.
- `payment_integration_events`: deduplicação `(provider, external_event_id)`. Evento sem associação confiável não deve alterar o financeiro (fica `received` / `ignored`).
- Sem estado financeiro agregado em `orders`. Quitação: `order_is_financially_settled` soma `pago − estorno` só de registros com valores conhecidos na moeda do pedido. Uma linha `paid` não basta se o valor não cobre o total.
- Sem webhook público, sem cliente HTTP, sem mudança financeira a partir do frontend ou do painel admin (consulta apenas).
- Confirmar, cancelar ou concluir um pedido **não** altera `payment_records`.

## Pendente (contrato real do ActionHub)

- Autenticação e assinatura das mensagens.
- Identificadores externos, tipos de evento e ordem (fora de ordem, retentativas).
- Mapeamento dos status do Hub para `financial_status`.
- Idempotência da *solicitação* de cobrança versus a do registro interno.
- Se a reserva da fornada espera `paid` ou permanece na confirmação operacional.
- Consulta de confirmação (pull) versus só push.
- Campos não sensíveis permitidos em metadados (hoje não há JSONB de payload).

Não armazenar cartão, CVV, tokens de acesso, segredos de assinatura nem payload completo indiscriminado.
