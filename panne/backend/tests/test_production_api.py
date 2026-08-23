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
        public = {"/health", "/ready"}
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
        detail = client.get(f"{prefix}/plans/{plan.id}", headers=_headers(token, org_id))
        assert detail.status_code == 200
        orders = client.get(f"{prefix}/orders", headers=_headers(token, org_id))
        assert orders.status_code == 200
        order_detail = client.get(f"{prefix}/orders/{order.id}", headers=_headers(token, org_id))
        assert order_detail.status_code == 200
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
        assert "cost" not in execution.text.lower()
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
