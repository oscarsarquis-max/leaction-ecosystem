from __future__ import annotations

from html import escape

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.email_outbox import (
    _brl,
    _date_for,
    delivery_address_text,
)
from app.domain.orders import order_delivery_pending
from app.domain.payments import order_is_financially_settled
from app.models.orders import Order, OrderItem
from app.models.payments import PaymentRecord

OFFICIAL_LOGO_PATH = "/images/lojadepaeslogo.png"
CTA_PAY = "Pagar e acompanhar meu pedido"
CTA_FOLLOW = "Acompanhar meu pedido"
DELIVERY_NEED = (
    "Precisamos que você complete os dados de entrega. "
    "Você pode informar o endereço no mesmo link do pedido."
)


def official_logo_url(settings: Settings) -> str:
    return f"{settings.public_origin.rstrip('/')}{OFFICIAL_LOGO_PATH}"


def _first_name(order: Order) -> str:
    name = (order.customer_name or "").strip()
    if not name:
        return "olá"
    return name.split()[0]


def _item_lines(session: Session, order: Order) -> list[str]:
    items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id)))
    lines: list[str] = []
    for item in items:
        product = (item.dough_name_snapshot or "pão").strip()
        variant = (item.shape_name_snapshot or "").strip()
        weight = f" ({item.net_weight_grams} g)" if item.net_weight_grams else ""
        label = f"{product} · {variant}{weight}" if variant else f"{product}{weight}"
        lines.append(f"{item.quantity}× {label}")
    return lines


def _preferred(order: Order) -> str:
    if order.preferred_time:
        return (
            f"{order.preferred_time.strftime('%H:%M')} "
            "(preferência; não é janela de entrega prometida)"
        )
    return "Sem preferência informada"


def order_customer_context(
    session: Session, settings: Settings, order: Order, kind: str
) -> dict:
    from app.domain.storefront_orders import protected_order_url

    records = list(session.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id)))
    paid = order_is_financially_settled(order, records)
    pending = order_delivery_pending(order)
    items = _item_lines(session, order)
    return {
        "name": _first_name(order),
        "ref": order.public_reference,
        "date": _date_for(order, kind),
        "items": items,
        "items_text": "\n".join(f"- {line}" for line in items) or "- itens conforme o pedido",
        "total": _brl(order.total_cents),
        "preferred_time": _preferred(order),
        "link": protected_order_url(settings, order),
        "logo": official_logo_url(settings),
        "paid": paid,
        "delivery_pending": pending,
        "address": delivery_address_text(order),
        "phone": (order.customer_phone or "").strip(),
        "cta": CTA_FOLLOW if paid else CTA_PAY,
    }


def complementary_pending_labels(ctx: dict) -> list[str]:
    pending: list[str] = []
    if ctx.get("delivery_pending"):
        pending.append("endereço de entrega")
    if not (ctx.get("phone") or "").strip():
        pending.append("telefone")
    return pending


def _pending_sentence(ctx: dict) -> str:
    pending = complementary_pending_labels(ctx)
    if not pending:
        return ""
    return (
        "Ainda precisamos de: "
        + ", ".join(pending)
        + ". Isso não impede o pagamento nem a reserva.\n\n"
    )


def render_order_accepted_text(ctx: dict) -> tuple[str, str]:
    if ctx["paid"]:
        subject = f"Pedido aceito — acompanhe {ctx['ref']}"
        lead = (
            f"A Loja aceitou o pedido {ctx['ref']} e reservou a data confirmada {ctx['date']}.\n"
            "O pagamento já foi recebido. Isso ainda não significa que o pão está em produção ou entregue."
        )
    else:
        subject = f"Pedido aceito — pague e acompanhe {ctx['ref']}"
        lead = (
            f"A Loja aceitou o pedido {ctx['ref']} e reservou a data confirmada {ctx['date']}.\n"
            "Aceite ainda não significa pago, em produção ou entregue."
        )
    delivery = (
        f"{DELIVERY_NEED}\n"
        if ctx["delivery_pending"]
        else f"Endereço de entrega:\n{ctx['address']}\n"
    )
    body = (
        f"Olá, {ctx['name']}.\n\n"
        f"{lead}\n\n"
        f"Itens:\n{ctx['items_text']}\n\n"
        f"Total: {ctx['total']}\n"
        f"Horário solicitado: {ctx['preferred_time']}\n\n"
        f"{delivery}\n"
        f"{_pending_sentence(ctx)}"
        f"{ctx['cta']}:\n{ctx['link']}\n\n"
        "Neste mesmo endereço protegido você paga (se ainda faltar), "
        "acompanha o andamento e completa os dados de entrega, se faltarem."
    )
    return subject, body


def render_order_accepted_html(ctx: dict) -> str:
    items = "".join(f"<li>{escape(line)}</li>" for line in ctx["items"])
    if not items:
        items = "<li>itens conforme o pedido</li>"
    pending = _pending_sentence(ctx).strip()
    pending_html = f"<p><strong>{escape(pending)}</strong></p>" if pending else ""
    if ctx["delivery_pending"]:
        delivery = f"<p><strong>{escape(DELIVERY_NEED)}</strong></p>"
    else:
        delivery = (
            "<p>Endereço de entrega:</p>"
            f"<p>{escape(ctx['address']).replace(chr(10), '<br>')}</p>"
        )
    lead = (
        f"A Loja aceitou o pedido <strong>{escape(ctx['ref'])}</strong> "
        f"e reservou a data confirmada {escape(ctx['date'])}."
    )
    status = (
        "O pagamento já foi recebido. Isso ainda não significa que o pão está em produção ou entregue."
        if ctx["paid"]
        else "Aceite ainda não significa pago, em produção ou entregue."
    )
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<body style="margin:0;padding:0;background:#faf8f2;color:#36392e;font-family:Georgia,serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#faf8f2;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#fffdf9;border:1px solid #deddd2;padding:28px 24px;">
        <tr><td>
          <img src="{escape(ctx['logo'])}" alt="Loja de Pães" width="220" style="display:block;max-width:220px;width:100%;height:auto;border:0;">
        </td></tr>
        <tr><td style="padding-top:20px;font-size:16px;line-height:1.6;">
          <p style="margin:0 0 16px;">Olá, {escape(ctx['name'])}.</p>
          <p style="margin:0 0 12px;">{lead}</p>
          <p style="margin:0 0 16px;">{escape(status)}</p>
          <p style="margin:0 0 8px;"><strong>Itens</strong></p>
          <ul style="margin:0 0 16px;padding-left:20px;">{items}</ul>
          <p style="margin:0 0 8px;">Total: <strong>{escape(ctx['total'])}</strong></p>
          <p style="margin:0 0 16px;">Horário solicitado: {escape(ctx['preferred_time'])}</p>
          {delivery}
          {pending_html}
          <p style="margin:24px 0;">
            <a href="{escape(ctx['link'])}" style="display:inline-block;background:#98533c;color:#fff;text-decoration:none;padding:14px 20px;border-radius:3px;font-family:Arial,sans-serif;font-size:16px;">{escape(ctx['cta'])}</a>
          </p>
          <p style="margin:0 0 8px;font-size:15px;">Neste mesmo endereço você paga (se ainda faltar), acompanha o andamento e completa os dados de entrega, se faltarem.</p>
          <p style="margin:16px 0 0;font-size:14px;word-break:break-all;">Se o botão não abrir: {escape(ctx['link'])}</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def render_order_accepted_parts(
    session: Session, settings: Settings, order: Order
) -> tuple[str, str, str]:
    ctx = order_customer_context(session, settings, order, "order_accepted")
    subject, text = render_order_accepted_text(ctx)
    return subject, text, render_order_accepted_html(ctx)
