"""Versões de retorno que preservam a confirmação financeira.

O Hub de retorno grava o pedido pago e um único evento para a Loja na mesma
persistência. A Loja publicada em prod-20261027f aplica esse evento. Reverter o
Hub para o processo que marca o cartão pago sem essa outbox não é retorno.
"""

HUB_FINANCIAL_RETURN = "hub-confirm-durable-20261028"
LOJA_FINANCIAL_RETURN = "lojadepaes:prod-20261027f"
FORBIDDEN_HUB_RETURN = "hub-card-paid-without-outbox"
# Extraído em 2026-10-28T15:27:52Z da imagem em execução. CRLF. O git HEAD do mesmo arquivo é LF e o texto coincide.
LOJA_27F_IMAGE_ID = "sha256:8c5b48336a55f3e078c7d8dc8b605bad3484d80df25ff51a96f43ff90ee47141"
LOJA_27F_WEBHOOK_SHA256 = "ad8147299228bc11d7bb06e58b2572c14aa63736b475145bf1c8df7876a6ad74"
# Cópias locais ainda não publicadas. O processo pm2 gateway-api não contém estes arquivos.
HUB_RETURN_MP_WEBHOOKS_SHA256 = "3983720d936e7bbd46d102587d46c8d455efe6016ef79ebd61221e26fbd6ac1d"
HUB_RETURN_AMOUNT_CHECKOUT_SHA256 = "28c75227ff0a75d5dc54e86922987d02ba89be5a7ac7923d5ee6adfc0d50819b"


def durable_card_event(
    *,
    outbox_id: str,
    hub_order_id: str,
    order_reference: str,
    paid_amount_cents: int,
    mp_payment_id: str,
    app_id: str = "lojadepaes",
) -> dict:
    """Payload único que o Hub de retorno enfileira. Não abre outra cobrança."""
    payload = {
        "source": "amount_checkout",
        "event_type": "PAYMENT_CONFIRMED",
        "financial_status": "paid",
        "order_id": hub_order_id,
        "order_reference": order_reference,
        "amount_cents": paid_amount_cents,
        "currency": "BRL",
        "mp_payment_id": mp_payment_id,
        "mp_status": "approved",
        "method": "card",
        "paid_amount_cents": paid_amount_cents,
        "provider_approved_at": "2026-10-27T17:10:26-03:00",
    }
    return {
        "iss": "leaction-hub",
        "app_id": app_id,
        "outbox_id": outbox_id,
        "event_type": "PAYMENT_CONFIRMED",
        "payload": payload,
    }
