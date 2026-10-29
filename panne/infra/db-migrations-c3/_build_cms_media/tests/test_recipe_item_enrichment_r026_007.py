from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import sessionmaker

from app.modules.formula_lab.models import FormulationItem
from app.modules.ingredient_catalog.models import Ingredient
from app.modules.recipe_http.serialize import load_item_enrichments
from tests import helpers


def test_load_item_enrichments_org_scoped(engine) -> None:
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    try:
        org_a = helpers.org(admin, f"r0267a-{uuid4().hex[:6]}")
        org_b = helpers.org(admin, f"r0267b-{uuid4().hex[:6]}")
        unit = helpers.gram(admin)
        ver_a = helpers.published_dossier(
            admin, org_a, unit, f"IA-{uuid4().hex[:4]}", nutrients={}
        )
        identity = admin.get(Ingredient, ver_a.ingredient_id)
        item = FormulationItem(
            id=uuid4(),
            organization_id=org_a.id,
            formulation_version_id=uuid4(),
            ingredient_version_id=ver_a.id,
            sequence=1,
            net_quantity=Decimal("1000"),
            measurement_unit_id=unit.id,
            correction_factor=Decimal("1"),
            is_flour_basis=True,
            role="ingredient",
        )

        ok = load_item_enrichments(admin, org_a.id, [item])
        assert ok[item.id][0]["display_name"] == identity.display_name
        assert ok[item.id][0]["code"] == identity.code
        assert ok[item.id][1]["code"] == "g"

        foreign = load_item_enrichments(admin, org_b.id, [item])
        assert foreign[item.id][0] is None
        assert foreign[item.id][1]["code"] == "g"
    finally:
        admin.close()
