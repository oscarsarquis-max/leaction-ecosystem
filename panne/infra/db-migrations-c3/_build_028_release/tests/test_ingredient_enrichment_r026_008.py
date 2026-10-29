"""Enriquecimento R026-008.

Catálogos globais (`nutrient_definition`, `allergen`, `measurement_unit`):
RLS exige usuário autenticado (`panne_current_user_id()`), não `organization_id`.
`Supplier` permanece escopo organizacional.
"""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.modules.ingredient_catalog.models import (
    IngredientAllergen,
    IngredientNutrient,
    Supplier,
    SupplierItem,
)
from app.modules.ingredient_http.serialize import (
    load_allergen_enrichments,
    load_item_enrichments,
    load_nutrient_enrichments,
)
from tests import helpers


def test_nutrient_allergen_item_enrichments_batch(engine) -> None:
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    try:
        org = helpers.org(admin, f"r0268-{uuid4().hex[:6]}")
        other = helpers.org(admin, f"r0268o-{uuid4().hex[:6]}")
        unit = helpers.gram(admin)
        protein = helpers.nutrient(admin, unit, f"prot-{uuid4().hex[:4]}")
        gluten = helpers.allergen(admin, f"glu-{uuid4().hex[:4]}")
        version = helpers.draft_ingredient(admin, org, unit, f"FAR-{uuid4().hex[:4]}")
        helpers.ingredient_nutrient(admin, version, protein, Decimal("10"))
        nutrient_row = admin.scalar(
            select(IngredientNutrient).where(IngredientNutrient.ingredient_version_id == version.id)
        )
        assert nutrient_row is not None
        allergen_row = IngredientAllergen(
            id=uuid4(),
            organization_id=org.id,
            ingredient_version_id=version.id,
            allergen_id=gluten.id,
            presence="contains",
            evidence_note="demo",
        )
        admin.add(allergen_row)
        supplier = Supplier(
            organization_id=org.id,
            code=f"FOR-{uuid4().hex[:4]}",
            display_name="Moinho",
            status="active",
        )
        admin.add(supplier)
        admin.flush()
        item = SupplierItem(
            organization_id=org.id,
            supplier_id=supplier.id,
            ingredient_id=version.ingredient_id,
            supplier_sku="SKU-FAR-25",
            description="Embalagem",
            package_quantity=Decimal("25"),
            measurement_unit_id=unit.id,
            status="active",
        )
        admin.add(item)
        admin.flush()

        nutrients = load_nutrient_enrichments(admin, [nutrient_row])
        assert nutrients[nutrient_row.id][0]["code"] == protein.code
        assert nutrients[nutrient_row.id][0]["name"] == protein.name
        assert nutrients[nutrient_row.id][1]["code"] == "g"

        allergens = load_allergen_enrichments(admin, [allergen_row])
        assert allergens[allergen_row.id]["name"] == gluten.name

        items = load_item_enrichments(admin, org.id, [item])
        assert items[item.id][0]["code"] == "g"
        assert items[item.id][1]["display_name"] == "Moinho"

        foreign = load_item_enrichments(admin, other.id, [item])
        assert foreign[item.id][1] is None
    finally:
        admin.close()


def test_orphan_nutrient_and_allergen_fall_back(engine) -> None:
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    try:
        org = helpers.org(admin, f"r0268orf-{uuid4().hex[:6]}")
        # objetos só em memória: IDs sem catálogo correspondente
        nutrient_row = IngredientNutrient(
            id=uuid4(),
            organization_id=org.id,
            ingredient_version_id=uuid4(),
            nutrient_id=uuid4(),
            value=Decimal("1"),
            value_status="measured",
        )
        allergen_row = IngredientAllergen(
            id=uuid4(),
            organization_id=org.id,
            ingredient_version_id=uuid4(),
            allergen_id=uuid4(),
            presence="contains",
        )
        nutrients = load_nutrient_enrichments(admin, [nutrient_row])
        assert nutrients[nutrient_row.id][0] is None
        allergens = load_allergen_enrichments(admin, [allergen_row])
        assert allergens[allergen_row.id] is None
    finally:
        admin.close()
