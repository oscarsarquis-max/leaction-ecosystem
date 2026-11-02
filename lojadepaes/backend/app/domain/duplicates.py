"""Mesmo cliente e possível duplicidade. A regra mora aqui e só lê."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from app.domain.order_board import classify_payment
from app.models.orders import Order, OrderItem
from app.models.payments import PaymentRecord

_SPACE = re.compile(r"\s+")
_HOURS = 72


def normalize_email(value: str | None) -> str:
    return _SPACE.sub("", (value or "").strip().lower())


def normalize_phone(value: str | None) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) >= 11:
        return digits[-11:]
    return digits


def normalize_name(value: str | None) -> str:
    raw = unicodedata.normalize("NFD", (value or "").strip().lower())
    raw = "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")
    return _SPACE.sub(" ", raw).strip()


def _item_parts(item) -> tuple[str, int] | None:
    if isinstance(item, dict):
        variant = item.get("variant_id") or item.get("product_variant_id")
        quantity = int(item.get("quantity") or 0)
        if variant:
            return f"v:{variant}", quantity
        dough = item.get("dough_type_id") or item.get("product_id") or ""
        shape = item.get("bread_shape_id") or ""
        if not dough and not shape:
            return None
        return f"c:{dough}:{shape}", quantity
    quantity = int(item.quantity)
    if item.product_variant_id is not None:
        return f"v:{item.product_variant_id}", quantity
    if item.dough_type_id is None and item.bread_shape_id is None and item.product_id is None:
        return None
    return f"c:{item.dough_type_id}:{item.bread_shape_id}", quantity


def item_signature(items) -> tuple:
    keys = [row for row in (_item_parts(item) for item in items or []) if row is not None]
    return tuple(sorted(keys))


def same_items(left, right) -> bool:
    signature = item_signature(left)
    return bool(signature) and signature == item_signature(right)


def customer_match_reason(left, right, left_items, right_items, *, require_items: bool) -> str | None:
    """Mesmo cliente. Sem exigir itens, o nome sozinho basta. Com itens, o nome só vale junto deles."""
    email_left = normalize_email(_attr(left, "customer_email", "email"))
    email_right = normalize_email(_attr(right, "customer_email", "email"))
    if email_left and email_left == email_right:
        return "mesmo e-mail"
    phone_left = normalize_phone(_attr(left, "customer_phone", "phone"))
    phone_right = normalize_phone(_attr(right, "customer_phone", "phone"))
    if phone_left and phone_left == phone_right:
        return "mesmo telefone"
    name_left = normalize_name(_attr(left, "customer_name", "name"))
    name_right = normalize_name(_attr(right, "customer_name", "name"))
    if not name_left or name_left != name_right:
        return None
    items_match = same_items(left_items, right_items)
    if require_items:
        return "mesmo nome e mesmos itens" if items_match else None
    if items_match:
        return "mesmo nome e mesmos itens"
    return "mesmo nome"


def _attr(row, *names: str) -> str | None:
    for name in names:
        if isinstance(row, dict) and row.get(name):
            return str(row.get(name))
        value = getattr(row, name, None)
        if value:
            return str(value)
    return None


def within_72h(left: datetime | None, right: datetime | None) -> bool:
    if left is None or right is None:
        return False
    return abs((left - right).total_seconds()) <= _HOURS * 3600


def possible_duplicate_reason(
    left,
    right,
    left_items,
    right_items,
    *,
    left_blocked: bool = False,
    right_blocked: bool = False,
) -> str | None:
    if left_blocked or right_blocked:
        return None
    if getattr(left, "status", None) == "cancelled" or getattr(right, "status", None) == "cancelled":
        return None
    if not within_72h(getattr(left, "created_at", None), getattr(right, "created_at", None)):
        return None
    if not same_items(left_items, right_items):
        return None
    return customer_match_reason(left, right, left_items, right_items, require_items=True)


@dataclass(frozen=True)
class DuplicateHit:
    other_id: UUID
    other_reference: str
    other_paid: bool
    reason: str


def _paid(order: Order, records: list[PaymentRecord]) -> bool:
    return classify_payment(order, records) == "paid"


def duplicate_hits(
    orders: list[Order],
    items_by_order: dict[UUID, list],
    records_by_order: dict[UUID, list[PaymentRecord]],
    blocked_ids: set[UUID] | None = None,
) -> dict[UUID, DuplicateHit]:
    """Um passe em memória. `blocked_ids` são teste ou já anulados."""
    blocked = blocked_ids or set()
    found: dict[UUID, DuplicateHit] = {}
    ranked: dict[UUID, tuple] = {}
    for left in orders:
        for right in orders:
            if left.id == right.id:
                continue
            reason = possible_duplicate_reason(
                left,
                right,
                items_by_order.get(left.id, []),
                items_by_order.get(right.id, []),
                left_blocked=left.id in blocked,
                right_blocked=right.id in blocked,
            )
            if reason is None:
                continue
            other_paid = _paid(right, records_by_order.get(right.id, []))
            created = getattr(right, "created_at", None)
            left_created = getattr(left, "created_at", None)
            distance = abs((created - left_created).total_seconds()) if created and left_created else 0
            rank = (not other_paid, distance)
            previous = ranked.get(left.id)
            if previous is not None and previous <= rank:
                continue
            ranked[left.id] = rank
            found[left.id] = DuplicateHit(
                other_id=right.id,
                other_reference=right.public_reference,
                other_paid=other_paid,
                reason=reason,
            )
    return found


def request_phone(request) -> str:
    complement = getattr(request, "complement", None) or {}
    if isinstance(complement, dict):
        return str(complement.get("customer_phone") or "")
    return ""


def request_items(lines: list[dict] | None) -> list[dict]:
    items = []
    for line in lines or []:
        variant = line.get("variant_id") or line.get("product_variant_id")
        product = line.get("product_id") or ""
        if not variant and not product:
            continue
        items.append(
            {
                "product_id": str(product),
                "variant_id": str(variant or ""),
                "quantity": int(line.get("quantity") or 0),
            }
        )
    return items
