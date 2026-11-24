"""Pedido da combo (M8): casa + parceiro numa transação, preços, entrega, decisões e sincronização."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from app.core.config import get_settings
from app.domain.orders import cancel_order
from app.domain.recipe_bases import create_recipe_base
from app.marketplace.models import PartnerOrder
from app.models.email_outbox import EmailOutbox
from app.models.enums import EditorialStatus
from app.models.orders import Order, OrderItem
from app.models.payments import PaymentRecord
from app.models.production import ProductionBatch
from app.models.products import Product, ProductVariant
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.db_fixtures import NEW_ORDER_ADDRESS
from tests.test_marketplace import _abrir, _aprovar, _csrf, _ligar, _vincular
from tests.test_storefront import _next_wednesday

pytestmark = pytest.mark.usefixtures("admin_client")

BREAD_PRICE = 2490
ITEM_PRICE = 3200
ITEM_FREIGHT = 900
FEE = 250
HOUSE_FREIGHT = 800


@pytest.fixture
def market(db: Session) -> Session:
    db.execute(text("TRUNCATE marketplace.partners RESTART IDENTITY CASCADE"))
    db.commit()
    return db


def _variante(db: Session) -> ProductVariant:
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa combo")
    product = Product(
        name="Pão da combo",
        slug=f"pao-combo-{uuid4().hex[:8]}",
        short_description="crosta firme",
        recipe_base_id=base.id,
        featured_image_alt="pão",
        editorial_status=EditorialStatus.PUBLISHED.value,
        is_available=True,
    )
    db.add(product)
    db.flush()
    variant = ProductVariant(
        product_id=product.id,
        display_name="500 g",
        presentation_type="weight",
        net_weight_grams=500,
        physical_units=1,
        price_cents=BREAD_PRICE,
        currency="BRL",
        is_active=True,
    )
    db.add(variant)
    db.commit()
    return variant


def _face(bread_unit: int = BREAD_PRICE, bread_qty: int = 2, item_qty: int = 2) -> int:
    return bread_qty * bread_unit + HOUSE_FREIGHT + item_qty * ITEM_PRICE + ITEM_FREIGHT


def _cenario(admin_client: TestClient, market: Session, **produto_extra) -> dict:
    csrf = login(admin_client)
    variant = _variante(market)
    slug = market.scalar(select(Product.slug).where(Product.id == variant.product_id))
    created, portal = _abrir(admin_client, csrf, f"c-{uuid4().hex[:6]}", "Queijaria Combo")
    _vincular(admin_client, csrf, created["id"], "queijos", "none")
    extra = {"delivery_days": 0, **produto_extra}
    product_id = _aprovar(admin_client, csrf, portal, slug, **extra)
    combo = portal.post(
        "/api/v1/partner/combos",
        json={"partner_product_id": product_id, "house_product_slug": slug, "reason": "O pão realça o queijo."},
        headers=_csrf(portal.csrf),
    )
    assert combo.status_code == 201, combo.text
    combo_id = combo.json()["id"]
    review = admin_client.post(
        f"/api/v1/admin/marketplace/combos/{combo_id}/review",
        json={"decision": "approve", "note": ""},
        headers=_csrf(csrf),
    )
    assert review.status_code == 200, review.text
    return {
        "csrf": csrf,
        "variant": variant,
        "slug": slug,
        "partner": created,
        "portal": portal,
        "product_id": product_id,
        "combo_id": combo_id,
        "day": _next_wednesday(),
    }


def _payload(cen: dict, *, quoted: int | None = None, key: str | None = None, **extra) -> dict:
    body = {
        "variant_id": str(cen["variant"].id),
        "bread_quantity": 2,
        "item_quantity": 2,
        "requested_date": cen["day"],
        "preferred_time": "",
        "customer_name": "Ana Cliente",
        "customer_email": "ana@example.com",
        "customer_phone": "",
        "idempotency_key": key or f"combo-{uuid4().hex}",
        "quoted_cents": _face() if quoted is None else quoted,
        **NEW_ORDER_ADDRESS,
    }
    body.update(extra)
    return body


def _pedir(client: TestClient, cen: dict, **kwargs):
    return client.post(f"/api/v1/combos/{cen['combo_id']}/orders", json=_payload(cen, **kwargs))


def _partner_orders(cen: dict) -> list[dict]:
    response = cen["portal"].get("/api/v1/partner/orders", headers=_csrf(cen["portal"].csrf))
    assert response.status_code == 200, response.text
    return response.json()


def test_chave_desligada_todas_as_rotas_novas_dao_404(db: Session, admin_client: TestClient, monkeypatch):
    del db
    _ligar(monkeypatch, False)
    combo = uuid4()
    assert admin_client.get(f"/api/v1/combos/{combo}").status_code == 404
    assert admin_client.post(f"/api/v1/combos/{combo}/orders", json={}).status_code == 404
    assert admin_client.get(f"/api/v1/combos/pedido/{uuid4()}?t=x").status_code == 404
    csrf = login(admin_client)
    price = admin_client.patch(
        f"/api/v1/admin/marketplace/combos/{combo}/price",
        json={"house_unit_price_cents": 2000},
        headers=_csrf(csrf),
    )
    assert price.status_code == 404
    order = uuid4()
    assert admin_client.get("/api/v1/partner/orders").status_code == 404
    for action in ("accept", "delivered"):
        assert admin_client.post(f"/api/v1/partner/orders/{order}/{action}").status_code == 404
    assert admin_client.post(f"/api/v1/partner/orders/{order}/refuse", json={"reason": "x"}).status_code == 404


def test_resumo_da_combo_traz_variacoes_e_so_combo_aprovada(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    cen = _cenario(admin_client, market)
    resumo = admin_client.get(f"/api/v1/combos/{cen['combo_id']}")
    assert resumo.status_code == 200, resumo.text
    body = resumo.json()
    assert body["id"] == cen["combo_id"]
    assert body["bread"]["slug"] == cen["slug"]
    assert body["bread"]["variants"] == [{"id": str(cen["variant"].id), "name": "500 g", "price_cents": BREAD_PRICE}]
    assert body["product"]["price_cents"] == ITEM_PRICE
    assert body["delivery"]["freight_cents"] == ITEM_FREIGHT
    assert body["house_unit_price_cents"] is None
    assert set(body["partner"]) == {"brand_name", "brand_slug", "highlight_hex", "logo_url"}
    assert "fee_cents" not in str(body)
    pausa = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{cen['partner']['id']}/pause", headers=_csrf(cen["csrf"])
    )
    assert pausa.status_code == 200
    assert admin_client.get(f"/api/v1/combos/{cen['combo_id']}").status_code == 404
    assert admin_client.get(f"/api/v1/combos/{uuid4()}").status_code == 404
    assert admin_client.get("/api/v1/combos/nao-e-uuid").status_code == 404


def test_cria_pedido_da_combo_e_reenvio_e_idempotente(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    cen = _cenario(admin_client, market)
    key = f"combo-{uuid4().hex}"
    first = _pedir(admin_client, cen, key=key)
    assert first.status_code == 200, first.text
    created = first.json()
    assert set(created) == {"combo_ref", "token"}
    second = _pedir(admin_client, cen, key=key)
    assert second.status_code == 200, second.text
    assert second.json()["combo_ref"] == created["combo_ref"]

    market.expire_all()
    orders = market.scalars(select(Order)).all()
    assert len(orders) == 1
    order = orders[0]
    assert str(order.combo_ref) == created["combo_ref"]
    assert order.delivery_fee_cents == HOUSE_FREIGHT
    assert order.combo_fee_cents == FEE
    assert order.subtotal_cents == 2 * BREAD_PRICE
    assert order.total_cents == 2 * BREAD_PRICE + HOUSE_FREIGHT + FEE
    assert order.status == "confirmed" and order.holds_capacity is True
    assert order.submit_idempotency_key == key
    items = market.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    assert len(items) == 1 and items[0].quantity == 2
    assert items[0].unit_price_cents == BREAD_PRICE and items[0].line_total_cents == 2 * BREAD_PRICE
    payment = market.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id)).one()
    assert payment.expected_cents == order.total_cents

    parts = market.scalars(select(PartnerOrder)).all()
    assert len(parts) == 1
    part = parts[0]
    assert part.house_order_id == order.id and str(part.combo_ref) == created["combo_ref"]
    assert part.public_reference.startswith("PO-")
    assert part.item_quantity == 2 and part.item_cents == 2 * ITEM_PRICE
    assert part.freight_cents == ITEM_FREIGHT and part.fee_cents == FEE
    assert part.status == "submitted"
    assert part.product_name == "Queijo coalho" and part.house_product_name == "Pão da combo"
    assert part.customer_name == "Ana Cliente"
    assert "Rua das Fornadas, 100" in part.address_line and "Fortaleza/CE" in part.address_line

    kinds = {row.kind for row in market.scalars(select(EmailOutbox).where(EmailOutbox.kind.like("combo_order_%")))}
    assert kinds == {"combo_order_customer", "combo_order_partner"}
    customer = market.scalars(select(EmailOutbox).where(EmailOutbox.kind == "combo_order_customer")).one()
    assert f"/combo/pedido/{created['combo_ref']}?t=" in customer.body
    assert customer.to_address == "ana@example.com"
    notice = market.scalars(select(EmailOutbox).where(EmailOutbox.kind == "combo_order_partner")).one()
    assert part.public_reference in notice.subject
    assert "Rua das Fornadas" not in notice.body

    view = admin_client.get(f"/api/v1/combos/pedido/{created['combo_ref']}", params={"t": created["token"]})
    assert view.status_code == 200, view.text
    body = view.json()
    assert body["combo_ref"] == created["combo_ref"]
    assert body["requested_date"] == cen["day"]
    assert body["house"]["public_reference"] == order.public_reference
    assert body["house"]["status"] == "confirmed"
    assert body["house"]["amount_cents"] == order.total_cents
    assert body["house"]["status_label"]
    assert f"/pedido/{order.public_reference}?token=" in body["house"]["order_url"]
    assert len(body["partners"]) == 1
    seen = body["partners"][0]
    assert seen["amount_cents"] == 2 * ITEM_PRICE + ITEM_FREIGHT - FEE
    assert seen["status"] == "submitted"
    assert seen["brand"]["brand_name"] == "Queijaria Combo"
    assert body["total_cents"] == _face()
    assert "fee" not in str(body)
    assert admin_client.get(f"/api/v1/combos/pedido/{created['combo_ref']}", params={"t": "errado"}).status_code == 401
    assert admin_client.get(f"/api/v1/combos/pedido/{created['combo_ref']}").status_code == 401
    assert admin_client.get(f"/api/v1/combos/pedido/{uuid4()}", params={"t": created["token"]}).status_code == 404

    listed = _partner_orders(cen)
    assert [row["id"] for row in listed] == [str(part.id)]
    mine = listed[0]
    assert mine["fee_cents"] == FEE and mine["item_cents"] == 2 * ITEM_PRICE
    assert mine["freight_cents"] == ITEM_FREIGHT and mine["item_quantity"] == 2
    assert mine["combo_ref"] == created["combo_ref"]
    assert mine["requested_date"] == cen["day"]
    assert mine["accept_deadline"] is None


def test_preco_do_pao_na_combo_vale_para_a_casa_e_para_o_cliente(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    cen = _cenario(admin_client, market)
    url = f"/api/v1/admin/marketplace/combos/{cen['combo_id']}/price"
    for ruim in (0, -5):
        assert admin_client.patch(url, json={"house_unit_price_cents": ruim}, headers=_csrf(cen["csrf"])).status_code == 400
    assert admin_client.patch(url, json={"house_unit_price_cents": "2000"}, headers=_csrf(cen["csrf"])).status_code == 422
    assert admin_client.patch(url, json={"house_unit_price_cents": 20.5}, headers=_csrf(cen["csrf"])).status_code == 422
    assert admin_client.patch(url, json={}, headers=_csrf(cen["csrf"])).status_code == 422
    assert admin_client.patch(url, json={"house_unit_price_cents": 2000}).status_code in {401, 403}
    assert (
        admin_client.patch(
            f"/api/v1/admin/marketplace/combos/{uuid4()}/price",
            json={"house_unit_price_cents": 2000},
            headers=_csrf(cen["csrf"]),
        ).status_code
        == 404
    )
    ok = admin_client.patch(url, json={"house_unit_price_cents": 2000}, headers=_csrf(cen["csrf"]))
    assert ok.status_code == 200, ok.text
    assert ok.json()["house_unit_price_cents"] == 2000
    resumo = admin_client.get(f"/api/v1/combos/{cen['combo_id']}").json()
    assert resumo["house_unit_price_cents"] == 2000
    vitrine = admin_client.get(f"/api/v1/marketplace/public/breads/{cen['slug']}").json()
    assert vitrine["combos"][0]["house_unit_price_cents"] == 2000
    publica = admin_client.get(f"/api/v1/marketplace/public/partners/{cen['partner']['brand_slug']}").json()
    assert publica["combos"][0]["house_unit_price_cents"] == 2000
    minha = cen["portal"].get("/api/v1/partner/combos", headers=_csrf(cen["portal"].csrf)).json()
    assert minha[0]["house_unit_price_cents"] == 2000

    preco_vitrine = admin_client.post(
        f"/api/v1/combos/{cen['combo_id']}/orders", json=_payload(cen, quoted=_face(BREAD_PRICE))
    )
    assert preco_vitrine.status_code == 409
    feito = _pedir(admin_client, cen, quoted=_face(2000))
    assert feito.status_code == 200, feito.text
    market.expire_all()
    order = market.scalars(select(Order)).one()
    assert order.subtotal_cents == 4000
    assert order.total_cents == 4000 + HOUSE_FREIGHT + FEE
    item = market.scalars(select(OrderItem)).one()
    assert item.unit_price_cents == 2000

    limpo = admin_client.patch(url, json={"house_unit_price_cents": None}, headers=_csrf(cen["csrf"]))
    assert limpo.status_code == 200 and limpo.json()["house_unit_price_cents"] is None


def test_valor_de_face_diferente_responde_409_sem_criar_nada(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    cen = _cenario(admin_client, market)
    recusa = _pedir(admin_client, cen, quoted=_face() + 1)
    assert recusa.status_code == 409
    assert recusa.json()["code"] == "price_changed"
    assert recusa.json()["current_cents"] == _face()
    market.expire_all()
    assert market.scalars(select(Order)).all() == []
    assert market.scalars(select(PartnerOrder)).all() == []


def test_frete_zero_do_parceiro_e_quantidades_de_1_a_10(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    cen = _cenario(admin_client, market, freight_cents=0, price_cents=1000)
    face = 3 * BREAD_PRICE + HOUSE_FREIGHT + 4 * 1000
    feito = _pedir(admin_client, cen, quoted=face, bread_quantity=3, item_quantity=4)
    assert feito.status_code == 200, feito.text
    market.expire_all()
    part = market.scalars(select(PartnerOrder)).one()
    assert part.item_cents == 4000 and part.freight_cents == 0
    for campo in ("bread_quantity", "item_quantity"):
        for ruim in (0, 11):
            resposta = _pedir(admin_client, cen, **{campo: ruim})
            assert resposta.status_code == 422, (campo, ruim)
    market.expire_all()
    assert len(market.scalars(select(Order)).all()) == 1


def test_entrega_do_parceiro_cidade_bairro_e_prazo(market: Session, admin_client: TestClient, monkeypatch):
    _ligar(monkeypatch, True)
    fora = _cenario(admin_client, market, delivery_cities=["Recife"])
    recusa = _pedir(admin_client, fora)
    assert recusa.status_code == 422, recusa.text
    assert "entrega" in recusa.json()["detail"]

    acento = _cenario(admin_client, market, delivery_cities=["Fortaléza"])
    assert _pedir(admin_client, acento).status_code == 200

    bairro = _cenario(admin_client, market, delivery_cities=[], delivery_districts=["ALDEOTA"])
    assert _pedir(admin_client, bairro).status_code == 200

    sem_restricao = _cenario(admin_client, market, delivery_cities=[], delivery_districts=[], delivery_cep_prefixes=["60"])
    assert _pedir(admin_client, sem_restricao).status_code == 200

    outro_bairro = _cenario(admin_client, market, delivery_cities=[], delivery_districts=["Meireles"])
    assert _pedir(admin_client, outro_bairro).status_code == 422

    longe = _cenario(admin_client, market, delivery_days=30)
    cedo = _pedir(admin_client, longe)
    assert cedo.status_code == 422, cedo.text
    assert "30 dias" in cedo.json()["detail"]
    market.expire_all()
    assert len(market.scalars(select(Order)).all()) == 3
    assert len(market.scalars(select(PartnerOrder)).all()) == 3


def test_endereco_completo_e_data_valida_como_o_pedido_normal(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    cen = _cenario(admin_client, market)
    sem_endereco = _pedir(
        admin_client,
        cen,
        delivery_street="",
        delivery_number="",
        delivery_district="",
        delivery_city="",
        delivery_state="",
        delivery_postal_code="",
    )
    assert sem_endereco.status_code == 422
    retirada = _pedir(admin_client, cen, fulfillment_modality="pickup")
    assert retirada.status_code == 422
    passada = _pedir(admin_client, {**cen, "day": "2020-01-01"})
    assert passada.status_code in {409, 422}
    pao_alheio = _pedir(admin_client, {**cen, "variant": _variante(market)})
    assert pao_alheio.status_code == 422
    market.expire_all()
    assert market.scalars(select(Order)).all() == []
    assert market.scalars(select(PartnerOrder)).all() == []


def test_prazo_da_loja_vira_prazo_do_parceiro(market: Session, admin_client: TestClient, monkeypatch):
    _ligar(monkeypatch, True)
    cen = _cenario(admin_client, market)
    zone = ZoneInfo(get_settings().bakery_timezone)
    year, month, day = (int(part) for part in cen["day"].split("-"))
    available = datetime(year, month, day, 12, 0, tzinfo=zone)
    cedo = available - timedelta(days=1, hours=6)
    tarde = available - timedelta(hours=20)
    for code, deadline in (("combo-tarde", tarde), ("combo-cedo", cedo)):
        market.add(
            ProductionBatch(
                code=f"{code}-{uuid4().hex[:4]}",
                planned_start_at=available - timedelta(hours=5),
                breads_available_at=available,
                order_deadline_at=deadline,
                capacity_units=10,
                status="open",
            )
        )
    market.add(
        ProductionBatch(
            code=f"combo-cancelada-{uuid4().hex[:4]}",
            planned_start_at=available - timedelta(hours=5),
            breads_available_at=available,
            order_deadline_at=available - timedelta(days=5),
            capacity_units=10,
            status="cancelled",
        )
    )
    market.commit()
    assert _pedir(admin_client, cen).status_code == 200
    market.expire_all()
    part = market.scalars(select(PartnerOrder)).one()
    assert part.accept_deadline == cedo.astimezone(UTC)
    listed = _partner_orders(cen)[0]
    assert datetime.fromisoformat(listed["accept_deadline"]) == cedo


def test_parceiro_aceita_recusa_e_entrega(market: Session, admin_client: TestClient, monkeypatch):
    _ligar(monkeypatch, True)
    cen = _cenario(admin_client, market)
    portal = cen["portal"]
    for _ in range(3):
        assert _pedir(admin_client, cen).status_code == 200
    market.expire_all()
    ids = [str(row.id) for row in market.scalars(select(PartnerOrder).order_by(PartnerOrder.created_at))]
    aceito, recusado, outro = ids

    cedo = portal.post(f"/api/v1/partner/orders/{aceito}/delivered", headers=_csrf(portal.csrf))
    assert cedo.status_code == 409
    ok = portal.post(f"/api/v1/partner/orders/{aceito}/accept", headers=_csrf(portal.csrf))
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "accepted"
    de_novo = portal.post(f"/api/v1/partner/orders/{aceito}/accept", headers=_csrf(portal.csrf))
    assert de_novo.status_code == 409
    recusa_tardia = portal.post(
        f"/api/v1/partner/orders/{aceito}/refuse", json={"reason": "mudei de ideia"}, headers=_csrf(portal.csrf)
    )
    assert recusa_tardia.status_code == 409
    entregue = portal.post(f"/api/v1/partner/orders/{aceito}/delivered", headers=_csrf(portal.csrf))
    assert entregue.status_code == 200 and entregue.json()["status"] == "delivered"
    assert portal.post(f"/api/v1/partner/orders/{aceito}/delivered", headers=_csrf(portal.csrf)).status_code == 409

    for motivo in ("", "   "):
        sem = portal.post(
            f"/api/v1/partner/orders/{recusado}/refuse", json={"reason": motivo}, headers=_csrf(portal.csrf)
        )
        assert sem.status_code == 400
    assert portal.post(f"/api/v1/partner/orders/{recusado}/refuse", json={}, headers=_csrf(portal.csrf)).status_code == 400
    assert _partner_orders(cen)[0]["status"] in {"submitted", "delivered"}
    recusa = portal.post(
        f"/api/v1/partner/orders/{recusado}/refuse", json={"reason": "Sem estoque"}, headers=_csrf(portal.csrf)
    )
    assert recusa.status_code == 200, recusa.text
    assert recusa.json()["status"] == "refused" and recusa.json()["refuse_reason"] == "Sem estoque"
    assert portal.post(f"/api/v1/partner/orders/{recusado}/accept", headers=_csrf(portal.csrf)).status_code == 409
    assert portal.post(f"/api/v1/partner/orders/{recusado}/delivered", headers=_csrf(portal.csrf)).status_code == 409

    assert portal.post(f"/api/v1/partner/orders/{outro}/accept").status_code == 403
    assert portal.post(f"/api/v1/partner/orders/{uuid4()}/accept", headers=_csrf(portal.csrf)).status_code == 404

    market.expire_all()
    assert market.scalars(select(Order)).first().status == "confirmed"
    estados = {str(row.id): row.status for row in market.scalars(select(PartnerOrder))}
    assert estados == {aceito: "delivered", recusado: "refused", outro: "submitted"}


def test_parceiro_so_age_nos_proprios_pedidos(market: Session, admin_client: TestClient, monkeypatch):
    _ligar(monkeypatch, True)
    cen = _cenario(admin_client, market)
    assert _pedir(admin_client, cen).status_code == 200
    market.expire_all()
    pedido = str(market.scalars(select(PartnerOrder)).one().id)
    csrf = login(admin_client)
    _criado, outro = _abrir(admin_client, csrf, f"o-{uuid4().hex[:6]}", "Outra Marca")
    assert outro.get("/api/v1/partner/orders", headers=_csrf(outro.csrf)).json() == []
    assert outro.post(f"/api/v1/partner/orders/{pedido}/accept", headers=_csrf(outro.csrf)).status_code == 404
    assert (
        outro.post(
            f"/api/v1/partner/orders/{pedido}/refuse", json={"reason": "não é meu"}, headers=_csrf(outro.csrf)
        ).status_code
        == 404
    )
    assert outro.post(f"/api/v1/partner/orders/{pedido}/delivered", headers=_csrf(outro.csrf)).status_code == 404
    market.expire_all()
    assert market.scalars(select(PartnerOrder)).one().status == "submitted"


def test_prazo_vencido_expira_o_parceiro_e_o_pao_segue(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    cen = _cenario(admin_client, market)
    portal = cen["portal"]
    for _ in range(2):
        assert _pedir(admin_client, cen).status_code == 200
    market.expire_all()
    rows = list(market.scalars(select(PartnerOrder).order_by(PartnerOrder.created_at)))
    vencido, aceito = str(rows[0].id), str(rows[1].id)
    combo_ref = str(rows[0].combo_ref)
    assert portal.post(f"/api/v1/partner/orders/{aceito}/accept", headers=_csrf(portal.csrf)).status_code == 200
    market.execute(
        text("UPDATE marketplace.partner_orders SET accept_deadline = now() - interval '1 hour' WHERE id = :id"),
        {"id": vencido},
    )
    market.execute(
        text("UPDATE marketplace.partner_orders SET accept_deadline = now() - interval '1 hour' WHERE id = :id"),
        {"id": aceito},
    )
    market.commit()

    visto = {row["id"]: row for row in _partner_orders(cen)}
    assert visto[vencido]["status"] == "expired"
    assert visto[aceito]["status"] == "accepted"
    recusa = portal.post(
        f"/api/v1/partner/orders/{vencido}/refuse", json={"reason": "tarde"}, headers=_csrf(portal.csrf)
    )
    assert recusa.status_code == 409
    assert portal.post(f"/api/v1/partner/orders/{vencido}/accept", headers=_csrf(portal.csrf)).status_code == 409

    market.expire_all()
    assert {str(row.id): row.status for row in market.scalars(select(PartnerOrder))} == {
        vencido: "expired",
        aceito: "accepted",
    }
    assert {order.status for order in market.scalars(select(Order))} == {"confirmed"}

    # Leitura do cliente também expira (lazy) e não mexe no pedido da casa.
    market.execute(
        text("UPDATE marketplace.partner_orders SET status = 'submitted', accept_deadline = now() - interval '1 minute' WHERE id = :id"),
        {"id": vencido},
    )
    market.commit()
    order = market.scalars(select(Order).where(Order.combo_ref == rows[0].combo_ref)).first()
    assert order is not None
    token = _token_do_cliente(order)
    view = admin_client.get(f"/api/v1/combos/pedido/{combo_ref}", params={"t": token})
    assert view.status_code == 200, view.text
    assert view.json()["partners"][0]["status"] == "expired"
    assert view.json()["house"]["status"] == "confirmed"


def _token_do_cliente(order: Order) -> str:
    from app.domain.storefront_orders import email_access_token

    return email_access_token(get_settings(), order)


def test_cancelamento_da_casa_cancela_o_parceiro_na_proxima_leitura(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    cen = _cenario(admin_client, market)
    portal = cen["portal"]
    for _ in range(3):
        assert _pedir(admin_client, cen).status_code == 200
    market.expire_all()
    parts = list(market.scalars(select(PartnerOrder).order_by(PartnerOrder.created_at)))
    pendente, aceito, entregue = (str(row.id) for row in parts)
    assert portal.post(f"/api/v1/partner/orders/{aceito}/accept", headers=_csrf(portal.csrf)).status_code == 200
    assert portal.post(f"/api/v1/partner/orders/{entregue}/accept", headers=_csrf(portal.csrf)).status_code == 200
    assert portal.post(f"/api/v1/partner/orders/{entregue}/delivered", headers=_csrf(portal.csrf)).status_code == 200

    for row in parts:
        if str(row.id) in {pendente, aceito}:
            cancel_order(market, row.house_order_id, "Cliente desistiu", actor_ref="admin:test")
    market.commit()

    visto = {row["id"]: row["status"] for row in _partner_orders(cen)}
    assert visto == {pendente: "cancelled", aceito: "cancelled", entregue: "delivered"}
    cancelado = portal.post(f"/api/v1/partner/orders/{pendente}/accept", headers=_csrf(portal.csrf))
    assert cancelado.status_code == 409
    assert portal.post(f"/api/v1/partner/orders/{aceito}/delivered", headers=_csrf(portal.csrf)).status_code == 409

    market.expire_all()
    cancelada = market.scalars(select(PartnerOrder).where(PartnerOrder.id == parts[0].id)).one()
    assert cancelada.status == "cancelled"
    house = market.scalars(select(Order).where(Order.id == cancelada.house_order_id)).one()
    token = _token_do_cliente(house)
    view = admin_client.get(f"/api/v1/combos/pedido/{cancelada.combo_ref}", params={"t": token})
    assert view.status_code == 200, view.text
    assert view.json()["house"]["status"] == "cancelled"
    assert view.json()["partners"][0]["status"] == "cancelled"


def test_migracao_m8_desce_e_sobe(test_engine, db: Session):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    del db
    ini = Path(__file__).resolve().parents[2] / "database" / "alembic.ini"
    config = Config(str(ini))
    config.set_main_option("script_location", str(ini.parent / "migrations"))
    revision = "d8b3f1a65c92"
    try:
        command.downgrade(config, "c4e8b2a91f70")
        inspector = inspect(test_engine)
        assert "partner_orders" not in inspector.get_table_names(schema="marketplace")
        assert "combo_ref" not in {col["name"] for col in inspector.get_columns("orders")}
        assert "house_unit_price_cents" not in {
            col["name"] for col in inspector.get_columns("product_combos", schema="marketplace")
        }
    finally:
        command.upgrade(config, "head")
    inspector = inspect(test_engine)
    assert "partner_orders" in inspector.get_table_names(schema="marketplace")
    assert {"combo_ref", "combo_fee_cents"} <= {col["name"] for col in inspector.get_columns("orders")}
    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == revision
