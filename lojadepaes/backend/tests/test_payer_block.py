"""A cobrança da Loja não leva o pagador estendido. O CPF fica no formulário do Pay."""

from pathlib import Path

from app.domain.actionhub_client import checkout_request_body

TODAY = [
    "app_id",
    "order_reference",
    "payment_request_id",
    "amount_cents",
    "currency",
    "description",
    "method",
    "customer",
    "return_origin",
    "return_to",
]


def _body(**extra):
    base = dict(
        app_id="lojadepaes",
        order_reference="LP77B815537C",
        payment_request_id="req-1",
        amount_cents=7000,
        description="Pedido Loja de Pães LP77B815537C",
        customer_email="ana@example.test",
        customer_name="Ana Souza",
        return_origin="https://lojadepaes.com.br",
        return_to="/pedido/LP77B815537C",
    )
    base.update(extra)
    return checkout_request_body(**base)


def test_card_and_pix_never_carry_payer():
    card = _body(method="card")
    pix = _body(method="pix")
    assert list(card) == TODAY
    assert list(pix) == TODAY
    assert "payer" not in card
    assert "payer" not in pix


def test_loja_does_not_build_an_extended_payer():
    root = Path(__file__).resolve().parents[1] / "app" / "domain"
    client = (root / "actionhub_client.py").read_text(encoding="utf-8")
    orders = (root / "storefront_orders.py").read_text(encoding="utf-8")
    for source in (client, orders):
        assert "build_card_payer" not in source
        assert "PAY_SEND_" not in source
        assert "security.js" not in source
    assert "payer=" not in client
    assert 'prepared["payer"]' not in orders
