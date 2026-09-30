from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.ses_mailer import send_outbox_email
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.orders import Order, OrderItem

TEMPLATES = {
    "order_submitted": (
        "Recebemos sua solicitação — {date}",
        "Recebemos o pedido {ref}.\n\n"
        "Data pedida: {date}.\n"
        "Horário solicitado: {preferred_time}.\n"
        "Essa data ainda não está reservada. Depois do pagamento, vamos conferir "
        "e confirmar a fornada por e-mail.\n\n"
        "Endereço de entrega:\n{address}\n\n"
        "Acompanhe o pedido neste endereço protegido:\n{link}",
    ),
    "payment_approved": (
        "Pagamento recebido — {date}",
        "O pagamento do pedido {ref} foi aprovado. Isso ainda não confirma a data da fornada.\n\n"
        "Data pedida: {date}.\n"
        "Horário solicitado: {preferred_time}.\n\n"
        "Endereço de entrega:\n{address}\n\n"
        "Acompanhe o pedido neste endereço protegido:\n{link}",
    ),
    "order_accepted": (
        "Data da fornada confirmada — {date}",
        "A Loja aceitou o pedido {ref} e reservou a data confirmada {date}.\n"
        "Horário solicitado: {preferred_time}. Esse horário é uma preferência e só vale se A Loja confirmar.\n\n"
        "Endereço de entrega:\n{address}\n\n"
        "Acompanhe o pedido neste endereço protegido:\n{link}",
    ),
    "order_submitted_admin": (
        "Nova solicitação {ref} — Loja de Pães",
        "Chegou uma solicitação {ref} aguardando avaliação.\n"
        "Data pedida: {date}.\n"
        "Total: {total}.\n\n"
        "Abra o detalhe no painel autorizado:\n{admin_link}\n\n"
        "A composição completa e o contato estão só no painel.",
    ),
    "date_request_received": (
        "Solicitação de data — Loja de Pães",
        "Recebemos sua solicitação de data {date}. "
        "Isso ainda não confirma a fornada. Vamos avaliar a possibilidade e responder por e-mail.",
    ),
    "date_request_proposed": (
        "Proposta de data — Loja de Pães",
        "A Loja avaliou sua solicitação de data e propôs {date}. "
        "Essa proposta ainda não confirma a fornada nem reserva vaga.",
    ),
    "adaptation_proposed": (
        "Proposta de adaptação — Loja de Pães",
        "A Loja avaliou uma solicitação de adaptação no pedido {ref}. "
        "Acesse a página protegida do pedido para ver a proposta e responder: {link} "
        "Silêncio não confirma a alteração nem a data da fornada.",
    ),
}

MAX_ATTEMPTS = 5


_WEEKDAYS = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)
_MONTHS = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def format_customer_date(value: date | None) -> str:
    if value is None:
        return "a combinar"
    return (
        f"{_WEEKDAYS[value.weekday()]}, {value.day} de {_MONTHS[value.month - 1]} de {value.year}"
    )


def delivery_address_text(order: Order) -> str:
    if not order.delivery_street:
        return "ainda não informado"
    complement = f", {order.delivery_complement}" if order.delivery_complement else ""
    postal = order.delivery_postal_code or ""
    if len(postal) == 8 and postal.isdigit():
        postal = f"{postal[:5]}-{postal[5:]}"
    return (
        f"{order.delivery_street}, {order.delivery_number}{complement}\n"
        f"{order.delivery_district} — {order.delivery_city}/{order.delivery_state}\n"
        f"CEP {postal}"
    )


def _brl(cents: int | None) -> str:
    value = int(cents or 0)
    return f"R$ {value / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def order_has_custom_item(session: Session, order: Order) -> bool:
    return (
        session.scalar(
            select(OrderItem.id)
            .where(OrderItem.order_id == order.id, OrderItem.product_variant_id.is_(None))
            .limit(1)
        )
        is not None
    )


def _date_for(order: Order, kind: str) -> str:
    if kind == "order_accepted" and order.production_local_date is not None:
        return format_customer_date(order.production_local_date)
    if kind == "order_submitted":
        requested = order.production_local_date or order.proposed_production_date
        if requested is not None:
            return format_customer_date(requested)
    if order.production_local_date is not None:
        return format_customer_date(order.production_local_date)
    return "a combinar"


def _rendered(session: Session, settings: Settings, order: Order, kind: str) -> tuple[str, str]:
    subject, body = TEMPLATES[kind]
    date_txt = _date_for(order, kind)
    from app.domain.storefront_orders import protected_order_url

    link = protected_order_url(settings, order)
    address = delivery_address_text(order)
    preferred = (
        f"{order.preferred_time.strftime('%H:%M')} (preferência; ainda não confirmado)"
        if order.preferred_time
        else "Sem preferência informada"
    )
    values = {
        "ref": order.public_reference,
        "date": date_txt,
        "preferred_time": preferred,
        "link": link,
        "address": address,
        "total": _brl(order.total_cents),
        "admin_link": f"{settings.public_origin.rstrip('/')}/admin/pedidos/{order.id}",
    }
    custom = order_has_custom_item(session, order)
    if kind == "order_submitted" and custom:
        return (
            f"Recebemos sua solicitação — {date_txt}",
            (
                "Recebemos o pedido {ref}. A Loja ainda vai avaliar a composição.\n\n"
                "Data pedida: {date}. Isso ainda não reserva a fornada nem confirma o aceite.\n"
                "Horário solicitado: {preferred_time}.\n\n"
                "Acompanhe o pedido neste endereço protegido:\n{link}"
            ).format(**values),
        )
    if kind == "order_accepted" and custom:
        return (
            "Seu pão foi aceito — prossiga para o pagamento",
            (
                "A Loja aceitou o pedido {ref} e reservou a data {date}.\n"
                "Total: {total}.\n"
                "Horário solicitado: {preferred_time}.\n\n"
                "Prossiga para o pagamento neste endereço protegido:\n{link}\n"
                "Aceite ainda não significa pago."
            ).format(**values),
        )
    if kind == "payment_approved" and (
        order.holds_capacity or order.status in {"confirmed", "in_production", "ready", "completed"}
    ):
        return (
            f"Pagamento recebido — {date_txt}",
            (
                "O pagamento do pedido {ref} foi recebido. A data {date} já está reservada.\n"
                "Horário solicitado: {preferred_time}.\n\n"
                "Endereço de entrega:\n{address}\n\n"
                "Acompanhe o pedido neste endereço protegido:\n{link}"
            ).format(**values),
        )
    if kind == "order_submitted":
        from app.domain.adaptations import order_has_pending_adaptation

        if order_has_pending_adaptation(session, order.id):
            body = (
                body
                + "\n\nHá uma solicitação de adaptação pendente de avaliação. "
                "Isso ainda não confirma a alteração. Os detalhes estão na página protegida do pedido."
            )
    return subject.format(**values), body.format(**values)


def enqueue_order_email(
    session: Session, settings: Settings, order: Order, kind: str
) -> EmailOutbox:
    subject, body = _rendered(session, settings, order, kind)
    to_address = (order.customer_email or "").strip()
    if not to_address or "@" not in to_address:
        raise ValueError("pedido sem e-mail para notificação")
    ready = settings.mail_transport_ready
    status = "pending" if ready else "skipped"
    last_error = (
        None
        if ready
        else "identidade SES ainda não verificada; mensagem não enviada"
        if settings.mail_from.strip()
        else "serviço de e-mail não configurado; mensagem não enviada"
    )
    dedupe_key = f"{order.id}:{kind}"
    existing = session.scalar(select(EmailOutbox).where(EmailOutbox.dedupe_key == dedupe_key))
    if existing is not None:
        return existing
    row = EmailOutbox(
        order_id=order.id,
        kind=kind,
        to_address=to_address,
        subject=subject,
        body=body,
        status=status,
        attempts=0,
        last_error=last_error,
        dedupe_key=dedupe_key,
    )
    session.add(row)
    session.flush()
    return row


def enqueue_admin_order_email(session: Session, settings: Settings, order: Order) -> EmailOutbox:
    kind = "order_submitted_admin"
    dest = (settings.mail_ops_to or "").strip()
    configured = bool(dest) and "@" in dest
    ready = settings.mail_transport_ready and configured
    if not configured:
        last_error = "destinatário administrativo não configurado; mensagem não enviada"
        to_address = "ops-unconfigured"
    elif not settings.mail_transport_ready:
        last_error = (
            "identidade SES ainda não verificada; mensagem não enviada"
            if settings.mail_from.strip()
            else "serviço de e-mail não configurado; mensagem não enviada"
        )
        to_address = dest
    else:
        last_error = None
        to_address = dest
    status = "pending" if ready else "skipped"
    subject, body = _rendered(session, settings, order, kind)
    dedupe_key = f"{order.id}:{kind}"
    existing = session.scalar(select(EmailOutbox).where(EmailOutbox.dedupe_key == dedupe_key))
    if existing is not None:
        return existing
    row = EmailOutbox(
        order_id=order.id,
        kind=kind,
        to_address=to_address,
        subject=subject,
        body=body,
        status=status,
        attempts=0,
        last_error=last_error,
        dedupe_key=dedupe_key,
    )
    session.add(row)
    session.flush()
    return row


def refresh_order_email(
    session: Session, settings: Settings, order: Order, kind: str
) -> EmailOutbox:
    """Reescreve um aviso já gravado e reenvia só se ele já tinha saído."""
    row = session.scalar(
        select(EmailOutbox).where(EmailOutbox.dedupe_key == f"{order.id}:{kind}")
    )
    if row is None:
        return enqueue_order_email(session, settings, order, kind)
    subject, body = _rendered(session, settings, order, kind)
    row.subject = subject
    row.body = body
    if row.status == "sent":
        row.status = "pending"
        row.attempts = 0
        row.sent_at = None
        row.provider_message_id = None
        row.last_error = None
    session.flush()
    return row


def enqueue_date_request_email(
    session: Session, settings: Settings, request: DateRequest, kind: str
) -> EmailOutbox:
    subject, body = TEMPLATES[kind]
    date_txt = (
        request.proposed_date.isoformat()
        if kind == "date_request_proposed" and request.proposed_date is not None
        else request.desired_date.isoformat()
    )
    to_address = (request.customer_email or "").strip()
    if not to_address or "@" not in to_address:
        raise ValueError("solicitação sem e-mail para notificação")
    ready = settings.mail_transport_ready
    status = "pending" if ready else "skipped"
    last_error = (
        None
        if ready
        else "identidade SES ainda não verificada; mensagem não enviada"
        if settings.mail_from.strip()
        else "serviço de e-mail não configurado; mensagem não enviada"
    )
    dedupe_key = f"{request.id}:{kind}"
    existing = session.scalar(select(EmailOutbox).where(EmailOutbox.dedupe_key == dedupe_key))
    if existing is not None:
        return existing
    row = EmailOutbox(
        order_id=None,
        date_request_id=request.id,
        kind=kind,
        to_address=to_address,
        subject=subject.format(ref="", date=date_txt),
        body=body.format(ref="", date=date_txt),
        status=status,
        attempts=0,
        last_error=last_error,
        dedupe_key=dedupe_key,
    )
    session.add(row)
    session.flush()
    return row


def process_due_outbox(
    session: Session, settings: Settings, *, limit: int = 20
) -> list[EmailOutbox]:
    rows = list(
        session.scalars(
            select(EmailOutbox)
            .where(EmailOutbox.status.in_(("pending", "failed")))
            .where(EmailOutbox.attempts < MAX_ATTEMPTS)
            .order_by(EmailOutbox.created_at.asc())
            .limit(limit)
        )
    )
    processed: list[EmailOutbox] = []
    for row in rows:
        _deliver_row(session, settings, row)
        processed.append(row)
    return processed


def _deliver_row(session: Session, settings: Settings, row: EmailOutbox) -> None:
    row.attempts += 1
    if not settings.mail_transport_ready:
        row.status = "failed"
        row.last_error = "serviço de e-mail não configurado; mensagem não enviada"
        session.flush()
        return
    result = send_outbox_email(
        settings,
        to_address=row.to_address,
        subject=row.subject,
        body=row.body,
    )
    if result.accepted:
        row.status = "sent"
        row.sent_at = datetime.now(UTC)
        row.last_error = None
        row.provider_message_id = result.message_id
        session.flush()
        return
    row.last_error = result.error or "falha ao enviar"
    if row.attempts >= MAX_ATTEMPTS:
        row.status = "failed"
    else:
        row.status = "failed"
    session.flush()
