from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.modules.production_http.serialize import plan_items_summary
from app.modules.production_planning.commands import create_plan, upsert_plan_item
from app.modules.production_planning.constants import TARGET_MODE_MASS
from tests import helpers
from tests.test_production_api import _cleanup, _headers, _setup_http


def test_plan_items_summary_contract() -> None:
    assert plan_items_summary([]) == (0, "Nenhum item planejado")
    assert plan_items_summary(["Pão francês (Demo)"]) == (1, "Pão francês (Demo)")
    assert plan_items_summary([None]) == (1, "1 item planejado")
    assert plan_items_summary(["  "]) == (1, "1 item planejado")
    assert plan_items_summary(["A", "B", "C"]) == (3, "A e mais 2")
    assert plan_items_summary([None, None]) == (2, "2 itens planejados")
    assert plan_items_summary(["Primeiro", None]) == (2, "Primeiro e mais 1")


def test_plan_list_enrichment_order_and_no_n_plus_one(engine) -> None:
    data = _setup_http(engine, "api-pl6")
    client, token, org_id, admin, ctx = (
        data["client"],
        data["token"],
        data["org_id"],
        data["admin"],
        data["ctx"],
    )
    try:
        other = helpers.technical_product(admin, ctx["organization"], f"P2-{uuid4().hex[:6]}")
        other.display_name = "Ciabatta (Demo)"
        early = create_plan(
            admin,
            ctx["principal"],
            establishment_id=ctx["establishment"].id,
            operational_date=date(2026, 8, 20),
            idempotency_key=uuid4(),
            shift="afternoon",
        )
        empty = create_plan(
            admin,
            ctx["principal"],
            establishment_id=ctx["establishment"].id,
            operational_date=date(2026, 8, 21),
            idempotency_key=uuid4(),
            shift="morning",
        )
        multi = create_plan(
            admin,
            ctx["principal"],
            establishment_id=ctx["establishment"].id,
            operational_date=date(2026, 8, 21),
            idempotency_key=uuid4(),
            shift="afternoon",
        )
        upsert_plan_item(
            admin,
            ctx["principal"],
            plan_id=multi.id,
            technical_product_id=ctx["product"].id,
            target_mode=TARGET_MODE_MASS,
            target_quantity=Decimal("1000"),
            sort_order=1,
            idempotency_key=uuid4(),
        )
        upsert_plan_item(
            admin,
            ctx["principal"],
            plan_id=multi.id,
            technical_product_id=other.id,
            target_mode=TARGET_MODE_MASS,
            target_quantity=Decimal("2000"),
            sort_order=2,
            idempotency_key=uuid4(),
        )
        late = create_plan(
            admin,
            ctx["principal"],
            establishment_id=ctx["establishment"].id,
            operational_date=date(2026, 8, 25),
            idempotency_key=uuid4(),
            shift="morning",
        )
        admin.commit()

        prefix = f"/api/v1/organizations/{org_id}/production"
        listed = client.get(f"{prefix}/plans", headers=_headers(token, org_id))
        assert listed.status_code == 200, listed.text
        rows = listed.json()["items"]
        by_id = {row["id"]: row for row in rows}

        assert by_id[str(empty.id)]["item_count"] == 0
        assert by_id[str(empty.id)]["items_summary"] == "Nenhum item planejado"
        assert by_id[str(multi.id)]["item_count"] == 2
        assert by_id[str(multi.id)]["items_summary"] == f"{ctx['product'].display_name} e mais 1"
        assert by_id[str(early.id)]["item_count"] == 0
        assert by_id[str(late.id)]["item_count"] == 0

        dates = [row["operational_date"] for row in rows]
        assert dates == sorted(dates)

        ids = [row["id"] for row in rows]
        assert ids.index(str(early.id)) < ids.index(str(empty.id))
        assert ids.index(str(empty.id)) < ids.index(str(multi.id))
        assert ids.index(str(multi.id)) < ids.index(str(late.id))

        page1 = client.get(f"{prefix}/plans?limit=1", headers=_headers(token, org_id))
        assert page1.status_code == 200
        assert page1.json()["next_cursor"]
        page2 = client.get(
            f"{prefix}/plans",
            headers=_headers(token, org_id),
            params={"limit": 1, "cursor": page1.json()["next_cursor"]},
        )
        assert page2.status_code == 200
        assert page2.json()["items"][0]["id"] != page1.json()["items"][0]["id"]
    finally:
        _cleanup(client)
        admin.close()
