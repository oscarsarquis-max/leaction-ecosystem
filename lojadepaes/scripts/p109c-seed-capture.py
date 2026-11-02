"""Acrescenta no lojadepaes_capture os casos visuais do 109C. Dados só de exemplo.

Não apaga nada. Recusa qualquer URL que não seja 127.0.0.1/localhost com o banco
lojadepaes_capture. Escreve readme/evidence/prompt-109c/capture-ids.json.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
CAPTURE_URL = "postgresql+psycopg://lojadepaes:lojadepaes_dev@127.0.0.1:5438/lojadepaes_capture"
OUT = ROOT / "readme" / "evidence" / "prompt-109c" / "capture-ids.json"


def assert_capture_target(url: str) -> None:
    from sqlalchemy.engine.url import make_url

    parsed = make_url(url)
    if (parsed.host or "").lower() not in {"127.0.0.1", "localhost"} or parsed.database != "lojadepaes_capture":
        raise SystemExit("recusando seed: não é o banco de captura local")


def next_weekday(start: date, weekday: int) -> date:
    return start + timedelta(days=(weekday - start.weekday()) % 7)


def main() -> None:
    assert_capture_target(CAPTURE_URL)
    os.environ["LOJADEPAES_DATABASE_URL"] = CAPTURE_URL
    os.environ["LOJADEPAES_PUBLIC_PAYMENTS_ENABLED"] = "false"
    os.environ["LOJADEPAES_MAIL_IDENTITY_READY"] = "false"
    sys.path.insert(0, str(BACKEND))

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from app.core.config import get_settings
    from app.domain.bakery_time import bakery_today
    from app.domain.schedule import save_date_override
    from app.models.date_requests import DateRequest
    from app.models.orders import Order, OrderItem
    from app.models.payments import PaymentRecord

    get_settings.cache_clear()
    settings = get_settings()
    engine = create_engine(CAPTURE_URL, pool_pre_ping=True)
    session = sessionmaker(bind=engine)()
    ids: dict[str, str] = {}
    try:
        source = session.scalar(select(Order).where(Order.customer_email.like("%@example.test")).limit(1))
        if source is None:
            raise SystemExit("capture sem pedido de exemplo")
        item = session.scalar(select(OrderItem).where(OrderItem.order_id == source.id).limit(1))
        today = bakery_today(settings)
        wednesday = next_weekday(today + timedelta(days=7), 2)
        saturday = wednesday + timedelta(days=3)
        friday = wednesday + timedelta(days=2)
        full_day = saturday + timedelta(days=7)

        def make(reference: str, *, email: str, name: str, status: str, produced: date,
                 pay: str | None, requested: date | None = None, created_hours_ago: int = 1,
                 **extra) -> Order:
            found = session.scalar(select(Order).where(Order.public_reference == reference))
            if found is not None:
                ids[reference] = str(found.id)
                return found
            data = {
                c.name: getattr(source, c.name)
                for c in Order.__table__.columns
                if c.name not in {"id", "created_at", "updated_at"}
            }
            now = datetime.now(UTC)
            data.update(
                public_reference=reference,
                submit_idempotency_key=f"p109c-{reference}",
                access_token_hash=None,
                fidelity_account_id=None,
                fidelity_campaign_id=None,
                fidelity_credit_id=None,
                source_date_request_id=None,
                customer_email=email,
                customer_name=name,
                status=status,
                holds_capacity=status in {"confirmed", "in_production", "ready", "completed"},
                production_local_date=produced,
                requested_date=requested or produced,
                date_change_origin=None,
                date_change_reason=None,
                date_change_actor=None,
                proposed_production_date=None,
                cancellation_reason=None,
                cancelled_at=None,
                production_started_at=None,
                delivery_confirmed_at=None,
                created_at=now - timedelta(hours=created_hours_ago),
            )
            data.update(extra)
            order = Order(**data)
            session.add(order)
            session.flush()
            session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    product_variant_id=item.product_variant_id,
                    recipe_base_id=item.recipe_base_id,
                    quantity=1,
                    physical_units=1,
                    dough_name_snapshot=item.dough_name_snapshot or "Pão de Café 500 g",
                    shape_name_snapshot=item.shape_name_snapshot,
                    unit_price_cents=item.unit_price_cents,
                    line_total_cents=item.line_total_cents,
                    net_weight_grams=item.net_weight_grams or 500,
                )
            )
            if pay:
                paid = pay == "paid"
                session.add(
                    PaymentRecord(
                        order_id=order.id,
                        provider="actionhub",
                        external_reference=f"capture-{reference}" if paid else None,
                        idempotency_key=f"p109c-{reference}",
                        expected_cents=order.total_cents or 0,
                        currency="BRL",
                        financial_status="paid" if paid else "pending",
                        amount_paid_cents=order.total_cents if paid else None,
                        method="pix" if paid else None,
                    )
                )
            session.flush()
            ids[reference] = str(order.id)
            return order

        # Reagendar: confirmado pago em dia normal; concluído para a correção de registro.
        make("LPC109NORMAL", email="normal@example.test", name="Cliente Exemplo Normal",
             status="confirmed", produced=wednesday, pay="paid")
        make("LPC109CONCL", email="concluido@example.test", name="Cliente Exemplo Concluído",
             status="completed", produced=today - timedelta(days=1), pay="paid",
             production_started_at=datetime.now(UTC) - timedelta(days=2),
             delivery_confirmed_at=datetime.now(UTC) - timedelta(days=1))
        # Dia cheio: um pão ocupa o único lugar do sábado seguinte.
        make("LPC109CHEIO", email="cheio@example.test", name="Cliente Exemplo Cheio",
             status="confirmed", produced=full_day, pay="paid")
        save_date_override(
            session, settings, full_day,
            open_state="open", daily_physical_limit=1, daily_base_limit=None,
            eligibility_mode="inherit", eligible_base_ids=None,
        )
        # Possível duplicidade: dois pedidos do mesmo cliente com os mesmos itens.
        make("LPC109DUPA", email="repetido@example.test", name="Cliente Exemplo Repetido",
             status="confirmed", produced=saturday, pay="paid", created_hours_ago=5)
        make("LPC109DUPB", email="repetido@example.test", name="Cliente Exemplo Repetido",
             status="confirmed", produced=saturday, pay="pending", created_hours_ago=3)
        # Anulado e original, com exceção de data registrada (caso de 30/10 em escala).
        orig = make("LPC109ORIG", email="orig@example.test", name="Cliente Exemplo Original",
                    status="completed", produced=today - timedelta(days=2), pay="paid",
                    requested=today, created_hours_ago=30,
                    date_change_origin="customer",
                    date_change_reason="Antecipação combinada com o cliente",
                    date_change_actor="admin:exemplo",
                    production_started_at=datetime.now(UTC) - timedelta(days=3),
                    delivery_confirmed_at=datetime.now(UTC) - timedelta(days=2))
        dup = make("LPC109ANUL", email="orig2@example.test", name="Cliente Exemplo Original",
                   status="completed", produced=today - timedelta(days=2), pay="pending",
                   created_hours_ago=28,
                   production_started_at=datetime.now(UTC) - timedelta(days=3),
                   delivery_confirmed_at=datetime.now(UTC) - timedelta(days=2))
        # Pedido existente do mesmo cliente de uma solicitação de data.
        make("LPC109EXIST", email="existente@example.test", name="Cliente Exemplo Existente",
             status="confirmed", produced=saturday, pay="paid")
        make("LPC109EXIST2", email="segundo@example.test", name="Cliente Exemplo Segundo",
             status="confirmed", produced=saturday, pay="paid")
        # Ensaio da seção E: par no formato do caso de 30/10 (pago e pendente, mesmo nome, e-mails diferentes).
        make("LPC109ENSAIOA", email="ensaio-a@example.test", name="Cliente Exemplo Ensaio",
             status="completed", produced=today + timedelta(days=1), pay="paid",
             requested=today + timedelta(days=1), created_hours_ago=2,
             production_started_at=datetime.now(UTC) - timedelta(hours=3),
             delivery_confirmed_at=datetime.now(UTC) - timedelta(hours=1))
        make("LPC109ENSAIOB", email="ensaio-b@example.test", name="Cliente Exemplo Ensaio",
             status="completed", produced=today, pay="pending", created_hours_ago=1,
             production_started_at=datetime.now(UTC) - timedelta(hours=3),
             delivery_confirmed_at=datetime.now(UTC) - timedelta(hours=1))
        session.commit()

        from app.domain.void_duplicate import void_duplicate

        try:
            void_duplicate(
                session, dup.id, original_order_id=orig.id,
                reason="Criado pelo aceite da solicitação; a encomenda real é a original.",
                actor_ref="admin:exemplo",
            )
            session.commit()
        except Exception as error:  # já anulado em execução anterior
            session.rollback()
            print("anulação:", str(error)[:120])

        def ensure_request(key: str, desired: date, message: str,
                           email: str = "existente@example.test",
                           name: str = "Cliente Exemplo Existente") -> DateRequest:
            found = session.scalar(select(DateRequest).where(DateRequest.idempotency_key == key))
            if found is None:
                found = DateRequest(
                    desired_date=desired,
                    customer_name=name,
                    customer_email=email,
                    intended_quantity=1,
                    message=message,
                    status="pending",
                    idempotency_key=key,
                    client_host="127.0.0.1",
                )
                session.add(found)
                session.commit()
            return found

        # Uma solicitação só para fotografar (nunca é acionada) e outra para o fluxo de mover.
        ids["date_request_existente"] = str(
            ensure_request("p109c-existente-vitrine", friday, "Posso antecipar para sexta? Exemplo.").id
        )
        ids["date_request_mover"] = str(
            ensure_request(
                "p109c-existente-mover-c", saturday + timedelta(days=14), "Pode ser no outro sábado? Exemplo.",
                email="segundo@example.test", name="Cliente Exemplo Segundo",
            ).id
        )
        ids["dates"] = json.dumps(
            {"quarta": wednesday.isoformat(), "sabado": saturday.isoformat(),
             "sexta_fechada": friday.isoformat(), "dia_cheio": full_day.isoformat()}
        )
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(ids, ensure_ascii=False, indent=2), encoding="utf-8")
        print("capture 109c atualizado")
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
