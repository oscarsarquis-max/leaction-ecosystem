"""Projeção das trilhas. Não altera regra de estado."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.domain.order_tracks import date_request_tracks, order_tracks, track_labels
from app.domain.orders import new_public_reference
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.managerial import OpsPushDelivery
from app.models.orders import Order, OrderStatusHistory
from app.models.payments import PaymentRecord
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login

assert admin_client
from tests.db_fixtures import priced_catalog


def _order(**fields):
    base = dict(
        status="submitted",
        fulfillment_modality="delivery",
        production_started_at=None,
        delivery_confirmed_at=None,
        production_local_date=None,
        proposed_production_date=None,
        cancellation_reason=None,
        delivery_street="Rua das Fornadas",
        delivery_number="100",
        delivery_complement="",
        delivery_district="Aldeota",
        delivery_city="Fortaleza",
        delivery_state="CE",
        delivery_postal_code="60150160",
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _date(status="pending", desired=None):
    return SimpleNamespace(status=status, desired_date=desired or date(2026, 11, 18))


def _tracks(order, bucket, **kwargs):
    return order_tracks(order, bucket, unresolved_adaptation=kwargs.pop("unresolved_adaptation", False), **kwargs)


CASES = []


def _keep(name, projection, **expect):
    row = (name, projection, expect)
    CASES.append(row)
    return row


def test_matriz_das_trilhas():
    today = date(2026, 10, 30)
    yesterday = date(2026, 10, 29)
    rows = [
        _keep(
            "submitted sem cobrança",
            _tracks(_order(), "no_charge"),
            commercial=("open", "Aberto", "open"),
            payment=("no_charge", "Após aceite", "none", "A cobrança abre depois do aceite"),
            production=("not_started", "Não iniciada", "none"),
            delivery=("awaiting", "Aguardando", "none", "Entrega exige confirmação da equipe"),
            action=("accept", "Avaliar e aceitar", True),
        ),
        _keep(
            "submitted com adaptação",
            _tracks(
                _order(),
                "no_charge",
                unresolved_adaptation=True,
                adaptation_text="sem gergelim na crosta, por favor, e sem sementes",
            ),
            action=("resolve_adaptation", "Resolver adaptação", True),
            attention="Adaptação pedida: sem gergelim na crosta, por favor, e sem sementes",
        ),
        _keep(
            "confirmed aguardando",
            _tracks(_order(status="confirmed"), "awaiting"),
            commercial=("accepted", "Aceito", "accepted"),
            payment=("awaiting", "Aguardando", "none", "Cobrança aberta, cliente ainda não pagou"),
            action=("open", "Abrir", False),
        ),
        _keep(
            "processando",
            _tracks(_order(status="confirmed"), "processing"),
            payment=("processing", "Processando", "none", "Pagamento encaminhado ao provedor, ainda pendente"),
            action=("open", "Abrir", False),
        ),
        _keep(
            "pago",
            _tracks(_order(status="confirmed"), "paid"),
            payment=("paid", "Pago", "paid", None),
            action=("start_production", "Iniciar produção", True),
        ),
        _keep(
            "desconhecido",
            _tracks(_order(status="confirmed"), "unknown"),
            payment=("unknown", "Verificando", "warn", "Pagamento não confirmado; a consulta ao provedor não respondeu"),
            action=("check_payment", "Ver pagamento", True),
            attention="Pagamento não confirmado pelo provedor",
        ),
        _keep(
            "falhou",
            _tracks(_order(status="confirmed"), "failed"),
            payment=("failed", "Falhou", "warn", "Falha de pagamento"),
            action=("check_payment", "Ver pagamento", True),
        ),
        _keep(
            "sem valor",
            _tracks(_order(status="confirmed"), "no_amount"),
            payment=("no_amount", "Sem valor", "none", "Pedido sem valor a pagar"),
            action=("start_production", "Iniciar produção", True),
        ),
        _keep(
            "em produção pago",
            _tracks(_order(status="in_production"), "paid"),
            production=("in_production", "Em produção", "production"),
            action=("confirm_delivery", "Confirmar entrega", True),
        ),
        _keep(
            "em produção sem pagamento",
            _tracks(_order(status="in_production"), "no_charge"),
            payment=("no_charge", "Sem cobrança", "none", "Nenhuma cobrança iniciada"),
            action=("confirm_delivery", "Confirmar entrega", True),
        ),
        _keep(
            "ready legado",
            _tracks(_order(status="ready"), "paid"),
            production=("ready", "Pronto", "open", "Pronto — aguardando confirmação de entrega"),
            action=("confirm_delivery", "Confirmar entrega", True),
        ),
        _keep(
            "entregue",
            _tracks(_order(status="completed", delivery_confirmed_at=datetime.now(UTC)), "paid"),
            commercial=("accepted", "Aceito", "accepted"),
            production=("done", "Concluída", "none"),
            delivery=("delivered", "Entregue", "delivered", None),
            action=("open", "Abrir", False),
        ),
        _keep(
            "finalizado",
            _tracks(_order(status="completed"), "paid"),
            delivery=("finalized", "Finalizado", "none", "Conclusão antiga, sem comprovação de entrega"),
            action=("open", "Abrir", False),
        ),
        _keep(
            "cancelado antes da produção",
            _tracks(_order(status="cancelled", cancellation_reason="cliente desistiu"), "cancelled_open"),
            commercial=("cancelled", "Cancelado", "cancelled"),
            payment=("cancelled_open", "Sem cobrança", "none", "Pedido cancelado sem pagamento regular"),
            production=("not_applicable", "—", "none", "Não se aplica"),
            delivery=("not_applicable", "—", "none", "Não se aplica"),
            attention="Motivo: cliente desistiu",
            action=("open", "Abrir", False),
        ),
        _keep(
            "cancelado depois da produção",
            _tracks(
                _order(status="cancelled", production_started_at=datetime.now(UTC)),
                "paid",
            ),
            production=("interrupted", "Interrompida", "cancelled"),
            action=("open", "Abrir", False),
        ),
        _keep(
            "estornado",
            _tracks(_order(status="cancelled"), "refunded"),
            payment=("refunded", "Estornado", "warn", "Valor estornado"),
        ),
        _keep(
            "estorno parcial",
            _tracks(_order(status="confirmed"), "partial_refund"),
            payment=("partial_refund", "Estorno parc.", "warn", "Estorno parcial; conferir saldo"),
            action=("open", "Abrir", False),
        ),
        _keep(
            "retirada histórica",
            _tracks(_order(status="confirmed", fulfillment_modality="pickup"), "paid"),
            delivery=("pickup", "Retirada", "none", None),
        ),
        _keep(
            "endereço pendente",
            _tracks(_order(status="confirmed", delivery_street=""), "paid"),
            delivery=("address_pending", "Sem endereço", "warn", "Endereço de entrega incompleto"),
        ),
        _keep(
            "data passada",
            _tracks(_order(production_local_date=yesterday), "awaiting", today=today),
            attention="Data da fornada já passou",
            action=("accept", "Avaliar e aceitar", True),
        ),
        _keep(
            "cobrança cancelada",
            _tracks(_order(status="confirmed"), "charge_cancelled"),
            payment=("charge_cancelled", "Cancelada", "none", "Cobrança cancelada no registro"),
        ),
    ]
    for status in ("pending", "alternative_proposed", "awaiting_details"):
        rows.append(
            _keep(
                f"solicitação {status}",
                date_request_tracks(_date(status), today=today),
                commercial=("open", "Aberto", "open"),
                payment=("not_applicable", "Sem cobrança", "none", "Solicitação não é cobrança"),
                production=("not_applicable", "—", "none", "Não se aplica"),
                action=("respond_date_request", "Avaliar e responder", True),
            )
        )
    rows.append(
        _keep(
            "solicitação closed",
            date_request_tracks(_date("closed"), today=today),
            commercial=("rejected", "Rejeitado", "cancelled"),
            action=("open", "Abrir", False),
        )
    )
    rows.append(
        _keep(
            "solicitação converted",
            date_request_tracks(_date("converted"), today=today),
            commercial=("converted", "Convertida", "none"),
            action=("open", "Abrir", False),
        )
    )
    for name, projection, expect in rows:
        for key in ("commercial", "payment", "production", "delivery"):
            if key not in expect:
                continue
            state, label, tone, *rest = expect[key]
            assert projection[key]["state"] == state, name
            assert projection[key]["label"] == label, name
            assert projection[key]["tone"] == tone, name
            if rest:
                assert projection[key]["hint"] == rest[0], name
        if "action" in expect:
            code, label, primary = expect["action"]
            assert projection["next_action"] == {"code": code, "label": label, "primary": primary}, name
        if "attention" in expect:
            assert projection["attention"] == expect["attention"], name
    assert len(rows) >= 24


def test_todo_label_de_trilha_tem_no_maximo_13():
    test_matriz_das_trilhas()
    for _name, projection, _expect in CASES:
        for label in track_labels(projection):
            assert len(label) <= 13, label


def _persist(db: Session, **fields) -> Order:
    order = Order(
        public_reference=new_public_reference(),
        currency="BRL",
        customer_note="",
        customer_name="Cliente Fila",
        customer_email=f"fila-{uuid4().hex[:8]}@example.test",
        fulfillment_modality="delivery",
        **fields,
    )
    db.add(order)
    db.flush()
    return order


def test_contagem_das_lentes_bate_com_a_lista(db: Session, admin_client):
    catalog = priced_catalog(db)
    del catalog
    _persist(db, status="submitted", total_cents=1800)
    _persist(db, status="confirmed", total_cents=1800)
    _persist(db, status="cancelled", total_cents=1800, cancellation_reason="teste")
    db.add(
        DateRequest(
            desired_date=date(2026, 11, 18),
            customer_name="Solicitante Fila",
            customer_email=f"sd-{uuid4().hex[:8]}@example.test",
            intended_quantity=1,
            status="pending",
            idempotency_key=f"p109-{uuid4().hex}",
            client_host="127.0.0.1",
        )
    )
    db.commit()
    login(admin_client)
    summary = admin_client.get("/api/v1/admin/ops/attendance-summary")
    assert summary.status_code == 200
    lenses = summary.json()["queue_lenses"]
    assert [row["key"] for row in lenses] == [
        "vigentes",
        "work:needs_action",
        "stage:open",
        "stage:accepted",
        "stage:paid",
        "stage:in_production",
        "stage:delivered",
        "stage:cancelled",
        "all",
    ]
    for row in lenses:
        listed = admin_client.get("/api/v1/admin/orders", params={"lens": row["key"], "page_size": 50})
        assert listed.status_code == 200, row["key"]
        assert listed.json()["total"] == row["count"], row["key"]
    action = admin_client.get("/api/v1/admin/orders", params={"lens": "work:needs_action", "page_size": 50})
    body = action.json()
    assert body["total"] == 2
    assert all(item["next_action"]["primary"] for item in body["items"])
    vigentes = admin_client.get("/api/v1/admin/orders", params={"lens": "vigentes", "page_size": 50}).json()
    assert any(item["next_action"]["primary"] is False for item in vigentes["items"])


def test_get_nao_grava(db: Session, admin_client):
    order = _persist(db, status="submitted", total_cents=900)
    db.commit()
    login(admin_client)

    def counts():
        return (
            db.scalar(select(func.count()).select_from(OrderStatusHistory)) or 0,
            db.scalar(select(func.count()).select_from(EmailOutbox)) or 0,
            db.scalar(select(func.count()).select_from(PaymentRecord)) or 0,
            db.scalar(select(func.count()).select_from(OpsPushDelivery)) or 0,
        )

    before = counts()
    assert admin_client.get("/api/v1/admin/orders").status_code == 200
    assert admin_client.get(f"/api/v1/admin/orders/{order.id}").status_code == 200
    assert admin_client.get("/api/v1/admin/ops/attendance-summary").status_code == 200
    db.expire_all()
    assert counts() == before


def test_lista_nao_cresce_consultas_com_os_itens(db: Session, admin_client):
    from app.db.session import get_engine

    for _ in range(2):
        _persist(db, status="submitted", total_cents=500)
    db.commit()
    login(admin_client)
    engine = get_engine()
    box = {"n": 0}

    def bump(*_args, **_kwargs):
        box["n"] += 1

    event.listen(engine, "before_cursor_execute", bump)
    try:
        box["n"] = 0
        assert admin_client.get("/api/v1/admin/orders", params={"page_size": 20}).status_code == 200
        first = box["n"]
        for _ in range(18):
            _persist(
                db,
                status="submitted",
                total_cents=500,
                created_at=datetime.now(UTC) - timedelta(minutes=1),
            )
        db.commit()
        box["n"] = 0
        assert admin_client.get("/api/v1/admin/orders", params={"page_size": 20}).status_code == 200
        second = box["n"]
    finally:
        event.remove(engine, "before_cursor_execute", bump)
    assert second == first
    assert first > 0
