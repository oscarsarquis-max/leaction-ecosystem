"""Pagador enviado na cobrança de cartão. O Pix fica sem esse bloco."""

from types import SimpleNamespace

from app.domain.actionhub_client import build_card_payer, checkout_request_body

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


def test_card_without_payer_matches_today_and_pix_never_carries_payer():
    card = _body(method="card", payer=None)
    pix = _body(method="pix", payer={"first_name": "Ana"})
    assert list(card) == TODAY
    assert list(pix) == TODAY
    assert "payer" not in card
    assert "payer" not in pix


def test_payer_from_order_with_address_and_cpf():
    order = SimpleNamespace(
        customer_name="Ana Souza",
        customer_email="Ana@Example.test",
        customer_phone="(11) 98765-4321",
        delivery_postal_code="01310-100",
        delivery_street="Paulista",
        delivery_number="1000",
        delivery_district="Bela Vista",
        delivery_city="São Paulo",
        delivery_state="sp",
    )
    payer = build_card_payer(order, cpf="529.982.247-25")
    assert payer["first_name"] == "Ana"
    assert payer["last_name"] == "Souza"
    assert payer["email"] == "ana@example.test"
    assert payer["identification"] == {"type": "CPF", "number": "52998224725"}
    assert payer["phone"] == {"area_code": "11", "number": "987654321"}
    assert payer["address"]["zip_code"] == "01310100"
    assert payer["address"]["federal_unit"] == "SP"
    body = _body(method="card", payer=payer)
    assert body["payer"]["address"]["street_name"] == "Paulista"


def test_payer_without_address_and_without_cpf_drops_invalid_phone():
    order = SimpleNamespace(
        customer_name="Ana",
        customer_email="ana@example.test",
        customer_phone="123",
        delivery_postal_code=None,
        delivery_street=None,
        delivery_number=None,
        delivery_district=None,
        delivery_city=None,
        delivery_state=None,
    )
    payer = build_card_payer(order)
    assert payer == {"first_name": "Ana", "email": "ana@example.test"}
    assert "address" not in payer
    assert "identification" not in payer
    assert "phone" not in payer
