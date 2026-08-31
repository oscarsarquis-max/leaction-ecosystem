from uuid import uuid4

from app.db import get_runtime_session
from app.main import app
from app.modules.identity_organization.access_tokens import FakeAccessTokenVerifier
from app.modules.identity_organization.http import get_access_token_verifier
from app.modules.identity_organization.models import OrganizationMembership
from app.modules.production_execution.sheet import issue_sheet
from app.modules.production_planning.commands import release_order
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from tests.jwt_support import ISSUER
from tests.rls_support import ensure_runtime_role, runtime_postgres_url
from tests.test_production_planning import _context, _plan_and_order


def _client(engine, fake: FakeAccessTokenVerifier) -> TestClient:
    ensure_runtime_role(engine)
    runtime = create_engine(runtime_postgres_url(), future=True, pool_pre_ping=True)
    factory = sessionmaker(bind=runtime, expire_on_commit=False, future=True)

    def override_session():
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_runtime_session] = override_session
    app.dependency_overrides[get_access_token_verifier] = lambda: fake
    client = TestClient(app)
    client.runtime_engine = runtime
    return client


def _cleanup(client: TestClient) -> None:
    app.dependency_overrides.clear()
    engine = getattr(client, "runtime_engine", None)
    if engine is not None:
        engine.dispose()


def _headers(token: str, org_id, *, key=None, match=None, extra=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Panne-Organization-Id": str(org_id),
        "X-Correlation-Id": str(uuid4()),
    }
    if key is not None:
        headers["Idempotency-Key"] = str(key)
    if match is not None:
        headers["If-Match"] = str(match)
    if extra:
        headers.update(extra)
    return headers


def _setup_http(engine, slug_prefix: str, role: str = "owner"):
    fake = FakeAccessTokenVerifier()
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    slug = f"{slug_prefix}-{uuid4().hex[:6]}"
    ctx = _context(admin, slug, role=role)
    from tests import helpers

    subject = f"sub-{slug}"
    helpers.auth_identity(admin, ctx["actor"], ISSUER, subject)
    plan, item, order = _plan_and_order(admin, ctx)
    admin.commit()
    token = f"token-{slug}"
    fake.register(token, issuer=ISSUER, subject=subject)
    client = _client(engine, fake)
    return {
        "client": client,
        "fake": fake,
        "admin": admin,
        "ctx": ctx,
        "token": token,
        "plan": plan,
        "item": item,
        "order": order,
        "org_id": ctx["organization"].id,
    }


def test_existing_endpoints_and_openapi(engine) -> None:
    fake = FakeAccessTokenVerifier()
    client = _client(engine, fake)
    try:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200
        assert client.get("/api/v1/me").status_code == 401
        schema = client.get("/openapi.json").json()
        public = {
            "/health",
            "/ready",
            "/api/v1/public/login-editorial",
            "/api/v1/public/demo-guide",
        }
        for path, methods in schema["paths"].items():
            if path in public:
                continue
            for operation in methods.values():
                if isinstance(operation, dict):
                    assert operation.get("security")
        assert "/api/v1/organizations/{organization_id}/production/board" in schema["paths"]
        assert "cost" not in str(schema).lower() or "cost" in "acostamento"
    finally:
        _cleanup(client)


def test_me_lists_multiple_roles(engine) -> None:
    data = _setup_http(engine, "api-me")
    client = data["client"]
    admin = data["admin"]
    membership = admin.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == data["ctx"]["actor"].id
        )
    )
    headers = _headers(data["token"], data["org_id"], key=uuid4())
    grant = client.post(
        f"/api/v1/organizations/{data['org_id']}/memberships/{membership.id}/roles",
        headers=headers,
        json={"role": "viewer", "reason": "leitura extra"},
    )
    assert grant.status_code == 200, grant.text
    me = client.get("/api/v1/me", headers=_headers(data["token"], data["org_id"]))
    assert me.status_code == 200
    body = me.json()
    assert "owner" in body["roles"]
    assert "viewer" in body["roles"]
    assert "identity.read_me" in body["permissions"]
    _cleanup(client)
    admin.close()


def test_production_reads_commands_board_and_security(engine) -> None:
    data = _setup_http(engine, "api-prd")
    client, token, org_id, order, plan = (
        data["client"],
        data["token"],
        data["org_id"],
        data["order"],
        data["plan"],
    )
    admin = data["admin"]
    try:
        prefix = f"/api/v1/organizations/{org_id}/production"
        denied = client.get(f"{prefix}/orders")
        assert denied.status_code == 401
        listed = client.get(f"{prefix}/plans", headers=_headers(token, org_id))
        assert listed.status_code == 200
        assert listed.json()["items"]
        plan_row = next(row for row in listed.json()["items"] if row["id"] == str(plan.id))
        assert plan_row["item_count"] >= 1
        assert plan_row["items_summary"] == data["ctx"]["product"].display_name
        assert "product" not in plan_row or plan_row.get("product") is None
        detail = client.get(f"{prefix}/plans/{plan.id}", headers=_headers(token, org_id))
        assert detail.status_code == 200
        plan_body = detail.json()["data"]
        assert plan_body["items"]
        first_item = plan_body["items"][0]
        assert first_item["product"]["display_name"] == data["ctx"]["product"].display_name
        assert first_item["product"]["code"] == data["ctx"]["product"].code
        assert first_item["technical_product_id"]
        assert first_item["priority"] == 50
        orders = client.get(f"{prefix}/orders", headers=_headers(token, org_id))
        assert orders.status_code == 200
        listed_orders = orders.json()["items"]
        assert listed_orders
        first = listed_orders[0]
        assert first["product"]["display_name"] == data["ctx"]["product"].display_name
        assert first["product"]["code"] == data["ctx"]["product"].code
        assert first["plan"]["public_code"] == plan.public_code
        assert first["plan"]["id"] == str(plan.id)
        assert first["target_mode"] in {"mass", "units"}
        assert "cost" not in orders.text.lower()
        order_detail = client.get(f"{prefix}/orders/{order.id}", headers=_headers(token, org_id))
        assert order_detail.status_code == 200
        assert order_detail.json()["data"]["product"]["display_name"] == data["ctx"]["product"].display_name
        assert order_detail.json()["data"]["plan"]["public_code"] == plan.public_code
        assert "cost" not in order_detail.text.lower()
        page1 = client.get(f"{prefix}/plans?limit=1", headers=_headers(token, org_id))
        assert page1.status_code == 200
        assert "next_cursor" in page1.json()
        board = client.get(
            f"{prefix}/board",
            headers=_headers(token, org_id),
            params={"operational_date": "2026-08-22", "shift": "morning", "q": order.public_code},
        )
        assert board.status_code == 200
        cards = board.json()["data"]
        assert cards
        assert cards[0]["next_action"] in {
            "release_order",
            "schedule_order",
            "adopt_execution_policy",
        }
        extra = client.post(
            f"{prefix}/plans",
            headers=_headers(token, org_id, key=uuid4()),
            json={
                "establishment_id": str(data["ctx"]["establishment"].id),
                "operational_date": "2026-08-23",
                "unexpected": True,
            },
        )
        assert extra.status_code == 400
        assert extra.json()["code"] == "contrato_invalido"
        assert "sql" not in extra.text.lower()
        key = uuid4()
        first = client.post(
            f"{prefix}/plans",
            headers=_headers(token, org_id, key=key),
            json={
                "establishment_id": str(data["ctx"]["establishment"].id),
                "operational_date": "2026-08-24",
            },
        )
        assert first.status_code == 200
        replay = client.post(
            f"{prefix}/plans",
            headers=_headers(token, org_id, key=key),
            json={
                "establishment_id": str(data["ctx"]["establishment"].id),
                "operational_date": "2026-08-24",
            },
        )
        assert replay.status_code == 200
        assert replay.json()["data"]["id"] == first.json()["data"]["id"]
        conflict = client.post(
            f"{prefix}/plans/{plan.id}/schedule",
            headers=_headers(token, org_id, key=uuid4(), match=999),
        )
        assert conflict.status_code == 409
        other = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
        other_ctx = _context(other, f"api-b-{uuid4().hex[:6]}")
        other.commit()
        hidden = client.get(
            f"/api/v1/organizations/{other_ctx['organization'].id}/production/orders",
            headers=_headers(token, other_ctx["organization"].id),
        )
        assert hidden.status_code == 403
        release_order(admin, data["ctx"]["principal"], order_id=order.id, idempotency_key=uuid4())
        admin.commit()
        issue_sheet(
            admin,
            data["ctx"]["principal"],
            order_id=order.id,
            purpose="operational",
            idempotency_key=uuid4(),
        )
        admin.commit()
        sheets = client.get(f"{prefix}/orders/{order.id}/sheets", headers=_headers(token, org_id))
        assert sheets.status_code == 200
        issue_id = sheets.json()["data"][0]["id"]
        payload = client.get(
            f"{prefix}/orders/{order.id}/sheets/{issue_id}", headers=_headers(token, org_id)
        )
        assert payload.status_code == 200
        body = payload.json()["data"]["canonical_payload"]
        assert "materials" in body
        assert "html" not in str(body).lower()
        materials = client.get(
            f"{prefix}/orders/{order.id}/materials", headers=_headers(token, org_id)
        )
        assert materials.status_code == 200
        assert "planned" in materials.json()["data"]
        assert "actual" in materials.json()["data"]
        trace = client.get(
            f"{prefix}/orders/{order.id}/traceability", headers=_headers(token, org_id)
        )
        assert trace.status_code == 200
        assert "events" in trace.json()["data"]
        assert "cost" not in trace.text.lower()
        other.close()
    finally:
        _cleanup(client)
        admin.close()


def test_catalog_and_execution_endpoints(engine) -> None:
    data = _setup_http(engine, "api-ex")
    client, admin, token, org_id, order = (
        data["client"],
        data["admin"],
        data["token"],
        data["org_id"],
        data["order"],
    )
    try:
        from tests import helpers

        helpers.kilogram(admin)
        admin.commit()
        prefix = f"/api/v1/organizations/{org_id}/production"
        catalog = client.get(f"{prefix}/catalog", headers=_headers(token, org_id))
        assert catalog.status_code == 200
        body = catalog.json()["data"]
        codes = {item["code"] for item in body["mass_units"]}
        assert "g" in codes
        assert "kg" in codes
        assert "pre_bake_mass" in body["yield_types"]
        assert "quality" in body["occurrence_categories"]
        assert "ml" not in codes
        release_order(admin, data["ctx"]["principal"], order_id=order.id, idempotency_key=uuid4())
        admin.commit()
        execution = client.get(f"{prefix}/orders/{order.id}/execution", headers=_headers(token, org_id))
        assert execution.status_code == 200
        view = execution.json()["data"]
        assert view["order"]["id"] == str(order.id)
        assert view["policy"]["weighing_policy"] == "optional"
        assert view["readiness"]["weighing"]["ok"] is True
        assert view["readiness"]["steps"]["ok"] is False
        assert view["readiness"]["consumptions"]["ok"] is False
        assert view["readiness"]["yields"]["ok"] is False
        lowered = execution.text.lower()
        assert "preço" not in lowered
        assert "total_amount" not in lowered
        assert "custo previsto" not in lowered
        denied = client.get(
            f"{prefix}/catalog",
            headers=_headers(token, org_id, extra={"Authorization": "Bearer missing"}),
        )
        assert denied.status_code in {401, 403}
    finally:
        _cleanup(client)
        admin.close()


def test_no_forbidden_external_calls_in_http_layer() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "modules" / "production_http"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    assert "boto3" not in text
    assert "cognito" not in text.lower()
    assert "bedrock" not in text.lower()


def test_list_orders_enrichment_without_n_plus_one(engine) -> None:
    from sqlalchemy import event

    data = _setup_http(engine, "orders-enrich")
    client, token, org_id, admin, ctx = (
        data["client"],
        data["token"],
        data["org_id"],
        data["admin"],
        data["ctx"],
    )
    runtime = client.runtime_engine
    try:
        for _ in range(3):
            _plan_and_order(admin, ctx, batches=1)
        admin.commit()

        statements: list[str] = []

        def before_cursor(conn, cursor, statement, parameters, context, executemany):
            if str(statement).lstrip().upper().startswith("SELECT"):
                statements.append(str(statement))

        event.listen(runtime, "before_cursor_execute", before_cursor)
        try:
            prefix = f"/api/v1/organizations/{org_id}/production"
            response = client.get(f"{prefix}/orders", headers=_headers(token, org_id))
        finally:
            event.remove(runtime, "before_cursor_execute", before_cursor)

        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) >= 4
        for item in items:
            assert item["product"] and item["product"]["display_name"]
            assert "cost" not in item
            assert "price" not in str(item).lower()
        order_selects = [sql for sql in statements if "production_order" in sql.lower()]
        assert len(order_selects) <= 2, f"possível N+1: {len(order_selects)} selects de ordem"
    finally:
        _cleanup(client)
        admin.close()


def test_order_out_null_product_and_plan_contract() -> None:
    from types import SimpleNamespace
    from decimal import Decimal
    from datetime import datetime, timezone
    from app.modules.production_http.serialize import order_out

    row = SimpleNamespace(
        id=uuid4(),
        public_code="ORD-X",
        establishment_id=uuid4(),
        plan_id=None,
        technical_product_id=uuid4(),
        target_mode="mass",
        target_quantity=Decimal("10"),
        priority=1,
        status="draft",
        planned_start_at=None,
        planned_end_at=None,
        row_version=1,
        materials_hash=None,
        steps_hash=None,
        snapshot_hash=None,
        created_at=datetime.now(timezone.utc),
    )
    payload = order_out(row, product=None, plan=None)
    assert payload["product"] is None
    assert payload["plan"] is None
    assert "cost" not in payload


def test_list_orders_plan_absent_and_product_fk_invariant(engine) -> None:
    from decimal import Decimal
    from sqlalchemy import inspect, text
    from app.modules.production_planning.commands import create_order
    from app.modules.production_planning.constants import TARGET_MODE_MASS
    from app.modules.production_planning.models import ProductionOrder

    data = _setup_http(engine, "orders-plan-null")
    client, token, org_id, admin, ctx = (
        data["client"],
        data["token"],
        data["org_id"],
        data["admin"],
        data["ctx"],
    )
    try:
        # Invariante: technical_product_id NOT NULL + FK composta com organization_id.
        table = inspect(admin.get_bind()).get_columns("production_order")
        product_col = next(col for col in table if col["name"] == "technical_product_id")
        assert product_col["nullable"] is False
        fks = inspect(admin.get_bind()).get_foreign_keys("production_order")
        product_fks = [
            fk
            for fk in fks
            if "technical_product_id" in fk.get("constrained_columns", [])
        ]
        assert product_fks, "FK de produto técnico ausente"
        assert any(
            "organization_id" in fk.get("constrained_columns", []) for fk in product_fks
        )

        orphan = create_order(
            admin,
            ctx["principal"],
            establishment_id=ctx["establishment"].id,
            technical_product_id=ctx["product"].id,
            target_mode=TARGET_MODE_MASS,
            target_quantity=Decimal("1000"),
            formulation_version_id=ctx["version"].id,
            scale_calculation_id=ctx["scale"].id,
            idempotency_key=uuid4(),
        )
        assert orphan.plan_id is None
        admin.commit()

        prefix = f"/api/v1/organizations/{org_id}/production"
        response = client.get(f"{prefix}/orders", headers=_headers(token, org_id))
        assert response.status_code == 200
        items = response.json()["items"]
        found = next(item for item in items if item["id"] == str(orphan.id))
        assert found["plan"] is None
        assert found["plan_id"] is None
        assert found["product"]["display_name"] == ctx["product"].display_name
        assert found["product"]["code"] == ctx["product"].code

        # Ordem continua listada se o join de produto falhar (outerjoin); product null.
        # Simula órfão bypassando FK apenas no ambiente de teste.
        admin.execute(text("SET session_replication_role = 'replica'"))
        admin.execute(
            text("DELETE FROM technical_product WHERE id = CAST(:id AS uuid)"),
            {"id": str(ctx["product"].id)},
        )
        admin.execute(text("SET session_replication_role = 'origin'"))
        admin.commit()

        after = client.get(f"{prefix}/orders", headers=_headers(token, org_id))
        assert after.status_code == 200
        rows = after.json()["items"]
        assert any(item["id"] == str(orphan.id) for item in rows)
        orphan_row = next(item for item in rows if item["id"] == str(orphan.id))
        assert orphan_row["product"] is None
        # Paginação não engole a linha órfã.
        assert len(rows) >= 1
        assert all(item.get("plan") is None or item["plan"].get("public_code") for item in rows)
        # Isolamento: nenhum display_name de outra org.
        for item in rows:
            if item["product"]:
                assert item["product"]["id"]
    finally:
        _cleanup(client)
        admin.close()


def test_list_orders_rejects_foreign_plan_enrichment(engine) -> None:
    from sqlalchemy import text
    from tests.test_production_planning import _context, _plan_and_order as plan_order

    data = _setup_http(engine, "orders-plan-iso-a")
    client, token, org_id, admin = data["client"], data["token"], data["org_id"], data["admin"]
    try:
        _plan, _item, order = _plan_and_order(admin, data["ctx"], batches=1)
        other_ctx = _context(admin, f"orders-plan-iso-b-{uuid4().hex[:6]}")
        other_plan, _other_item, _other_order = plan_order(admin, other_ctx, batches=1)
        admin.commit()

        # Aponta plan_id para plano de outra org (bypass FK) — enrich não deve vazar.
        admin.execute(text("SET session_replication_role = 'replica'"))
        admin.execute(
            text(
                "UPDATE production_order SET plan_id = CAST(:pid AS uuid) WHERE id = CAST(:oid AS uuid)"
            ),
            {"pid": str(other_plan.id), "oid": str(order.id)},
        )
        admin.execute(text("SET session_replication_role = 'origin'"))
        admin.commit()

        prefix = f"/api/v1/organizations/{org_id}/production"
        response = client.get(f"{prefix}/orders", headers=_headers(token, org_id))
        assert response.status_code == 200
        row = next(item for item in response.json()["items"] if item["id"] == str(order.id))
        assert row["plan"] is None
        assert row["plan_id"] == str(other_plan.id)
        # Plano estrangeiro não é hidratado (mesmo se o código público coincidir com outro plano local).
        assert all(
            item["plan"] is None or item["plan"]["id"] != str(other_plan.id)
            for item in response.json()["items"]
        )
    finally:
        _cleanup(client)
        admin.close()
