"""Pedido da casa numa combo (M8): pão da Loja + frete fixo + acordo de comercialização do parceiro.

Espelha as regras de calendário, endereço, idempotência e token do `submit_order`, sem alterá-lo.
Este módulo não conhece o marketplace: a ponte (`app/api/v1/combo.py`) entrega os números do parceiro.

Preço (centavos):
- unidade do pão = preço do pão na combo, se houver; senão o da variação na vitrine;
- pedido da casa: subtotal (qtd x unidade) + frete fixo + acordo (combo_fee_cents) = total;
- valor de face que o cliente viu (`quoted_cents`) = pão + frete da Loja + itens do parceiro + frete do parceiro.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.bakery_time import bakery_zone
from app.domain.email_outbox import enqueue_admin_order_email
from app.domain.errors import CapacityError, ConfirmationError, ConflictError, NotFoundError, PriceChangedError
from app.domain.orders import confirm_order, new_public_reference
from app.domain.schedule import (
    REASON_UNKNOWN_BASE,
    REASON_UNKNOWN_UNITS,
    ProposedLine,
    evaluate_day,
    proposed_physical,
    resolve_proposed_lines,
)
from app.domain.storefront_orders import (
    _crm_session,
    _email,
    _load_variant,
    email_access_token,
    hash_access_token,
    parse_preferred_time,
    require_new_order_address,
)
from app.models.enums import EditorialStatus, FinancialStatus, OrderStatus, PaymentProvider
from app.models.orders import Order, OrderItem
from app.models.payments import PaymentRecord
from app.models.production import ProductionBatch
from app.models.products import Product, ProductVariant

logger = logging.getLogger(__name__)

COMBO_HOUSE_FREIGHT_CENTS = 800
COMBO_MAX_QUANTITY = 10
_BAKERY_LABELS = {
    "submitted": "Aguardando a Loja",
    "confirmed": "Confirmado pela Loja",
    "in_production": "Em produção",
    "ready": "Pronto para entrega",
    "completed": "Entregue",
    "cancelled": "Cancelado pela Loja",
}


@dataclass(frozen=True)
class ComboHouseOrder:
    order: Order
    token: str
    combo_ref: UUID
    created: bool


def clean_quantity(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise ConfirmationError(f"informe a quantidade de {label}")
    try:
        quantity = int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        raise ConfirmationError(f"informe a quantidade de {label}") from None
    if quantity < 1 or quantity > COMBO_MAX_QUANTITY:
        raise ConfirmationError(f"a quantidade de {label} vai de 1 a {COMBO_MAX_QUANTITY}")
    return quantity


def combo_status_label(status: str) -> str:
    return _BAKERY_LABELS.get(status, status)


_ADDRESS_LABELS = (
    ("delivery_street", "a rua"),
    ("delivery_number", "o número"),
    ("delivery_district", "o bairro"),
    ("delivery_city", "a cidade"),
    ("delivery_state", "o estado"),
    ("delivery_postal_code", "o CEP"),
)


def require_full_delivery_address(payload: dict) -> dict:
    """Mesma leitura do pedido normal (só entrega), mas o endereço precisa vir completo: o parceiro entrega nele."""
    address = require_new_order_address(payload)
    missing = [label for key, label in _ADDRESS_LABELS if not address.get(key)]
    if missing:
        raise ConfirmationError("informe o endereço de entrega completo: falta " + ", ".join(missing))
    return address


def address_line_of(address: dict) -> str:
    """Endereço em uma linha para o parceiro (rua, número, complemento - bairro, cidade/UF, CEP)."""
    street = ", ".join(part for part in (address.get("delivery_street"), address.get("delivery_number")) if part)
    if address.get("delivery_complement"):
        street = f"{street}, {address['delivery_complement']}"
    place = ", ".join(part for part in (address.get("delivery_district"), address.get("delivery_city")) if part)
    if address.get("delivery_state"):
        place = f"{place}/{address['delivery_state']}"
    postal = address.get("delivery_postal_code") or ""
    if len(postal) == 8 and postal.isdigit():
        postal = f"{postal[:5]}-{postal[5:]}"
    return " - ".join(part for part in (street, place, f"CEP {postal}" if postal else "") if part)


def bread_variants(session: Session, slug: str) -> tuple[Product, list[ProductVariant]] | None:
    """Pão publicado e à venda, com as variações ativas e com preço. None se não está à venda."""
    product = session.scalar(select(Product).where(Product.slug == slug))
    if (
        product is None
        or product.editorial_status != EditorialStatus.PUBLISHED.value
        or not product.is_available
    ):
        return None
    variants = [
        variant
        for variant in session.scalars(
            select(ProductVariant)
            .where(ProductVariant.product_id == product.id)
            .order_by(ProductVariant.sort_order, ProductVariant.display_name)
        )
        if variant.is_active and variant.price_cents is not None and variant.price_cents > 0
    ]
    return product, variants


def find_combo_order(session: Session, settings: Settings, idempotency_key: str) -> ComboHouseOrder | None:
    """Reenvio da mesma chave: devolve o pedido já criado, sem nova reserva nem nova cobrança."""
    key = (idempotency_key or "").strip()
    if not key or len(key) > 120:
        raise ConfirmationError("chave de envio obrigatória")
    existing = session.scalar(select(Order).where(Order.submit_idempotency_key == key))
    if existing is None:
        return None
    if existing.combo_ref is None:
        raise ConflictError("esta chave de envio já foi usada em outro pedido")
    return ComboHouseOrder(
        order=existing,
        token=email_access_token(settings, existing),
        combo_ref=existing.combo_ref,
        created=False,
    )


def accept_deadline_for_date(session: Session, settings: Settings, day: date) -> datetime | None:
    """Prazo de pedidos da Loja para a data: `order_deadline_at` da fornada daquela data.

    A agenda por data (evaluate_day/occupy_capacity) não usa fornadas; as fornadas continuam existindo
    em `production_batches`. Havendo mais de uma fornada no dia, vale o prazo mais cedo. Sem fornada
    para a data devolve None (o pedido do parceiro expira quando a data passa).
    """
    zone = bakery_zone(settings)
    start = datetime(day.year, day.month, day.day, tzinfo=zone)
    end = start + timedelta(days=1)
    return session.scalar(
        select(ProductionBatch.order_deadline_at)
        .where(
            ProductionBatch.status != "cancelled",
            ProductionBatch.breads_available_at >= start,
            ProductionBatch.breads_available_at < end,
        )
        .order_by(ProductionBatch.order_deadline_at.asc())
        .limit(1)
    )


def _assert_day_fits(session: Session, settings: Settings, requested: date, product: Product, variant, quantity: int):
    proposed = ProposedLine(kind="product", quantity=quantity, variant_id=variant.id)
    resolved = resolve_proposed_lines(session, [proposed])
    day = evaluate_day(session, settings, requested, resolved)
    catalog_gap = day.reason in {REASON_UNKNOWN_UNITS, REASON_UNKNOWN_BASE}
    selection = f"{quantity}× {product.name} ({variant.display_name})"
    if not day.eligible_for_selection and not catalog_gap:
        raise CapacityError(
            f"{day.accessible_label}. Item impeditivo: {selection}. "
            "A seleção permanece e nenhum pedido foi criado."
        )
    asked, unknown_asked = proposed_physical(resolved)
    if not unknown_asked and asked is not None and asked > day.remaining_physical:
        raise CapacityError(
            f"{day.accessible_label}. Item impeditivo: {selection}. "
            f"A quantidade pedida ({asked} pães) passa do que esta data ainda comporta "
            f"({day.remaining_physical}). A seleção permanece e nenhum pedido foi criado."
        )


def create_combo_house_order(
    session: Session,
    settings: Settings,
    payload: dict,
    *,
    bread_slug: str,
    house_unit_price_cents: int | None,
    partner_fee_cents: int,
    partner_face_cents: int,
) -> ComboHouseOrder:
    """Cria o pedido da casa da combo (aceite automático, como o pedido normal).

    `partner_face_cents` = quantidade x preço do item do parceiro + frete do parceiro (0 se não informado).
    `payload` traz variant_id, bread_quantity, requested_date, quoted_cents, cliente, endereço e idempotency_key.
    A transação é do chamador (nada é confirmado aqui).
    """
    replay = find_combo_order(session, settings, str(payload.get("idempotency_key") or ""))
    if replay is not None:
        return replay
    key = str(payload["idempotency_key"]).strip()

    quantity = clean_quantity(payload.get("bread_quantity"), "pães")
    quoted_cents = int(payload["quoted_cents"])
    requested = date.fromisoformat(str(payload["requested_date"]))

    product, variant = _load_variant(session, UUID(str(payload["variant_id"])))
    if product.slug != bread_slug:
        raise ConfirmationError("a opção escolhida não é do pão desta combinação")
    if product.editorial_status != EditorialStatus.PUBLISHED.value or not product.is_available:
        raise ConfirmationError(f"{product.name} não está à venda")
    if not variant.is_active or variant.price_cents is None or variant.price_cents <= 0:
        raise ConfirmationError(f"a opção de {product.name} não está à venda")

    unit = int(house_unit_price_cents) if house_unit_price_cents else int(variant.price_cents)
    subtotal = quantity * unit
    face_total = subtotal + COMBO_HOUSE_FREIGHT_CENTS + int(partner_face_cents)
    if face_total != quoted_cents:
        raise PriceChangedError(quoted_cents, face_total)

    _assert_day_fits(session, settings, requested, product, variant, quantity)

    name = str(payload.get("customer_name") or "").strip()
    if not name or len(name) > 160:
        raise ConfirmationError("informe o nome de quem pede")
    email = _email(str(payload.get("customer_email") or ""))
    phone = str(payload.get("customer_phone") or "").strip() or None
    address = require_full_delivery_address(payload)
    preferred = parse_preferred_time(payload.get("preferred_time"))

    combo_ref = uuid4()
    token = secrets.token_urlsafe(32)
    fee = int(partner_fee_cents)
    total = subtotal + COMBO_HOUSE_FREIGHT_CENTS + fee
    order = Order(
        public_reference=new_public_reference(),
        status=OrderStatus.SUBMITTED.value,
        fulfillment_modality="delivery",
        preferred_time=preferred,
        production_local_date=requested,
        requested_date=requested,
        customer_name=name,
        customer_email=email,
        customer_phone=phone,
        delivery_street=address["delivery_street"],
        delivery_number=address["delivery_number"],
        delivery_complement=address["delivery_complement"],
        delivery_district=address["delivery_district"],
        delivery_city=address["delivery_city"],
        delivery_state=address["delivery_state"],
        delivery_postal_code=address["delivery_postal_code"],
        customer_note=str(payload.get("customer_note") or "")[:2000],
        currency="BRL",
        subtotal_cents=subtotal,
        delivery_fee_cents=COMBO_HOUSE_FREIGHT_CENTS,
        discount_cents=0,
        total_cents=total,
        holds_capacity=False,
        access_token_hash=hash_access_token(token),
        submit_idempotency_key=key,
        crm_id_sessao=_crm_session(payload.get("id_sessao")),
        order_kind="standard",
        fidelity_opt_in=False,
        fidelity_qualifies=False,
        combo_ref=combo_ref,
        combo_fee_cents=fee,
    )
    session.add(order)
    session.flush()
    session.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_variant_id=variant.id,
            recipe_base_id=product.recipe_base_id,
            physical_units=None if variant.physical_units is None else variant.physical_units * quantity,
            quantity=quantity,
            dough_name_snapshot=product.name,
            shape_name_snapshot=variant.display_name,
            unit_price_cents=unit,
            line_total_cents=subtotal,
            net_weight_grams=variant.net_weight_grams,
        )
    )
    session.flush()
    session.add(
        PaymentRecord(
            order_id=order.id,
            provider=PaymentProvider.ACTIONHUB.value,
            expected_cents=total,
            currency="BRL",
            financial_status=FinancialStatus.PENDING.value,
        )
    )
    confirm_order(session, order.id, actor_ref="system:auto-accept")
    enqueue_admin_order_email(session, settings, order, auto_accepted=True)
    session.flush()
    from app.domain.crm_tracking import emit_order_fact

    emit_order_fact(session, settings, order, "pedido_enviar", situacao="confirmed")
    # M8: sem cobrança (fica para o M9). PaymentRecord fica pending só como memória do valor.
    return ComboHouseOrder(order=order, token=token, combo_ref=combo_ref, created=True)


def combo_house_order_by_ref(session: Session, combo_ref: UUID) -> Order:
    order = session.scalar(select(Order).where(Order.combo_ref == combo_ref))
    if order is None:
        raise NotFoundError("pedido não encontrado")
    return order
