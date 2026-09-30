from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.core.config import Settings
from app.domain.bakery_time import bakery_today
from app.domain.capacity import utc_now
from app.domain.house_fidelity import CAMPAIGN_SLUG, real_balance
from app.domain.house_fidelity_ledger import (
    consume_or_return_credit,
    reconcile_order,
    reserve_credit,
)
from app.domain.house_fidelity_redeem import redeem_loaf
from app.domain.orders import new_public_reference, transition_order
from app.domain.recipe_bases import create_recipe_base
from app.domain.showcase import ensure_slots
from app.models.customers import CustomerAccount
from app.models.enums import EditorialStatus, FinancialStatus, OrderStatus, PaymentProvider
from app.models.house_fidelity import HouseFidelityCampaign, HouseFidelityCredit, HouseFidelityEvent
from app.models.orders import Order, OrderItem
from app.models.payments import PaymentRecord
from app.models.products import Product, ProductVariant
from sqlalchemy import select
from sqlalchemy.orm import Session


def _settings(**extra) -> Settings:
    return Settings(
        admin_session_secret="test-admin-session-secret-32chars",
        customer_identity_secret="test-customer-identity-secret-32c",
        house_fidelity_active=True,
        **extra,
    )


def _campaign(db: Session, status: str = "active") -> HouseFidelityCampaign:
    row = HouseFidelityCampaign(
        slug=CAMPAIGN_SLUG,
        version=1,
        status=status,
        rules_version="43a",
        title="Fidelidade da casa",
        starts_at=datetime(2026, 1, 1, tzinfo=UTC),
        rules_json="{}",
    )
    db.add(row)
    db.flush()
    return row


def _account(db: Session) -> CustomerAccount:
    account = CustomerAccount(
        name="Ana",
        email=f"ana-{uuid4().hex[:8]}@example.com",
        email_verified_at=datetime.now(UTC),
        cpf_hmac=f"hmac-{uuid4().hex}",
        cpf_last2="05",
        marketing_opt_in=False,
    )
    db.add(account)
    db.flush()
    return account


def _product(db: Session, grams: int = 500) -> ProductVariant:
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa teste")
    product = Product(
        name="Pão teste",
        slug=f"pao-{uuid4().hex[:8]}",
        short_description="crosta",
        recipe_base_id=base.id,
        featured_image_alt="pão",
        editorial_status=EditorialStatus.PUBLISHED.value,
        is_available=True,
        fidelity_eligible=True,
    )
    db.add(product)
    db.flush()
    slots = ensure_slots(db)
    empty = next((slot for slot in slots if slot.product_id is None), slots[0])
    empty.product_id = product.id
    db.flush()
    variant = ProductVariant(
        product_id=product.id,
        display_name=f"{grams} g",
        presentation_type="weight",
        net_weight_grams=grams,
        physical_units=1,
        price_cents=2490,
        currency="BRL",
        is_active=True,
    )
    db.add(variant)
    db.flush()
    return variant


def _order(
    db: Session,
    account: CustomerAccount,
    campaign: HouseFidelityCampaign,
    variant: ProductVariant,
    *,
    opt_in: bool = True,
    total: int = 2490,
    kind: str = "standard",
    created_at: datetime | None = None,
) -> Order:
    order = Order(
        public_reference=new_public_reference(),
        status=OrderStatus.SUBMITTED.value,
        fulfillment_modality="pickup",
        customer_name=account.name,
        customer_email=account.email,
        currency="BRL",
        subtotal_cents=total,
        delivery_fee_cents=0,
        discount_cents=0,
        total_cents=total,
        holds_capacity=False,
        access_token_hash=uuid4().hex + uuid4().hex[:32],
        submit_idempotency_key=f"key-{uuid4().hex}",
        order_kind=kind,
        fidelity_opt_in=opt_in,
        fidelity_account_id=account.id if opt_in else None,
        fidelity_campaign_id=campaign.id if opt_in else None,
        fidelity_rules_version="43a" if opt_in else None,
    )
    db.add(order)
    db.flush()
    if created_at is not None:
        order.created_at = created_at
    product = db.get(Product, variant.product_id)
    db.add(
        OrderItem(
            order_id=order.id,
            product_id=variant.product_id,
            product_variant_id=variant.id,
            recipe_base_id=product.recipe_base_id,
            physical_units=1,
            quantity=1,
            dough_name_snapshot=product.name,
            shape_name_snapshot=variant.display_name,
            unit_price_cents=variant.price_cents,
            line_total_cents=total,
            net_weight_grams=variant.net_weight_grams,
        )
    )
    if total > 0:
        db.add(
            PaymentRecord(
                order_id=order.id,
                provider=PaymentProvider.ACTIONHUB.value,
                expected_cents=total,
                currency="BRL",
                financial_status=FinancialStatus.PENDING.value,
            )
        )
    db.flush()
    return order


def _pay(db: Session, order: Order, when: datetime | None = None) -> None:
    record = db.scalar(select(PaymentRecord).where(PaymentRecord.order_id == order.id))
    record.financial_status = FinancialStatus.PAID.value
    record.amount_paid_cents = order.total_cents
    record.confirmed_at = when or datetime.now(UTC)
    db.flush()


def _close(db: Session, order: Order, when: datetime | None = None) -> None:
    order.status = OrderStatus.CONFIRMED.value
    order.confirmed_at = when or utc_now()
    db.flush()


def _qualify(db: Session, settings: Settings, order: Order) -> None:
    reconcile_order(db, settings, order)


def _next_wednesday(settings: Settings) -> str:
    today = bakery_today(settings)
    delta = (3 - today.isoweekday()) % 7
    day = today + timedelta(days=delta)
    if day <= today:
        day += timedelta(days=7)
    return day.isoformat()


def _events(db: Session, account_id) -> list[HouseFidelityEvent]:
    return list(
        db.scalars(
            select(HouseFidelityEvent).where(
                HouseFidelityEvent.account_id == account_id,
                HouseFidelityEvent.kind == "qualify",
                HouseFidelityEvent.status == "applied",
            )
        )
    )


def test_four_closed_and_paid_orders_make_one_credit(db: Session) -> None:
    settings = _settings()
    campaign = _campaign(db)
    account = _account(db)
    variant = _product(db)
    for _ in range(4):
        order = _order(db, account, campaign, variant)
        _pay(db, order)
        _qualify(db, settings, order)
        assert db.scalar(select(HouseFidelityEvent).where(HouseFidelityEvent.order_id == order.id)) is None
        _close(db, order)
        _qualify(db, settings, order)
    assert len(_events(db, account.id)) == 4
    credits = list(
        db.scalars(
            select(HouseFidelityCredit).where(
                HouseFidelityCredit.account_id == account.id,
                HouseFidelityCredit.status == "available",
            )
        )
    )
    assert len(credits) == 1
    last = _order(db, account, campaign, variant)
    _close(db, last)
    _qualify(db, settings, last)
    assert db.scalar(select(HouseFidelityEvent).where(HouseFidelityEvent.order_id == last.id)) is None
    _pay(db, last)
    _qualify(db, settings, last)
    _qualify(db, settings, last)
    assert len(_events(db, account.id)) == 5


def test_paid_only_or_closed_only_does_not_stamp(db: Session) -> None:
    settings = _settings()
    campaign = _campaign(db)
    account = _account(db)
    variant = _product(db)
    paid_only = _order(db, account, campaign, variant)
    _pay(db, paid_only)
    _qualify(db, settings, paid_only)
    assert db.scalar(select(HouseFidelityEvent).where(HouseFidelityEvent.order_id == paid_only.id)) is None
    closed_only = _order(db, account, campaign, variant)
    _close(db, closed_only)
    _qualify(db, settings, closed_only)
    assert db.scalar(select(HouseFidelityEvent).where(HouseFidelityEvent.order_id == closed_only.id)) is None


def test_out_of_order_events_do_not_duplicate(db: Session) -> None:
    settings = _settings()
    campaign = _campaign(db)
    account = _account(db)
    variant = _product(db)
    first = _order(db, account, campaign, variant)
    _pay(db, first, datetime(2026, 9, 28, 10, 0, tzinfo=UTC))
    _close(db, first, datetime(2026, 9, 28, 18, 0, tzinfo=UTC))
    _qualify(db, settings, first)
    _qualify(db, settings, first)
    second = _order(db, account, campaign, variant)
    _close(db, second, datetime(2026, 9, 29, 9, 0, tzinfo=UTC))
    _pay(db, second, datetime(2026, 9, 29, 16, 0, tzinfo=UTC))
    _qualify(db, settings, second)
    _qualify(db, settings, second)
    events = _events(db, account.id)
    assert len(events) == 2
    assert {row.order_id for row in events} == {first.id, second.id}


def test_order_before_campaign_never_counts_even_if_delivered(db: Session) -> None:
    settings = _settings()
    campaign = _campaign(db)
    campaign.starts_at = datetime(2026, 9, 1, tzinfo=UTC)
    account = _account(db)
    variant = _product(db)
    order = _order(
        db,
        account,
        campaign,
        variant,
        created_at=datetime(2026, 8, 20, tzinfo=UTC),
    )
    _pay(db, order)
    _close(db, order)
    order.status = OrderStatus.COMPLETED.value
    order.fulfilled_at = utc_now()
    db.flush()
    _qualify(db, settings, order)
    assert db.scalar(select(HouseFidelityEvent).where(HouseFidelityEvent.order_id == order.id)) is None


def test_standalone_order_stays_unstamped_after_later_signup(db: Session) -> None:
    settings = _settings()
    campaign = _campaign(db)
    guest = _account(db)
    variant = _product(db)
    order = _order(db, guest, campaign, variant, opt_in=False)
    _pay(db, order)
    _close(db, order)
    later = _account(db)
    order.customer_email = later.email
    db.flush()
    _qualify(db, settings, order)
    assert order.fidelity_opt_in is False
    assert db.scalar(select(HouseFidelityEvent).where(HouseFidelityEvent.order_id == order.id)) is None


def test_historical_delivery_does_not_create_points(db: Session) -> None:
    settings = _settings()
    campaign = _campaign(db)
    account = _account(db)
    variant = _product(db)
    order = _order(
        db,
        account,
        campaign,
        variant,
        opt_in=False,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    _pay(db, order)
    _close(db, order)
    order.status = OrderStatus.COMPLETED.value
    order.fulfilled_at = utc_now()
    db.flush()
    _qualify(db, settings, order)
    assert db.scalar(select(HouseFidelityEvent)) is None


def test_eighth_order_second_credit_and_month_keeps_credits(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings()
    campaign = _campaign(db)
    account = _account(db)
    variant = _product(db)
    for _ in range(8):
        order = _order(db, account, campaign, variant)
        _pay(db, order)
        _close(db, order)
        _qualify(db, settings, order)
    available = list(
        db.scalars(
            select(HouseFidelityCredit).where(
                HouseFidelityCredit.account_id == account.id,
                HouseFidelityCredit.status == "available",
            )
        )
    )
    assert len(available) == 2
    october = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
    monkeypatch.setattr("app.domain.house_fidelity.bakery_now", lambda _settings: october)
    balance = real_balance(db, settings, account.id, campaign)
    assert balance["valid_orders_month"] == 0
    assert balance["credits"] == 2


def test_redemption_zero_total_skips_provider_and_does_not_stamp(db: Session) -> None:
    settings = _settings()
    campaign = _campaign(db)
    account = _account(db)
    variant = _product(db)
    for _ in range(4):
        paid = _order(db, account, campaign, variant)
        _pay(db, paid)
        _close(db, paid)
        _qualify(db, settings, paid)
    order, token = redeem_loaf(
        db,
        settings,
        account,
        {
            "variant_id": str(variant.id),
            "requested_date": _next_wednesday(settings),
            "idempotency_key": f"redeem-{uuid4().hex}",
        },
    )
    assert token
    assert order.total_cents == 0
    credit = db.get(HouseFidelityCredit, order.fidelity_credit_id)
    assert credit.status == "reserved"
    order.status = OrderStatus.COMPLETED.value
    order.fulfilled_at = utc_now()
    db.flush()
    consume_or_return_credit(db, order)
    _qualify(db, settings, order)
    db.refresh(credit)
    assert credit.status == "used"
    assert (
        db.scalar(
            select(HouseFidelityEvent).where(
                HouseFidelityEvent.order_id == order.id, HouseFidelityEvent.kind == "qualify"
            )
        )
        is None
    )


def test_cancel_returns_reserved_credit(db: Session) -> None:
    settings = _settings()
    campaign = _campaign(db)
    account = _account(db)
    variant = _product(db)
    for _ in range(4):
        paid = _order(db, account, campaign, variant)
        _pay(db, paid)
        _close(db, paid)
        _qualify(db, settings, paid)
    order = Order(
        public_reference=new_public_reference(),
        status=OrderStatus.SUBMITTED.value,
        fulfillment_modality="pickup",
        customer_name=account.name,
        customer_email=account.email,
        currency="BRL",
        subtotal_cents=2490,
        delivery_fee_cents=0,
        discount_cents=2490,
        total_cents=0,
        holds_capacity=False,
        access_token_hash=uuid4().hex + uuid4().hex[:32],
        submit_idempotency_key=f"key-{uuid4().hex}",
        order_kind="redemption",
        fidelity_account_id=account.id,
        fidelity_campaign_id=campaign.id,
        fidelity_rules_version="43a",
    )
    db.add(order)
    db.flush()
    reserve_credit(db, settings, account.id, order)
    transition_order(db, order.id, OrderStatus.CANCELLED.value, "cliente desistiu")
    credit = db.scalar(select(HouseFidelityCredit).where(HouseFidelityCredit.account_id == account.id))
    assert credit.status == "available"


def test_partial_refund_opens_review_and_does_not_grant_credit(db: Session) -> None:
    settings = _settings()
    campaign = _campaign(db)
    account = _account(db)
    variant = _product(db)
    for _ in range(3):
        paid = _order(db, account, campaign, variant)
        _pay(db, paid)
        _close(db, paid)
        _qualify(db, settings, paid)
    contested = _order(db, account, campaign, variant)
    _pay(db, contested)
    _close(db, contested)
    record = db.scalar(select(PaymentRecord).where(PaymentRecord.order_id == contested.id))
    record.financial_status = FinancialStatus.PARTIALLY_REFUNDED.value
    record.amount_refunded_cents = 500
    record.amount_paid_cents = 2490
    db.flush()
    _qualify(db, settings, contested)
    review = db.scalar(
        select(HouseFidelityEvent).where(
            HouseFidelityEvent.order_id == contested.id,
            HouseFidelityEvent.kind == "partial_review",
            HouseFidelityEvent.status == "pending",
        )
    )
    assert review is not None
    assert "sem decisão automática" in review.reason
    assert (
        db.scalar(
            select(HouseFidelityEvent).where(
                HouseFidelityEvent.order_id == contested.id,
                HouseFidelityEvent.kind == "qualify",
            )
        )
        is None
    )
    assert (
        db.scalar(
            select(HouseFidelityCredit).where(HouseFidelityCredit.account_id == account.id)
        )
        is None
    )


def test_partial_refund_keeps_existing_stamp_and_used_credit(db: Session) -> None:
    settings = _settings()
    campaign = _campaign(db)
    account = _account(db)
    variant = _product(db)
    stamped = []
    for _ in range(4):
        paid = _order(db, account, campaign, variant)
        _pay(db, paid)
        _close(db, paid)
        _qualify(db, settings, paid)
        stamped.append(paid)
    credit = db.scalar(select(HouseFidelityCredit).where(HouseFidelityCredit.account_id == account.id))
    credit.status = "used"
    db.flush()
    target = stamped[0]
    record = db.scalar(select(PaymentRecord).where(PaymentRecord.order_id == target.id))
    record.financial_status = FinancialStatus.PARTIALLY_REFUNDED.value
    record.amount_refunded_cents = 200
    db.flush()
    _qualify(db, settings, target)
    qualify = db.scalar(
        select(HouseFidelityEvent).where(
            HouseFidelityEvent.order_id == target.id,
            HouseFidelityEvent.kind == "qualify",
        )
    )
    assert qualify.status == "applied"
    db.refresh(credit)
    assert credit.status == "used"
    review = db.scalar(
        select(HouseFidelityEvent).where(
            HouseFidelityEvent.kind == "partial_review",
            HouseFidelityEvent.order_id == target.id,
        )
    )
    assert review is not None and review.status == "pending"


def test_second_reserve_does_not_reuse_the_same_credit(db: Session) -> None:
    settings = _settings()
    campaign = _campaign(db)
    account = _account(db)
    variant = _product(db)
    for _ in range(4):
        paid = _order(db, account, campaign, variant)
        _pay(db, paid)
        _close(db, paid)
        _qualify(db, settings, paid)
    first = Order(
        public_reference=new_public_reference(),
        status=OrderStatus.SUBMITTED.value,
        fulfillment_modality="pickup",
        customer_name=account.name,
        customer_email=account.email,
        currency="BRL",
        subtotal_cents=0,
        delivery_fee_cents=0,
        discount_cents=2490,
        total_cents=0,
        holds_capacity=False,
        access_token_hash=uuid4().hex + uuid4().hex[:32],
        submit_idempotency_key=f"key-{uuid4().hex}",
        order_kind="redemption",
        fidelity_account_id=account.id,
        fidelity_campaign_id=campaign.id,
        fidelity_rules_version="44",
    )
    second = Order(
        public_reference=new_public_reference(),
        status=OrderStatus.SUBMITTED.value,
        fulfillment_modality="pickup",
        customer_name=account.name,
        customer_email=account.email,
        currency="BRL",
        subtotal_cents=0,
        delivery_fee_cents=0,
        discount_cents=2490,
        total_cents=0,
        holds_capacity=False,
        access_token_hash=uuid4().hex + uuid4().hex[:32],
        submit_idempotency_key=f"key-{uuid4().hex}",
        order_kind="redemption",
        fidelity_account_id=account.id,
        fidelity_campaign_id=campaign.id,
        fidelity_rules_version="44",
    )
    db.add_all([first, second])
    db.flush()
    reserved = reserve_credit(db, settings, account.id, first)
    assert reserved.status == "reserved"
    with pytest.raises(Exception, match="não há crédito disponível"):
        reserve_credit(db, settings, account.id, second)
