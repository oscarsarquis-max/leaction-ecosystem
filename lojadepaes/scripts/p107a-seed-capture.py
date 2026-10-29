"""Recria o banco local lojadepaes_capture e semeia o backoffice pelos caminhos de domínio.

Recusa qualquer URL que não seja 127.0.0.1/localhost com o banco lojadepaes_capture.
Não envia e-mail, push nem cobrança real. Reexecutar: python scripts/p107a-seed-capture.py
Provar a recusa: python scripts/p107a-seed-capture.py --prove-refusal
"""

from __future__ import annotations

import io
import json
import os
import sys
from datetime import timedelta
from pathlib import Path

from sqlalchemy.engine.url import make_url

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
CAPTURE_URL = "postgresql+psycopg://lojadepaes:lojadepaes_dev@127.0.0.1:5438/lojadepaes_capture"
MAINTENANCE_URL = "postgresql+psycopg://lojadepaes:lojadepaes_dev@127.0.0.1:5438/lojadepaes"
MANIFEST = ROOT / "readme" / "evidence" / "prompt-107" / "capture-ids.json"
ADDRESS = {
    "delivery_street": "Rua Exemplo",
    "delivery_number": "100",
    "delivery_complement": "",
    "delivery_district": "Aldeota",
    "delivery_city": "Fortaleza",
    "delivery_state": "CE",
    "delivery_postal_code": "60150160",
}


def assert_capture_target(url: str) -> None:
    parsed = make_url(url)
    host = (parsed.host or "").lower()
    name = parsed.database or ""
    lowered = url.lower()
    if host not in {"127.0.0.1", "localhost"} or name != "lojadepaes_capture":
        raise SystemExit(
            f"recusando seed: a URL precisa ser 127.0.0.1 ou localhost "
            f"e o banco lojadepaes_capture (recebido {host or 'sem host'}/{name or 'sem nome'})"
        )
    if any(token in lowered for token in ("amazonaws.com", "production", "mercadopago")):
        raise SystemExit("recusando seed: a URL parece produção")


def prove_refusal() -> None:
    samples = [
        "postgresql+psycopg://lojadepaes:lojadepaes_dev@127.0.0.1:5438/lojadepaes",
        "postgresql+psycopg://lojadepaes:lojadepaes_dev@192.168.0.20:5438/lojadepaes_capture",
        CAPTURE_URL,
    ]
    for sample in samples:
        try:
            assert_capture_target(sample)
        except SystemExit as exc:
            print(f"RECUSOU {sample}: {exc}")
            continue
        if sample != CAPTURE_URL:
            raise SystemExit(f"a guarda aceitou uma URL proibida: {sample}")
        print(f"ACEITOU {sample}")


def _png() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), (196, 164, 108)).save(buffer, format="PNG")
    return buffer.getvalue()


def _recreate_database() -> None:
    from sqlalchemy import create_engine, text

    assert_capture_target(CAPTURE_URL)
    maintenance = make_url(MAINTENANCE_URL)
    if (maintenance.host or "").lower() not in {"127.0.0.1", "localhost"}:
        raise SystemExit("recusando seed: a conexão de manutenção não é local")
    if maintenance.database != "lojadepaes":
        raise SystemExit("recusando seed: a manutenção só pode usar o banco lojadepaes")
    engine = create_engine(MAINTENANCE_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = 'lojadepaes_capture' AND pid <> pg_backend_pid()"
            )
        )
        connection.execute(text("DROP DATABASE IF EXISTS lojadepaes_capture"))
        connection.execute(text("CREATE DATABASE lojadepaes_capture"))
    engine.dispose()


def _upgrade() -> None:
    from alembic import command
    from alembic.config import Config

    os.environ["LOJADEPAES_DATABASE_URL"] = CAPTURE_URL
    ini = ROOT / "database" / "alembic.ini"
    config = Config(str(ini))
    config.set_main_option("script_location", str(ini.parent / "migrations"))
    command.upgrade(config, "head")


def main() -> None:
    if "--prove-refusal" in sys.argv:
        prove_refusal()
        return
    assert_capture_target(CAPTURE_URL)
    os.environ["LOJADEPAES_DATABASE_URL"] = CAPTURE_URL
    os.environ["LOJADEPAES_PUBLIC_PAYMENTS_ENABLED"] = "false"
    os.environ["LOJADEPAES_HOUSE_FIDELITY_ACTIVE"] = "true"
    os.environ["LOJADEPAES_CUSTOMER_IDENTITY_SECRET"] = "capture-107a-local-only-secret-32b"
    os.environ["LOJADEPAES_MAIL_IDENTITY_READY"] = "false"
    os.environ["LOJADEPAES_ACTIONHUB_APP_SECRET"] = ""
    os.environ["LOJADEPAES_ACTIONHUB_BASE_URL"] = "http://127.0.0.1:9"
    os.environ["LOJADEPAES_MEDIA_DIR"] = str(ROOT / "var" / "media")
    sys.path.insert(0, str(BACKEND))
    _recreate_database()
    from app.core.config import get_settings

    get_settings.cache_clear()
    _upgrade()
    get_settings.cache_clear()
    _seed()


def _seed() -> None:
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from app.core.config import get_settings
    from app.domain.bakery_time import bakery_today
    from app.domain.date_request_accept import accept_date_request
    from app.domain.date_requests import apply_date_request_action, create_date_request
    from app.domain.house_fidelity import activate_campaign
    from app.domain.house_fidelity_admin import apply_manual_adjustment
    from app.domain.house_fidelity_ledger import reconcile_order
    from app.domain.orders import add_internal_note, confirm_delivery, start_production, transition_order
    from app.domain.payment_webhooks import apply_actionhub_observation
    from app.domain.products import archive_product, attach_image, create_product, publish_product
    from app.domain.recipe_bases import create_recipe_base
    from app.domain.schedule_closures import upsert_closure
    from app.domain.showcase import assign_slot
    from app.domain.storefront_orders import propose_production_date, quote_lines, start_checkout, submit_order
    from app.domain.week_recipes import attach_image as attach_recipe_image
    from app.domain.week_recipes import create_recipe, publish_recipe
    from app.models.email_outbox import EmailOutbox
    from app.models.enums import OrderStatus
    from app.models.payments import PaymentRecord
    from app.schemas.products import IngredientIn, ProductSaveIn, VariantIn
    from app.schemas.suggestions import DateRequestActionIn, DateRequestCreateIn, DateRequestLineIn
    from app.seed import seed_demo_catalog

    settings = get_settings()
    engine = create_engine(CAPTURE_URL, pool_pre_ping=True)
    session = sessionmaker(bind=engine)()
    actor = "admin:captura"
    today = bakery_today(settings)
    wednesday = today + timedelta(days=(2 - today.weekday()) % 7 or 7)
    if wednesday <= today:
        wednesday += timedelta(days=7)
    later = wednesday + timedelta(days=14)
    png = _png()

    def product_payload(name: str, slug: str, base_id) -> ProductSaveIn:
        return ProductSaveIn(
            name=name,
            slug=slug,
            short_description="Pão de exemplo para a captura do backoffice.",
            featured_image_alt=f"Foto de exemplo de {name}",
            featured_image_caption="Foto de exemplo",
            fidelity_eligible=True,
            recipe_base_id=base_id,
            ingredients=[IngredientIn(name="Farinha de exemplo")],
            variants=[
                VariantIn(
                    display_name="500 g",
                    presentation_type="weight",
                    net_weight_grams=500,
                    physical_units=1,
                    price_cents=2490,
                ),
                VariantIn(
                    display_name="Pacote com 4",
                    presentation_type="pack",
                    units_per_pack=4,
                    physical_units=1,
                    price_cents=4800,
                ),
            ],
        )

    def place(name: str, email: str, key: str, items: list[dict], *, day=None, account=None) -> object:
        payload = {
            "requested_date": (day or wednesday).isoformat(),
            "items": items,
            "customer_name": name,
            "customer_email": email,
            "idempotency_key": key,
            **ADDRESS,
        }
        if account is not None:
            payload["fidelity_opt_in"] = True
            payload["_fidelity_account"] = account
        payload["quoted_cents"] = quote_lines(session, settings, payload)["total_cents"]
        order, _token = submit_order(session, settings, payload)
        session.flush()
        return order

    def pay(order) -> None:
        start_checkout(session, settings, order, "pix")
        session.flush()
        record = session.scalar(
            select(PaymentRecord).where(
                PaymentRecord.order_id == order.id, PaymentRecord.financial_status == "pending"
            )
        )
        apply_actionhub_observation(
            session,
            settings,
            {
                "app_id": settings.actionhub_app_id,
                "outbox_id": f"capture-{order.public_reference}",
                "event_type": "PAYMENT_CONFIRMED",
                "payload": {
                    "order_id": record.external_reference,
                    "order_reference": order.public_reference,
                    "financial_status": "paid",
                    "paid_amount_cents": order.total_cents,
                    "mp_payment_id": f"mp-capture-{order.public_reference}",
                    "mp_status": "approved",
                    "method": "pix",
                },
            },
        )
        session.flush()

    catalog_seed = "aplicado"
    try:
        try:
            seed_demo_catalog(session)
            session.flush()
        except Exception as exc:
            session.rollback()
            catalog_seed = (
                "não reaplicado: o Alembic já deixa o slug nozes e o seed_demo_catalog "
                f"insere de novo ({type(exc).__name__})"
            )
        base = create_recipe_base(session, code="rb-captura", name="Massa Exemplo")
        session.flush()
        published = []
        for index, name in enumerate(("Pão Exemplo 01", "Pão Exemplo 02", "Pão Exemplo 03"), start=1):
            row = create_product(session, actor, product_payload(name, f"pao-exemplo-0{index}", base.id))
            attach_image(session, settings, row.id, actor, png, f"Foto de exemplo de {name}")
            publish_product(session, row.id, actor)
            published.append(row)
        draft = create_product(session, actor, product_payload("Pão Exemplo Rascunho", "pao-exemplo-rascunho", base.id))
        archived = create_product(
            session, actor, product_payload("Pão Exemplo Arquivado", "pao-exemplo-arquivado", base.id)
        )
        attach_image(session, settings, archived.id, actor, png, "Foto de exemplo arquivada")
        publish_product(session, archived.id, actor)
        archive_product(session, archived.id, actor)
        for position, row in enumerate(published, start=1):
            assign_slot(session, position, row.id)
        recipe = create_recipe(
            session,
            actor,
            {
                "title": "Receita Exemplo da Semana",
                "slug": "receita-exemplo-semana",
                "summary": "Receita de exemplo publicada para a captura.",
                "featured_image_alt": "Foto de exemplo da receita",
                "ingredients": ["Farinha de exemplo"],
                "method_text": "Misture e asse em forno de exemplo.",
                "product_ids": [str(published[0].id)],
            },
        )
        attach_recipe_image(session, settings, recipe.id, actor, png, "Foto de exemplo da receita")
        publish_recipe(session, recipe.id, actor)
        draft_recipe = create_recipe(
            session,
            actor,
            {
                "title": "Receita Exemplo Rascunho",
                "slug": "receita-exemplo-rascunho",
                "summary": "Rascunho de exemplo.",
            },
        )
        activate_campaign(session, settings)
        from datetime import timedelta as _delta
        from app.domain.capacity import utc_now
        from app.domain.house_fidelity import current_campaign

        campaign = current_campaign(session)
        campaign.starts_at = utc_now() - _delta(seconds=30)
        from app.domain.customer_identity import start_signup, verify_code

        start_signup(session, settings, "Cliente Exemplo Fidelidade", "fidelidade@example.test", "390.533.447-05")
        mail = session.scalar(select(EmailOutbox).where(EmailOutbox.kind == "customer_verify"))
        code = mail.body.split("é ", 1)[1].split(".", 1)[0]
        account, _resume = verify_code(session, settings, "fidelidade@example.test", code)
        weight = next(item for item in published[0].variants if item.presentation_type == "weight")
        pack = next(item for item in published[0].variants if item.presentation_type == "pack")
        one = [{"variant_id": str(weight.id), "quantity": 1}]

        def fake_checkout(_settings, prepared):
            return {
                "external_reference": "hub-capture-" + prepared["payment_request_id"][:8],
                "expected_cents": prepared["expected_cents"],
                "reused": False,
                "checkout_url": None,
                "hub_result": None,
            }

        import app.domain.storefront_orders as storefront

        storefront.recover_or_create_checkout = fake_checkout
        opened = place(
            "Cliente Exemplo 01",
            "exemplo01@example.test",
            "capture-aberto",
            [{**one[0], "adaptation": {"text": "sem gergelim de exemplo", "reason": "preference"}}],
        )
        add_internal_note(session, opened.id, "Nota de exemplo para a captura.", actor_ref=actor)
        accepted = place("Cliente Exemplo 02", "exemplo02@example.test", "capture-aceito", one)
        paid = place(
            "Cliente Exemplo 03",
            "exemplo03@example.test",
            "capture-pago",
            one,
            account=account,
        )
        pay(paid)
        session.refresh(paid)
        reconcile_order(session, settings, paid)
        producing = place("Cliente Exemplo 04", "exemplo04@example.test", "capture-producao", one)
        pay(producing)
        start_production(session, producing.id, actor_ref=actor)
        exception = place("Cliente Exemplo 05", "exemplo05@example.test", "capture-excecao", one)
        start_production(session, exception.id, actor_ref=actor, unpaid_exception=True)
        ready = place("Cliente Exemplo 06", "exemplo06@example.test", "capture-pronto", one)
        start_production(session, ready.id, actor_ref=actor, unpaid_exception=True)
        transition_order(session, ready.id, OrderStatus.READY.value, "marcado pronto pelo gestor", actor_ref=actor)
        delivered = place("Cliente Exemplo 07", "exemplo07@example.test", "capture-entregue", one)
        start_production(session, delivered.id, actor_ref=actor, unpaid_exception=True)
        confirm_delivery(session, delivered.id, actor_ref=actor)
        finalized = place("Cliente Exemplo 08", "exemplo08@example.test", "capture-finalizado", one)
        start_production(session, finalized.id, actor_ref=actor, unpaid_exception=True)
        transition_order(session, finalized.id, OrderStatus.READY.value, "marcado pronto pelo gestor", actor_ref=actor)
        transition_order(
            session, finalized.id, OrderStatus.COMPLETED.value, "entregue ou retirado", actor_ref=actor
        )
        cancelled = place("Cliente Exemplo 09", "exemplo09@example.test", "capture-cancelado", one)
        transition_order(
            session, cancelled.id, OrderStatus.CANCELLED.value, "cliente de exemplo desistiu", actor_ref=actor
        )
        sync_fail = place("Cliente Exemplo 11", "exemplo11@example.test", "capture-sync", one)
        start_checkout(session, settings, sync_fail, "pix")
        from app.domain.actionhub_client import HubUnavailableError
        from app.domain.storefront_orders import refresh_open_checkout

        def unavailable(*_args, **_kwargs):
            raise HubUnavailableError("gateway falso: consulta indisponível")

        storefront.reconcile_payment_record = unavailable
        refresh_open_checkout(session, settings, sync_fail.id)
        several = place(
            "Cliente Exemplo 12",
            "exemplo12@example.test",
            "capture-linhas",
            [
                {"variant_id": str(weight.id), "quantity": 1},
                {"variant_id": str(pack.id), "quantity": 1},
            ],
        )
        proposed = place(
            "Cliente Exemplo 14",
            "exemplo14@example.test",
            "capture-proposta",
            [{**one[0], "adaptation": {"text": "casca mais clara de exemplo", "reason": "preference"}}],
        )
        propose_production_date(session, proposed, wednesday + timedelta(days=7))
        dialog = place("Cliente Exemplo 13", "exemplo13@example.test", "capture-dialogo", one)

        def request(name: str, email: str, key: str, day):
            return create_date_request(
                session,
                settings,
                DateRequestCreateIn(
                    desired_date=day,
                    customer_name=name,
                    customer_email=email,
                    intended_quantity=1,
                    message="Solicitação de exemplo.",
                    idempotency_key=key,
                ),
                client_host="127.0.0.1",
            )

        pending = request("Cliente Exemplo Data 01", "data01@example.test", "capture-data-pendente", later)
        alternative = request(
            "Cliente Exemplo Data 02", "data02@example.test", "capture-data-proposta", later + timedelta(days=1)
        )
        apply_date_request_action(
            session,
            settings,
            alternative.id,
            DateRequestActionIn(
                action="propose",
                proposed_date=later + timedelta(days=8),
                note="outra data de exemplo",
            ),
            actor_ref=actor,
        )
        waiting = request(
            "Cliente Exemplo Data 03", "data03@example.test", "capture-data-complemento", later + timedelta(days=2)
        )
        apply_date_request_action(
            session,
            settings,
            waiting.id,
            DateRequestActionIn(action="request_completion", note="faltam os dados de exemplo"),
            actor_ref=actor,
        )
        closed = request("Cliente Exemplo Data 04", "data04@example.test", "capture-data-encerrada", later + timedelta(days=3))
        apply_date_request_action(
            session,
            settings,
            closed.id,
            DateRequestActionIn(action="close", note="encerrada no exemplo da captura"),
            actor_ref=actor,
        )
        converted = request(
            "Cliente Exemplo 10", "exemplo10@example.test", "capture-data-convertida", later + timedelta(days=7)
        )
        accept_date_request(
            session,
            settings,
            converted,
            DateRequestActionIn(
                action="accept",
                lines=[DateRequestLineIn(variant_id=weight.id, quantity=1)],
            ),
            actor_ref=actor,
        )
        upsert_closure(
            session,
            settings,
            start_date=today + timedelta(days=40),
            end_date=today + timedelta(days=46),
            first_eligible_date=today + timedelta(days=47),
            pause_intake=False,
            internal_reason="viagem de exemplo da captura",
            public_notice="Fechamento de exemplo. Não é um aviso real.",
            actor_ref=actor,
        )
        apply_manual_adjustment(
            session,
            settings,
            account_id=str(account.id),
            kind="grant",
            reason="ajuste manual de exemplo da captura",
            actor_ref=actor,
        )
        session.commit()
        manifest = {
            "database": "lojadepaes_capture",
            "catalog_seed": catalog_seed,
            "orders": {
                "aberto": str(opened.id),
                "aceito": str(accepted.id),
                "pago": str(paid.id),
                "em-producao": str(producing.id),
                "excecao": str(exception.id),
                "pronto": str(ready.id),
                "entregue": str(delivered.id),
                "finalizado": str(finalized.id),
                "cancelado": str(cancelled.id),
                "endereco-pendente": str(converted.converted_order_id),
                "verificacao": str(sync_fail.id),
                "varias-linhas": str(several.id),
                "proposta": str(proposed.id),
                "dialogo-cancelamento": str(dialog.id),
            },
            "date_requests": {
                "pendente": str(pending.id),
                "proposta": str(alternative.id),
                "complemento": str(waiting.id),
                "encerrada": str(closed.id),
                "convertida": str(converted.id),
            },
            "products": {
                "publicado": str(published[0].id),
                "rascunho": str(draft.id),
                "arquivado": str(archived.id),
            },
            "fidelity_account": str(account.id),
            "omitted": [
                "Aberto sem data: submit_order grava production_local_date a partir da data cotada "
                "(app/domain/storefront_orders.py, por volta da linha 644). Não há caminho de domínio "
                "que crie um pedido aberto sem essa data."
            ],
        }
        MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(MANIFEST)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
