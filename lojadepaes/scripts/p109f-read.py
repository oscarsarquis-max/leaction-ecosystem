"""109F, seÃ§Ã£o 1: por que a cliente caiu na solicitaÃ§Ã£o SDDB6BA3CD.

Somente leitura: tudo roda em BEGIN TRANSACTION READ ONLY e termina em ROLLBACK.
Roda dentro do contÃªiner da API:
    docker compose exec -T -w /app/backend api python - < scripts/p109f-read.py
Imprime referÃªncias, datas, status e contagens. Nunca nome, e-mail, telefone ou texto de cliente.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

for candidate in (Path("/app/backend"), Path(__file__).resolve().parents[1] / "backend"):
    if candidate.exists():
        sys.path.insert(0, str(candidate))
        break

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.domain.bakery_time as bakery_time  # noqa: E402
import app.domain.schedule as schedule  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.domain.attendance import date_request_reference  # noqa: E402
from app.models.date_requests import DateRequest  # noqa: E402
from app.models.orders import Order, OrderItem  # noqa: E402
from app.models.payments import PaymentRecord  # noqa: E402

REQUEST_REF = "SDDB6BA3CD"
ORDER_REF = "LPA39746B92A"


def main() -> int:
    settings = get_settings()
    zone = ZoneInfo(settings.bakery_timezone)
    with Session(get_engine()) as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        try:
            request = next(
                (row for row in session.scalars(select(DateRequest)) if date_request_reference(row.id) == REQUEST_REF),
                None,
            )
            order = session.scalar(select(Order).where(Order.public_reference == ORDER_REF))
            if request is None or order is None:
                print("nao encontrado", request is not None, order is not None)
                return 1
            created = request.created_at.astimezone(zone)
            print("solicitacao", REQUEST_REF, "status", request.status, "criada", created.strftime("%d/%m %H:%M"))
            print("  data desejada", request.desired_date, "cart_context", "SIM" if request.cart_context else "NAO",
                  "linhas", len(request.cart_context or []), "qtd", request.intended_quantity)
            for line in request.cart_context or []:
                print("  linha", line.get("product_name"), "|", line.get("variant_name"), "x", line.get("quantity"))
            print("  idempotency_key", (request.idempotency_key or "")[:6] + "â€¦", "converted_order_id", request.converted_order_id)
            print("pedido", ORDER_REF, "status", order.status, "criado",
                  order.created_at.astimezone(zone).strftime("%d/%m %H:%M"),
                  "data de producao", order.production_local_date, "holds_capacity", order.holds_capacity)
            print("  origem", "solicitacao" if order.source_date_request_id else "vitrine",
                  "| pagamentos", [(p.financial_status, p.expected_cents) for p in session.scalars(
                      select(PaymentRecord).where(PaymentRecord.order_id == order.id))])
            items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id)))
            print("  itens", [(i.dough_name_snapshot, i.shape_name_snapshot, i.quantity, i.physical_units) for i in items])

            fixed = created.replace(second=0, microsecond=0)
            bakery_time.bakery_now = lambda _s: fixed  # type: ignore[assignment]
            bakery_time.bakery_today = lambda _s: fixed.date()  # type: ignore[assignment]
            schedule.bakery_now = bakery_time.bakery_now  # type: ignore[attr-defined]
            schedule.bakery_today = bakery_time.bakery_today  # type: ignore[attr-defined]
            import app.domain.schedule_closures as closures
            closures.bakery_today = bakery_time.bakery_today  # type: ignore[attr-defined]
            lines = [
                schedule.ProposedLine(kind="product", quantity=int(line["quantity"]), variant_id=line["variant_id"])
                for line in (request.cart_context or [])
            ]
            from uuid import UUID

            lines = [
                schedule.ProposedLine(kind="product", quantity=line.quantity, variant_id=UUID(str(line.variant_id)))
                for line in lines
            ]
            resolved = schedule.resolve_proposed_lines(session, lines)
            day = schedule.evaluate_day(session, settings, request.desired_date, resolved)
            row = schedule.ensure_schedule_settings(session)
            own = sum(int(i.physical_units if i.physical_units is not None else i.quantity) for i in items)
            own_counts = bool(order.holds_capacity and order.production_local_date == request.desired_date)
            before = day.committed_physical - (own if own_counts else 0)
            print(f"vitrine as {fixed.strftime('%d/%m %H:%M')} para {request.desired_date}:")
            print("  status", day.status, "motivo", day.reason, "elegivel", day.eligible_for_selection)
            print("  antecedencia minima (h)", row.min_advance_hours, "| limite fisico", day.daily_physical_limit,
                  "| comprometido agora", day.committed_physical, "| sem o pedido LPA", before,
                  "| restante antes do LPA", max(day.daily_physical_limit - before, 0))
            print("  limite de bases", day.daily_base_limit, "| fechamento por periodo:",
                  "sim" if schedule_closures_block(session, request.desired_date) else "nao")
        finally:
            session.rollback()
    print("ROLLBACK ok")
    return 0


def schedule_closures_block(session: Session, day) -> bool:
    from app.domain.schedule_closures import matching_date_block

    return matching_date_block(session, day) is not None


if __name__ == "__main__":
    raise SystemExit(main())
