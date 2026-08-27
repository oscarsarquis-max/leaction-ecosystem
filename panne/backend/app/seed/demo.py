"""Cenário sintético da Panne Demonstração. Idempotente. Sem dados reais."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ai_orchestration.fake_gateway import FakeModelGateway
from app.modules.ai_orchestration.service import (
    decide_proposal,
    materialize_recipe_proposal,
    propose_recipe,
    review_changes,
)
from app.modules.calculation_engine.scale import calculate_total_dough_mass, persist_scale_calculation
from app.modules.costing_pricing.services import (
    create_policy as create_costing_policy,
    create_practiced_price,
    decide_price,
    publish_policy as publish_costing_policy,
    run_calculation,
    simulate_price,
)
from app.modules.formula_lab.commands import publish_version
from app.modules.formula_lab.models import FormulationItem, Trial
from app.modules.identity_organization.authorization import Principal
from app.modules.identity_organization.models import (
    AppUser,
    AuthIdentity,
    Establishment,
    Organization,
    OrganizationMembership,
    OrganizationMembershipRole,
)
from app.modules.ingredient_catalog.models import (
    Allergen,
    Ingredient,
    IngredientAllergen,
    IngredientComposition,
    IngredientNutrient,
    IngredientVersion,
    MeasurementUnit,
    NutrientDefinition,
    Supplier,
    SupplierItem,
    SupplierItemPrice,
)
from app.modules.inventory_procurement.services import (
    confirm_pick,
    create_count,
    create_item,
    create_location,
    create_order as create_purchase_order,
    create_policy,
    compare_quotations,
    create_quotation,
    create_requisition,
    freeze_count_scope,
    post_consumption,
    open_balance,
    publish_policy,
    receive_order,
    record_count,
    record_observed_price,
    reserve_order,
    current_order_items,
    receipt_items,
    return_to_supplier,
    review_count,
    set_lot_status,
    suggest_fefo,
    suggest_replenishment,
    transition_order,
    transition_requisition,
)
from app.modules.knowledge_grounding.ingest import IngestRequest, ingest, review_source_version
from app.modules.labeling_compliance.services import (
    create_dossier,
    run_evaluation,
    review_version,
    save_profile,
)
from app.modules.production_execution.constants import (
    CONSUMPTION_CONSUME,
    CONSUMPTION_RETURN,
    CONSUMPTION_WASTE,
    OCCURRENCE_QUALITY,
    POLICY_WEIGHING_REQUIRED,
    SEVERITY_HIGH,
    SHEET_OPERATIONAL,
    VERIFICATION_SECOND_PERSON,
    VERIFY_ACCEPTED,
    YIELD_POST_BAKE_MASS,
)
from app.modules.production_execution.consumption import record_consumption
from app.modules.production_execution.lifecycle import complete_order, mark_order_ready, short_close_order
from app.modules.production_execution.occurrences import record_occurrence
from app.modules.production_execution.policy import set_execution_policy
from app.modules.production_execution.sheet import issue_sheet
from app.modules.production_execution.steps import complete_step, hold_step, mark_step_ready, start_step
from app.modules.production_execution.weighing import (
    complete_weighing_session,
    open_weighing_session,
    record_weighing,
    verify_weighing,
)
from app.modules.production_execution.yields import record_yield
from app.modules.production_planning.commands import (
    cancel_order,
    create_order,
    create_plan,
    hold_order,
    release_order,
    schedule_order,
    schedule_plan,
    split_batches,
    upsert_plan_item,
)
from app.modules.production_planning.constants import TARGET_MODE_MASS
from app.modules.production_planning.models import (
    ProductionBatch,
    ProductionBatchMaterial,
    ProductionOrderStep,
    ProductionPlanItem,
)
from app.modules.reporting_analytics.services import create_saved_view, create_snapshot
from app.seed.ids import at, seed_uuid
from app.seed.reference import seed_reference
from tests import helpers

ORG_A = "panne-demonstracao"
ORG_B = "padaria-horizonte-demo"
ISSUER = "https://panne.local/fake"

PROFILES = (
    ("demo-owner", "Proprietário Demo", "owner.demo@panne.invalid", "owner"),
    ("demo-manager", "Gestor de Produção Demo", "gestor.producao.demo@panne.invalid", "production_manager"),
    ("demo-formulator", "Formulador Demo", "formulador.demo@panne.invalid", "technical_responsible"),
    ("demo-baker", "Padeiro Demo", "padeiro.demo@panne.invalid", "baker_operator"),
    ("demo-reviewer", "Revisor Regulatório Demo", "revisor.demo@panne.invalid", "regulatory_reviewer"),
    ("demo-buyer", "Compras Demo", "compras.demo@panne.invalid", "commercial"),
    ("demo-reader", "Leitor Demo", "leitor.demo@panne.invalid", "viewer"),
)

INGREDIENTS = (
    ("FAR-TRIGO", "Farinha de trigo tipo 1", "simple", "published", "full", True, "g"),
    ("FAR-INT", "Farinha integral", "simple", "published", "full", True, "g"),
    ("AGUA", "Água", "simple", "published", "partial", False, "g"),
    ("SAL", "Sal refinado", "simple", "published", "full", False, "g"),
    ("FER-BIO", "Fermento biológico fresco", "simple", "published", "full", False, "g"),
    ("ACUCAR", "Açúcar cristal", "simple", "published", "full", False, "g"),
    ("MANTEIGA", "Manteiga", "simple", "published", "full", True, "g"),
    ("OLEO", "Óleo de soja", "simple", "published", "partial", False, "g"),
    ("LEITE", "Leite integral", "simple", "published", "full", True, "g"),
    ("OVO", "Ovo", "simple", "published", "full", True, "g"),
    ("GERGELIM", "Gergelim", "simple", "published", "partial", True, "g"),
    ("RECHEIO", "Recheio de goiabada", "simple", "draft", "none", False, "g"),
    ("MELHOR", "Melhorador de farinha", "composite", "published", "partial", True, "g"),
    ("CALDA", "Calda de açúcar", "preparation", "published", "none", False, "g"),
    ("FAR-RET", "Farinha especial retirada", "simple", "retired", "none", False, "g"),
    ("LEV-POOL", "Poolish", "preparation", "published", "partial", True, "g"),
    ("MARGARINA", "Margarina", "simple", "published", "full", False, "g"),
    ("LEITE-PO", "Leite em pó", "simple", "draft", "partial", True, "g"),
)


@dataclass
class DemoWorld:
    organization: Organization
    other: Organization
    central: Establishment
    bairro: Establishment
    horizonte: Establishment
    users: dict[str, AppUser]
    principals: dict[str, Principal]
    units: dict[str, MeasurementUnit]
    ingredients: dict[str, IngredientVersion] = field(default_factory=dict)
    products: dict = field(default_factory=dict)
    orders: dict = field(default_factory=dict)
    gaps: list[str] = field(default_factory=list)


def _principal(user: AppUser, organization: Organization, role: str) -> Principal:
    return helpers.principal_for(user, organization, role)


def _org(session: Session, slug: str, legal: str, display: str) -> Organization:
    row = session.scalar(select(Organization).where(Organization.slug == slug))
    if row:
        return row
    row = Organization(id=seed_uuid("org", slug), slug=slug, legal_name=legal, display_name=display, status="active")
    session.add(row)
    session.flush()
    return row


def _place(session: Session, organization: Organization, code: str, name: str) -> Establishment:
    row = session.scalar(
        select(Establishment).where(
            Establishment.organization_id == organization.id, Establishment.code == code
        )
    )
    if row:
        return row
    row = Establishment(
        id=seed_uuid("est", str(organization.id), code),
        organization_id=organization.id,
        code=code,
        display_name=name,
        status="active",
    )
    session.add(row)
    session.flush()
    return row


def _user(session: Session, subject: str, name: str, email: str) -> AppUser:
    row = session.scalar(select(AppUser).where(AppUser.email == email))
    if row:
        return row
    row = AppUser(id=seed_uuid("user", subject), email=email, display_name=name, status="active")
    session.add(row)
    session.flush()
    identity = session.scalar(
        select(AuthIdentity).where(AuthIdentity.issuer == ISSUER, AuthIdentity.subject == subject)
    )
    if identity is None:
        session.add(AuthIdentity(user_id=row.id, issuer=ISSUER, subject=subject, status="active"))
        session.flush()
    return row


def _member(session: Session, organization: Organization, user: AppUser, role: str) -> None:
    row = session.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization.id,
            OrganizationMembership.user_id == user.id,
        )
    )
    if row is None:
        row = OrganizationMembership(
            organization_id=organization.id, user_id=user.id, legacy_role_label=role, status="active"
        )
        session.add(row)
        session.flush()
    exists = session.scalar(
        select(OrganizationMembershipRole).where(
            OrganizationMembershipRole.membership_id == row.id,
            OrganizationMembershipRole.role == role,
        )
    )
    if exists is None:
        session.add(
            OrganizationMembershipRole(
                organization_id=organization.id,
                membership_id=row.id,
                role=role,
                granted_by_user_id=user.id,
                reason="seed-demo",
            )
        )
        session.flush()


def seed_identity(session: Session) -> DemoWorld:
    org_a = _org(session, ORG_A, "Panne Demonstração LTDA", "Panne Demonstração")
    org_b = _org(session, ORG_B, "Padaria Horizonte Demo LTDA", "Padaria Horizonte Demo")
    central = _place(session, org_a, "CENTRAL", "Padaria Central")
    bairro = _place(session, org_a, "BAIRRO", "Unidade Bairro")
    horizonte = _place(session, org_b, "HORIZONTE", "Unidade Horizonte")
    users: dict[str, AppUser] = {}
    principals: dict[str, Principal] = {}
    for subject, name, email, role in PROFILES:
        user = _user(session, subject, name, email)
        users[subject] = user
        _member(session, org_a, user, role)
        principals[subject] = _principal(user, org_a, role)
    _member(session, org_b, users["demo-owner"], "viewer")
    horizonte_owner = _user(
        session, "demo-horizonte", "Proprietário Horizonte Demo", "horizonte.owner@panne.invalid"
    )
    _member(session, org_b, horizonte_owner, "owner")
    users["demo-horizonte"] = horizonte_owner
    principals["demo-horizonte"] = _principal(horizonte_owner, org_b, "owner")
    units = {
        row.code: row
        for row in session.scalars(select(MeasurementUnit).where(MeasurementUnit.status == "active"))
    }
    return DemoWorld(
        organization=org_a,
        other=org_b,
        central=central,
        bairro=bairro,
        horizonte=horizonte,
        users=users,
        principals=principals,
        units=units,
    )


def _nutrient(session: Session, code: str) -> NutrientDefinition:
    row = session.scalar(select(NutrientDefinition).where(NutrientDefinition.code == code))
    if row is None:
        raise RuntimeError(f"nutriente {code} ausente do reference seed")
    return row


def seed_ingredients(session: Session, world: DemoWorld) -> None:
    gram = world.units["g"]
    org = world.organization
    allergens = {row.code: row for row in session.scalars(select(Allergen))}
    for code, name, kind, status, nutrition, allergenic, _unit in INGREDIENTS:
        item = session.scalar(
            select(Ingredient).where(Ingredient.organization_id == org.id, Ingredient.code == code)
        )
        if item is None:
            item = Ingredient(
                organization_id=org.id,
                code=code,
                display_name=f"{name} (Demo)",
                ingredient_type=kind,
                status="active",
            )
            session.add(item)
            session.flush()
        version = session.scalar(
            select(IngredientVersion).where(
                IngredientVersion.ingredient_id == item.id, IngredientVersion.version_number == 1
            )
        )
        if version is None:
            version = helpers.version(session, item, gram, status="draft")
        if nutrition != "none":
            values = {
                "protein": "10" if nutrition == "full" else "8",
                "carbohydrate": "70" if nutrition == "full" else None,
                "total_fat": "2",
                "sodium": "0.4" if nutrition == "full" else None,
            }
            for nutrient_code, raw in values.items():
                if raw is None:
                    continue
                definition = _nutrient(session, nutrient_code)
                existing = session.scalar(
                    select(IngredientNutrient).where(
                        IngredientNutrient.ingredient_version_id == version.id,
                        IngredientNutrient.nutrient_id == definition.id,
                    )
                )
                if existing is None:
                    helpers.ingredient_nutrient(session, version, definition, Decimal(raw))
        if allergenic and "gluten" in allergens and code.startswith("FAR"):
            exists = session.scalar(
                select(IngredientAllergen).where(
                    IngredientAllergen.ingredient_version_id == version.id,
                    IngredientAllergen.allergen_id == allergens["gluten"].id,
                )
            )
            if exists is None:
                session.add(
                    IngredientAllergen(
                        organization_id=org.id,
                        ingredient_version_id=version.id,
                        allergen_id=allergens["gluten"].id,
                        presence="contains",
                        evidence_note="Fonte sintética de demonstração.",
                    )
                )
        if status == "retired":
            version.status = "retired"
        elif status == "published" and code != "MELHOR":
            version.status = "published"
        world.ingredients[code] = version
    flour = world.ingredients["FAR-TRIGO"]
    melhor = world.ingredients["MELHOR"]
    composed = session.scalar(
        select(IngredientComposition).where(
            IngredientComposition.parent_ingredient_version_id == melhor.id
        )
    )
    if composed is None:
        session.add(
            IngredientComposition(
                organization_id=org.id,
                parent_ingredient_version_id=melhor.id,
                component_ingredient_version_id=flour.id,
                component_type="constituent",
                quantity=Decimal("100"),
                measurement_unit_id=gram.id,
                sequence=1,
            )
        )
        session.flush()
    if melhor.status != "published":
        melhor.status = "published"
    other_item = session.scalar(
        select(Ingredient).where(Ingredient.organization_id == world.other.id, Ingredient.code == "FAR-HZ")
    )
    if other_item is None:
        world.ingredients["FAR-HZ"] = helpers.published_ingredient(
            session, world.other, gram, "FAR-HZ", ingredient_type="simple"
        )
    else:
        world.ingredients["FAR-HZ"] = session.scalar(
            select(IngredientVersion).where(IngredientVersion.ingredient_id == other_item.id)
        )
    _seed_suppliers(session, world)
    session.flush()


def _seed_suppliers(session: Session, world: DemoWorld) -> None:
    org = world.organization
    gram = world.units["g"]
    kg = world.units["kg"]
    # SKU-FAR-25 = saco de 25 kg (não 25000 kg). Demais: quantidade na unidade do item.
    specs = (
        ("FOR-MOINHO", "Moinho Demo", "FAR-TRIGO", "SKU-FAR-25", Decimal("25"), kg, True),
        ("FOR-LATIC", "Laticínio Demo", "LEITE", "SKU-LEI-1", Decimal("1000"), gram, True),
        ("FOR-GRANJA", "Granja Demo", "OVO", "SKU-OVO-30", Decimal("1800"), gram, True),
        ("FOR-SEMENTE", "Sementes Demo", "GERGELIM", "SKU-GER-1", Decimal("1000"), gram, False),
    )
    for code, name, ingredient_code, sku, qty, unit, priced in specs:
        supplier = session.scalar(
            select(Supplier).where(Supplier.organization_id == org.id, Supplier.code == code)
        )
        if supplier is None:
            supplier = Supplier(
                organization_id=org.id, code=code, display_name=f"{name}", status="active"
            )
            session.add(supplier)
            session.flush()
        item = session.scalar(
            select(SupplierItem).where(
                SupplierItem.organization_id == org.id, SupplierItem.supplier_sku == sku
            )
        )
        if item is None:
            item = SupplierItem(
                organization_id=org.id,
                supplier_id=supplier.id,
                ingredient_id=world.ingredients[ingredient_code].ingredient_id,
                supplier_sku=sku,
                description="Embalagem de demonstração",
                package_quantity=qty,
                measurement_unit_id=unit.id,
                status="active",
            )
            session.add(item)
            session.flush()
        else:
            # Corrige seed incoerente anterior (ex.: 25000 kg) sem recriar o item.
            if item.package_quantity != qty or item.measurement_unit_id != unit.id:
                item.package_quantity = qty
                item.measurement_unit_id = unit.id
                session.flush()
        if priced and session.scalar(select(SupplierItemPrice).where(SupplierItemPrice.supplier_item_id == item.id)) is None:
            session.add(
                SupplierItemPrice(
                    supplier_item_id=item.id,
                    unit_price=Decimal("12.50"),
                    currency="BRL",
                    observed_at=at(date(2026, 8, 24), days=-10),
                    source="seed-demo",
                )
            )
            session.add(
                SupplierItemPrice(
                    supplier_item_id=item.id,
                    unit_price=Decimal("13.10"),
                    currency="BRL",
                    observed_at=at(date(2026, 8, 24), days=-1),
                    source="seed-demo",
                )
            )


def _recipe(
    session: Session,
    world: DemoWorld,
    code: str,
    name: str,
    lines: list[tuple[str, str, bool]],
    *,
    publish: bool,
) -> dict:
    org = world.organization
    actor = world.users["demo-formulator"]
    principal = world.principals["demo-formulator"]
    from app.modules.formula_lab.models import Formulation, FormulationVersion, ScaleCalculation, TechnicalProduct

    product = session.scalar(
        select(TechnicalProduct).where(TechnicalProduct.organization_id == org.id, TechnicalProduct.code == code)
    )
    if product is None:
        product = helpers.technical_product(session, org, code, status="approved")
        product.display_name = f"{name} (Demo)"
    recipe = session.scalar(
        select(Formulation).where(Formulation.organization_id == org.id, Formulation.code == f"F-{code}")
    )
    if recipe is None:
        recipe = helpers.formulation(session, product, f"F-{code}", status="active")
        recipe.display_name = f"{name} (Demo)"
    version = session.scalar(
        select(FormulationVersion).where(
            FormulationVersion.formulation_id == recipe.id, FormulationVersion.version_number == 1
        )
    )
    if version is None:
        version = helpers.formulation_version(session, recipe, created_by_user_id=actor.id)
        for index, (ingredient_code, qty, flour) in enumerate(lines, start=1):
            helpers.formulation_item(
                session,
                version,
                world.ingredients[ingredient_code],
                world.units["g"],
                index,
                Decimal(qty),
                is_flour_basis=flour,
            )
        helpers.process_step(session, version, 1, "Misturar", "Misturar até homogêneo. Demo.")
        helpers.process_step(session, version, 2, "Fermentar", "Fermentar na câmara. Demo.")
        helpers.process_step(session, version, 3, "Assar", "Assar nos fornos. Demo.")
        helpers.approve_version(session, version, actor, "approved")
        if publish:
            publish_version(session, principal, version.id, expected_version=None, idempotency_key=seed_uuid("pub", code))
    items = list(
        session.scalars(select(FormulationItem).where(FormulationItem.formulation_version_id == version.id))
    )
    scale = session.scalar(
        select(ScaleCalculation).where(ScaleCalculation.formulation_version_id == version.id)
    )
    if scale is None:
        scale = persist_scale_calculation(
            session, version, calculate_total_dough_mass(items, Decimal("3300")), actor.id
        )
    world.products[code] = {"product": product, "version": version, "scale": scale}
    return world.products[code]


def seed_recipes(session: Session, world: DemoWorld) -> None:
    _recipe(
        session,
        world,
        "PAO-FR",
        "Pão francês",
        [("FAR-TRIGO", "1000", True), ("AGUA", "650", False), ("SAL", "20", False), ("FER-BIO", "15", False)],
        publish=True,
    )
    _recipe(
        session,
        world,
        "PAO-INT",
        "Pão integral",
        [("FAR-INT", "800", True), ("FAR-TRIGO", "200", True), ("AGUA", "700", False), ("SAL", "18", False)],
        publish=True,
    )
    _recipe(
        session,
        world,
        "FOCACCIA",
        "Focaccia",
        [("FAR-TRIGO", "1000", True), ("AGUA", "750", False), ("OLEO", "80", False), ("SAL", "22", False)],
        publish=True,
    )
    _recipe(
        session,
        world,
        "BRIOCHE",
        "Brioche",
        [("FAR-TRIGO", "1000", True), ("OVO", "300", False), ("MANTEIGA", "400", False), ("ACUCAR", "120", False)],
        publish=True,
    )
    _recipe(
        session,
        world,
        "BOLO",
        "Bolo simples",
        [("FAR-TRIGO", "400", False), ("ACUCAR", "300", False), ("OVO", "200", False), ("LEITE", "200", False)],
        publish=False,
    )
    if session.scalar(select(Trial).where(Trial.code == "TR-PAO-OK")) is None:
        session.add(
            Trial(
                organization_id=world.organization.id,
                formulation_version_id=world.products["PAO-FR"]["version"].id,
                code="TR-PAO-OK",
                status="completed",
                notes="Trial sintético aprovado. Demo.",
                created_by_user_id=world.users["demo-formulator"].id,
            )
        )
        session.add(
            Trial(
                organization_id=world.organization.id,
                formulation_version_id=world.products["BOLO"]["version"].id,
                code="TR-BOLO-WAIT",
                status="planned",
                notes="Trial sintético pendente. Demo.",
                created_by_user_id=world.users["demo-formulator"].id,
            )
        )
        session.add(
            Trial(
                organization_id=world.organization.id,
                formulation_version_id=world.products["FOCACCIA"]["version"].id,
                code="TR-FOC-NO",
                status="cancelled",
                notes="Trial sintético rejeitado. Demo.",
                created_by_user_id=world.users["demo-formulator"].id,
            )
        )


def _plan_order(session: Session, world: DemoWorld, key: str, product_code: str, *, when: date, shift: str, qty: str, priority: int):
    principal = world.principals["demo-manager"]
    ctx = world.products[product_code]
    mass = ctx["scale"].input_target_total_dough_mass or Decimal(qty)
    plan = create_plan(
        session,
        principal,
        establishment_id=world.central.id,
        operational_date=when,
        idempotency_key=seed_uuid("plan", key),
        shift=shift,
        notes=f"Plano demo {key}",
    )
    existing_item = session.scalar(
        select(ProductionPlanItem).where(
            ProductionPlanItem.production_plan_id == plan.id,
            ProductionPlanItem.sort_order == 1,
        )
    )
    item = upsert_plan_item(
        session,
        principal,
        plan_id=plan.id,
        technical_product_id=ctx["product"].id,
        target_mode=TARGET_MODE_MASS,
        target_quantity=mass,
        sort_order=1,
        item_id=existing_item.id if existing_item is not None else None,
        idempotency_key=seed_uuid("item", key),
    )
    if plan.status == "draft":
        schedule_plan(session, principal, plan_id=plan.id, idempotency_key=seed_uuid("psched", key))
    order = create_order(
        session,
        principal,
        establishment_id=world.central.id,
        technical_product_id=ctx["product"].id,
        target_mode=TARGET_MODE_MASS,
        target_quantity=mass,
        plan_id=plan.id,
        plan_item_id=item.id,
        formulation_version_id=ctx["version"].id,
        scale_calculation_id=ctx["scale"].id,
        priority=priority,
        idempotency_key=seed_uuid("order", key),
    )
    return plan, order


def _batches(session: Session, order_id: UUID):
    return list(
        session.scalars(
            select(ProductionBatch).where(ProductionBatch.production_order_id == order_id).order_by(ProductionBatch.sequence)
        )
    )


def _materials(session: Session, batch_id: UUID):
    return list(session.scalars(select(ProductionBatchMaterial).where(ProductionBatchMaterial.production_batch_id == batch_id)))


def _steps(session: Session, order_id: UUID):
    return list(
        session.scalars(
            select(ProductionOrderStep).where(ProductionOrderStep.production_order_id == order_id).order_by(ProductionOrderStep.sequence)
        )
    )


def _release(session: Session, world: DemoWorld, order, key: str):
    principal = world.principals["demo-manager"]
    if order.status == "draft":
        schedule_order(session, principal, order_id=order.id, idempotency_key=seed_uuid("osched", key))
    set_execution_policy(
        session,
        principal,
        order_id=order.id,
        weighing_policy=POLICY_WEIGHING_REQUIRED,
        verification_policy=VERIFICATION_SECOND_PERSON,
        completion_tolerance=Decimal("10"),
        allow_short_close=True,
        absolute_tolerance=Decimal("50"),
        percent_tolerance=Decimal("5"),
        idempotency_key=seed_uuid("pol", key),
    )
    split_batches(session, principal, order_id=order.id, count=1, idempotency_key=seed_uuid("split", key))
    return release_order(session, principal, order_id=order.id, idempotency_key=seed_uuid("rel", key))


def _weigh(session: Session, world: DemoWorld, batch, key: str):
    baker = world.principals["demo-baker"]
    verifier = world.principals["demo-manager"]
    opened = open_weighing_session(session, baker, batch_id=batch.id, idempotency_key=seed_uuid("wopen", key))
    for material in _materials(session, batch.id):
        entry = record_weighing(
            session,
            baker,
            session_id=opened.id,
            batch_material_id=material.id,
            quantity=material.planned_gross_quantity,
            measurement_unit_id=world.units["g"].id,
            idempotency_key=seed_uuid("wrec", key, str(material.id)),
            lot_code="DEMO-L1",
        )
        verify_weighing(
            session,
            verifier,
            entry_id=entry.id,
            decision=VERIFY_ACCEPTED,
            idempotency_key=seed_uuid("wver", key, str(material.id)),
        )
    complete_weighing_session(session, baker, session_id=opened.id, idempotency_key=seed_uuid("wdone", key))


def _advance_production(
    session: Session,
    world: DemoWorld,
    key: str,
    product: str,
    *,
    when: date,
    shift: str,
    qty: str,
    priority: int,
) -> None:
    manager = world.principals["demo-manager"]
    baker = world.principals["demo-baker"]
    _plan, order = _plan_order(
        session, world, key, product, when=when, shift=shift, qty=qty, priority=priority
    )
    world.orders[key] = order
    if key == "draft":
        return
    if key == "scheduled":
        schedule_order(session, manager, order_id=order.id, idempotency_key=seed_uuid("osched", key))
        return
    if key == "cancelled":
        schedule_order(session, manager, order_id=order.id, idempotency_key=seed_uuid("osched", key))
        cancel_order(session, manager, order_id=order.id, reason="cancelamento demo", idempotency_key=seed_uuid("can", key))
        return
    order = _release(session, world, order, key)
    world.orders[key] = order
    batches = _batches(session, order.id)
    if key == "released":
        return
    if key == "in_weighing":
        open_weighing_session(session, baker, batch_id=batches[0].id, idempotency_key=seed_uuid("wopen", key))
        return
    for batch in batches:
        _weigh(session, world, batch, f"{key}-{batch.sequence}")
    mark_order_ready(session, manager, order_id=order.id, idempotency_key=seed_uuid("ready", key))
    if key == "ready":
        return
    first = batches[0]
    for step in _steps(session, order.id):
        run = mark_step_ready(
            session, baker, batch_id=first.id, order_step_id=step.id, idempotency_key=seed_uuid("sready", key, str(step.id))
        )
        start_step(
            session,
            baker,
            batch_id=first.id,
            order_step_id=step.id,
            idempotency_key=seed_uuid("sstart", key, str(step.id)),
            expected_row_version=run.row_version,
        )
        if key == "in_progress":
            break
        if key == "on_hold":
            hold_step(
                session,
                baker,
                batch_id=first.id,
                order_step_id=step.id,
                reason="pausa demo",
                idempotency_key=seed_uuid("shold", key),
            )
            hold_order(session, manager, order_id=order.id, reason="bloqueio demo", idempotency_key=seed_uuid("hold", key))
            record_occurrence(
                session,
                baker,
                order_id=order.id,
                batch_id=first.id,
                category=OCCURRENCE_QUALITY,
                severity=SEVERITY_HIGH,
                is_blocking=True,
                description="Ocorrência bloqueante sintética. Demo.",
                idempotency_key=seed_uuid("occ", key),
            )
            break
        complete_step(
            session, baker, batch_id=first.id, order_step_id=step.id, idempotency_key=seed_uuid("sdone", key, str(step.id))
        )
    if key not in {"completed", "short_closed"}:
        return
    for batch in batches:
        for material in _materials(session, batch.id):
            record_consumption(
                session,
                baker,
                batch_id=batch.id,
                batch_material_id=material.id,
                consumption_type=CONSUMPTION_CONSUME,
                quantity=material.planned_gross_quantity,
                measurement_unit_id=world.units["g"].id,
                idempotency_key=seed_uuid("cons", key, str(material.id)),
            )
        record_yield(
            session,
            baker,
            batch_id=batch.id,
            measurement_type=YIELD_POST_BAKE_MASS,
            quantity=batch.target_quantity if key == "completed" else batch.target_quantity * Decimal("0.7"),
            measurement_unit_id=world.units["g"].id,
            idempotency_key=seed_uuid("yld", key, str(batch.id)),
        )
    issue_sheet(session, manager, order_id=order.id, purpose=SHEET_OPERATIONAL, idempotency_key=seed_uuid("sheet1", key))
    issue_sheet(session, manager, order_id=order.id, purpose=SHEET_OPERATIONAL, idempotency_key=seed_uuid("sheet2", key))
    if key == "completed":
        complete_order(session, manager, order_id=order.id, idempotency_key=seed_uuid("done", key))
        return
    short_close_order(
        session, manager, order_id=order.id, reason="encerramento parcial demo", idempotency_key=seed_uuid("short", key)
    )


def seed_production(session: Session, world: DemoWorld, anchor: date) -> None:
    manager = world.principals["demo-manager"]
    baker = world.principals["demo-baker"]
    specs = (
        ("draft", "PAO-FR", 0, "morning", "3300", 80),
        ("scheduled", "PAO-INT", 0, "afternoon", "3300", 60),
        ("released", "FOCACCIA", 0, "morning", "3300", 70),
        ("in_weighing", "PAO-FR", 0, "morning", "3300", 90),
        ("ready", "BRIOCHE", 1, "afternoon", "3300", 50),
        ("in_progress", "PAO-FR", 0, "night", "3300", 85),
        ("on_hold", "PAO-INT", 1, "morning", "3300", 40),
        ("completed", "FOCACCIA", -1, "morning", "3300", 55),
        ("short_closed", "BRIOCHE", -1, "afternoon", "3300", 35),
        ("cancelled", "PAO-FR", 1, "night", "3300", 20),
    )
    for key, product, delta, shift, qty, priority in specs:
        try:
            with session.begin_nested():
                _advance_production(
                    session,
                    world,
                    key,
                    product,
                    when=anchor + timedelta(days=delta),
                    shift=shift,
                    qty=qty,
                    priority=priority,
                )
        except Exception as exc:
            world.gaps.append(f"producao:{key}:{exc}")


def seed_inventory(session: Session, world: DemoWorld, anchor: date) -> None:
    principal = world.principals["demo-owner"]
    policy = create_policy(
        session,
        principal,
        {
            "code": "EST-DEMO",
            "display_name": "Política de estoque demo",
            "effective_from": at(anchor).isoformat(),
            "justification": "política operacional de demonstração",
            "lot_mode": "required",
            "expiry_required": True,
            "lot_consumption": "fefo_suggest",
        },
        idempotency_key=seed_uuid("ipol"),
    )
    publish_policy(session, principal, policy.id, expected_version=policy.row_version, idempotency_key=seed_uuid("ipub"))
    places = []
    for code, kind, name in (
        ("ALM-CENTRAL", "warehouse", "Almoxarifado Central"),
        ("PROD-MASSAS", "production", "Câmara de massas"),
        ("QUAR-1", "quarantine", "Quarentena"),
        ("ALM-BAIRRO", "warehouse", "Almoxarifado Bairro"),
    ):
        est = world.bairro.id if "BAIRRO" in code else world.central.id
        places.append(
            create_location(
                session,
                principal,
                {"establishment_id": est, "code": code, "kind": kind, "display_name": name},
                idempotency_key=seed_uuid("loc", code),
            )
        )
    flour = session.scalar(
        select(Ingredient).where(Ingredient.organization_id == world.organization.id, Ingredient.code == "FAR-TRIGO")
    )
    if flour is None:
        raise RuntimeError("FAR-TRIGO ausente para estoque")
    item = create_item(
        session,
        principal,
        {
            "ingredient_id": flour.id,
            "unit_code": "g",
            "lot_control": "required",
            "expiry_control": True,
            "reorder_point": "5000",
            "safety_stock": "2000",
            "target_quantity": "25000",
        },
        idempotency_key=seed_uuid("iitem"),
    )
    lots = []
    for key, days, qty, location in (
        ("ok", 40, "20000", places[0]),
        ("soon", 3, "4000", places[0]),
        ("block", 20, "1500", places[0]),
        ("quar", 15, "800", places[2]),
    ):
        lot = open_balance(
            session,
            principal,
            {
                "inventory_item_id": item.id,
                "inventory_location_id": location.id,
                "quantity": qty,
                "expires_on": (anchor + timedelta(days=days)).isoformat(),
                "reason": f"abertura demo {key}",
            },
            idempotency_key=seed_uuid("lot", key),
        )
        lots.append(lot)
    set_lot_status(session, principal, lots[2].id, "blocked", "lote bloqueado demo", expected_version=lots[2].row_version, idempotency_key=seed_uuid("lblock"))
    set_lot_status(session, principal, lots[3].id, "quarantined", "quarentena demo", expected_version=lots[3].row_version, idempotency_key=seed_uuid("lquar"))
    suggest_fefo(session, principal, item.id, Decimal("3000"))
    released = world.orders.get("released")
    try:
        with session.begin_nested():
            if released is not None:
                reserve_order(
                    session,
                    principal,
                    {
                        "production_order_id": released.id,
                        "inventory_item_id": item.id,
                        "required_quantity": "2500",
                        "adopt_historical": True,
                        "reason": "adoção demo de ordem anterior à política de estoque",
                    },
                    idempotency_key=seed_uuid("res1"),
                )
                reserve_order(
                    session,
                    principal,
                    {
                        "production_order_id": released.id,
                        "inventory_item_id": item.id,
                        "required_quantity": "90000",
                        "adopt_historical": True,
                        "reason": "adoção demo de reserva parcial",
                    },
                    idempotency_key=seed_uuid("res2"),
                )
            suggest_replenishment(session, principal, {"horizon_days": 7}, idempotency_key=seed_uuid("repl"))
            if released is not None:
                confirm_pick(
                    session,
                    principal,
                    {
                        "production_order_id": released.id,
                        "lines": [
                            {
                                "inventory_item_id": item.id,
                                "inventory_lot_id": lots[0].id,
                                "quantity": "500",
                                "suggested": True,
                            }
                        ],
                    },
                    idempotency_key=seed_uuid("pick1"),
                )
            completed = world.orders.get("completed")
            if completed is not None:
                from app.modules.production_execution.models import ProductionMaterialConsumption

                consumption = session.scalar(
                    select(ProductionMaterialConsumption).where(
                        ProductionMaterialConsumption.production_order_id == completed.id,
                        ProductionMaterialConsumption.consumption_type == "consume",
                    )
                )
                if consumption is not None:
                    post_consumption(
                        session,
                        principal,
                        consumption.id,
                        {
                            "ingredient_id": flour.id,
                            "inventory_lot_id": lots[0].id,
                            "from_location_id": places[0].id,
                        },
                        idempotency_key=seed_uuid("cpost"),
                    )
    except Exception as exc:
        world.gaps.append(f"estoque:reserva:{exc}")
    vendor_id = session.scalar(
        select(Supplier.id).where(Supplier.organization_id == world.organization.id, Supplier.code == "FOR-MOINHO")
    )
    if vendor_id is None:
        world.gaps.append("estoque:compras:fornecedor FOR-MOINHO ausente")
        return
    try:
        with session.begin_nested():
            _seed_procurement_and_count(session, world, principal, item, places, vendor_id, anchor)
    except Exception as exc:
        world.gaps.append(f"estoque:compras:{exc}")


def _seed_procurement_and_count(session, world, principal, item, places, vendor_id, anchor) -> None:
    supplier_item = session.scalar(
        select(SupplierItem).where(
            SupplierItem.organization_id == world.organization.id, SupplierItem.supplier_sku == "SKU-FAR-25"
        )
    )
    other_vendor = session.scalar(
        select(Supplier.id).where(Supplier.organization_id == world.organization.id, Supplier.code == "FOR-LATIC")
    )
    create_requisition(
        session,
        principal,
        {
            "establishment_id": world.central.id,
            "inventory_location_id": places[0].id,
            "justification": "rascunho de cobertura demo",
            "items": [{"inventory_item_id": item.id, "quantity": "2000", "unit_code": "g"}],
        },
        idempotency_key=seed_uuid("req-draft"),
    )
    req_sub = create_requisition(
        session,
        principal,
        {
            "establishment_id": world.central.id,
            "inventory_location_id": places[0].id,
            "justification": "requisição submetida demo",
            "items": [{"inventory_item_id": item.id, "quantity": "3000", "unit_code": "g"}],
        },
        idempotency_key=seed_uuid("req-sub"),
    )
    transition_requisition(
        session, principal, req_sub.id, "submitted", expected_version=req_sub.row_version, idempotency_key=seed_uuid("req-subs")
    )
    req_ok = create_requisition(
        session,
        principal,
        {
            "establishment_id": world.central.id,
            "inventory_location_id": places[0].id,
            "justification": "requisição aprovada e mantida demo",
            "items": [{"inventory_item_id": item.id, "quantity": "4000", "unit_code": "g"}],
        },
        idempotency_key=seed_uuid("req-ok"),
    )
    req_ok = transition_requisition(
        session, principal, req_ok.id, "submitted", expected_version=req_ok.row_version, idempotency_key=seed_uuid("req-oks")
    )
    transition_requisition(
        session, principal, req_ok.id, "approved", expected_version=req_ok.row_version, idempotency_key=seed_uuid("req-oka")
    )
    req = create_requisition(
        session,
        principal,
        {
            "establishment_id": world.central.id,
            "inventory_location_id": places[0].id,
            "justification": "cobertura abaixo do ponto demo",
            "items": [{"inventory_item_id": item.id, "quantity": "10000", "unit_code": "g"}],
        },
        idempotency_key=seed_uuid("req1"),
    )
    req = transition_requisition(session, principal, req.id, "submitted", expected_version=req.row_version, idempotency_key=seed_uuid("reqs"))
    req = transition_requisition(session, principal, req.id, "approved", expected_version=req.row_version, idempotency_key=seed_uuid("reqa"))
    create_quotation(
        session,
        principal,
        {
            "supplier_id": vendor_id,
            "lead_time_days": 4,
            "items": [{"inventory_item_id": item.id, "quantity": "10000", "unit_code": "g", "unit_price": "12.80"}],
        },
        idempotency_key=seed_uuid("quo1"),
    )
    create_quotation(
        session,
        principal,
        {
            "supplier_id": other_vendor or vendor_id,
            "lead_time_days": 6,
            "items": [{"inventory_item_id": item.id, "quantity": "10000", "unit_code": "g", "unit_price": "13.40"}],
        },
        idempotency_key=seed_uuid("quo2"),
    )
    compare_quotations(session, principal, item.id)
    order = create_purchase_order(
        session,
        principal,
        {
            "establishment_id": world.central.id,
            "supplier_id": vendor_id,
            "inventory_location_id": places[0].id,
            "items": [
                {
                    "inventory_item_id": item.id,
                    "supplier_item_id": supplier_item.id if supplier_item is not None else None,
                    "quantity": "8000",
                    "unit_code": "g",
                    "unit_price": "12.90",
                }
            ],
        },
        idempotency_key=seed_uuid("po1"),
    )
    order = transition_order(session, principal, order.id, "approved", expected_version=order.row_version, idempotency_key=seed_uuid("poa"))
    order = transition_order(session, principal, order.id, "issued", expected_version=order.row_version, idempotency_key=seed_uuid("poi"))
    order_item = current_order_items(session, order)[0]
    receipt = receive_order(
        session,
        principal,
        {
            "procurement_order_id": order.id,
            "inventory_location_id": places[0].id,
            "items": [
                {
                    "procurement_order_item_id": order_item.id,
                    "quantity": "4000",
                    "supplier_lot_code": "DEMO-RCP",
                    "expires_on": (anchor + timedelta(days=30)).isoformat(),
                    "observed_unit_price": "13.00",
                }
            ],
        },
        idempotency_key=seed_uuid("rcp1"),
    )
    received = receipt_items(session, receipt.id)
    if received and supplier_item is not None:
        record_observed_price(session, principal, received[0].id, idempotency_key=seed_uuid("obs1"))
    if received:
        return_to_supplier(
            session,
            principal,
            {
                "procurement_receipt_id": receipt.id,
                "inventory_lot_id": received[0].inventory_lot_id,
                "quantity": "200",
                "reason": "embalagem avariada demo",
            },
            idempotency_key=seed_uuid("ret1"),
        )
    full = create_purchase_order(
        session,
        principal,
        {
            "establishment_id": world.central.id,
            "supplier_id": vendor_id,
            "inventory_location_id": places[0].id,
            "items": [
                {
                    "inventory_item_id": item.id,
                    "supplier_item_id": supplier_item.id if supplier_item is not None else None,
                    "quantity": "3000",
                    "unit_code": "g",
                    "unit_price": "12.70",
                }
            ],
        },
        idempotency_key=seed_uuid("po2"),
    )
    full = transition_order(session, principal, full.id, "approved", expected_version=full.row_version, idempotency_key=seed_uuid("po2a"))
    full = transition_order(session, principal, full.id, "issued", expected_version=full.row_version, idempotency_key=seed_uuid("po2i"))
    full_item = current_order_items(session, full)[0]
    receive_order(
        session,
        principal,
        {
            "procurement_order_id": full.id,
            "inventory_location_id": places[0].id,
            "items": [
                {
                    "procurement_order_item_id": full_item.id,
                    "quantity": "3000",
                    "supplier_lot_code": "DEMO-RCP-FULL",
                    "expires_on": (anchor + timedelta(days=45)).isoformat(),
                    "observed_unit_price": "12.70",
                }
            ],
        },
        idempotency_key=seed_uuid("rcp2"),
    )
    transition_requisition(session, principal, req.id, "converted", expected_version=req.row_version, idempotency_key=seed_uuid("reqc"))
    from app.modules.inventory_procurement.models import InventoryCountScope

    count = create_count(
        session,
        principal,
        {"inventory_location_id": places[0].id, "cutoff_at": at(anchor).isoformat(), "require_second_count": True},
        idempotency_key=seed_uuid("cnt"),
    )
    freeze_count_scope(session, principal, count.id, expected_version=count.row_version, idempotency_key=seed_uuid("cntf"))
    scope = session.scalar(select(InventoryCountScope).where(InventoryCountScope.inventory_count_session_id == count.id))
    if scope is None:
        return
    record_count(
        session,
        principal,
        count.id,
        {"inventory_count_scope_id": scope.id, "pass_number": 1, "quantity": "18000"},
        idempotency_key=seed_uuid("cnt1"),
    )
    record_count(
        session,
        principal,
        count.id,
        {"inventory_count_scope_id": scope.id, "pass_number": 2, "quantity": "17950"},
        idempotency_key=seed_uuid("cnt2"),
    )
    session.refresh(count)
    review_count(
        session,
        principal,
        count.id,
        {"decision": "reviewed", "reason": "divergência demo"},
        expected_version=count.row_version,
        idempotency_key=seed_uuid("cntr"),
    )


def seed_compliance(session: Session, world: DemoWorld, anchor: date) -> None:
    principal = world.principals["demo-reviewer"]
    version = world.products["PAO-FR"]["version"]
    dossier = create_dossier(
        session,
        world.principals["demo-owner"],
        {"formulation_version_id": version.id, "establishment_id": world.central.id},
        idempotency_key=seed_uuid("dos1"),
    )
    save_profile(
        session,
        world.principals["demo-owner"],
        dossier.id,
        {
            "jurisdiction": "BR",
            "evaluation_date": anchor.isoformat(),
            "packed_food": True,
            "packed_away_from_consumer": True,
            "sales_channel": "retail",
            "physical_state": "solid",
            "ready_to_eat": True,
            "category_confirmed": True,
            "net_content_g": "50",
            "package_area_cm2": "200",
            "purpose": "rotulagem demo",
        },
        expected_version=None,
    )
    run_evaluation(session, principal, dossier.id, idempotency_key=seed_uuid("eval1"), expected_version=None)
    thin = create_dossier(
        session,
        world.principals["demo-owner"],
        {"formulation_version_id": world.products["BOLO"]["version"].id},
        idempotency_key=seed_uuid("dos2"),
    )
    save_profile(session, world.principals["demo-owner"], thin.id, {"purpose": "contexto insuficiente"}, expected_version=None)


def seed_costing(session: Session, world: DemoWorld, anchor: date) -> None:
    principal = world.principals["demo-owner"]
    policy = create_costing_policy(
        session,
        principal,
        {
            "code": "CUS-DEMO",
            "display_name": "Política de custeio demo",
            "effective_from": at(anchor).isoformat(),
            "justification": "política sintética",
        },
        idempotency_key=seed_uuid("cpol"),
    )
    publish_costing_policy(session, principal, policy.id, expected_version=policy.row_version, idempotency_key=seed_uuid("cpub"))
    from app.modules.costing_pricing.services import latest_version

    version = latest_version(session, policy.id)
    calc = run_calculation(
        session,
        principal,
        {
            "kind": "planned",
            "policy_version_id": str(version.id),
            "valuation_at": at(anchor).isoformat(),
            "formulation_version_id": str(world.products["PAO-FR"]["version"].id),
            "scale_calculation_id": str(world.products["PAO-FR"]["scale"].id),
        },
        idempotency_key=seed_uuid("ccalc"),
    )
    completed = world.orders.get("completed")
    if completed is not None:
        run_calculation(
            session,
            principal,
            {
                "kind": "actual",
                "policy_version_id": str(version.id),
                "valuation_at": at(anchor).isoformat(),
                "production_order_id": str(completed.id),
            },
            idempotency_key=seed_uuid("ccalc-act"),
        )
    if calc.total_amount is not None:
        simulate_price(
            session,
            principal,
            calc.id,
            {"kind": "markup_percent", "percent": "60", "channel": "own_counter"},
            idempotency_key=seed_uuid("sim1"),
        )
        price = create_practiced_price(
            session,
            principal,
            {
                "technical_product_id": str(world.products["PAO-FR"]["product"].id),
                "channel": "own_counter",
                "amount": "8.90",
                "currency": "BRL",
                "valid_from": at(anchor).isoformat(),
                "justification": "preço demo",
            },
            idempotency_key=seed_uuid("price1"),
        )
        decide_price(
            session,
            principal,
            price.id,
            {"decision": "publish", "notes": "preço demo", "reinforced_confirmation": True},
            expected_version=price.row_version,
            idempotency_key=seed_uuid("pricea"),
        )


def seed_reporting(session: Session, world: DemoWorld, anchor: date) -> None:
    principal = world.principals["demo-owner"]
    create_saved_view(
        session,
        principal,
        {
            "code": "REL-DEMO-PROD",
            "display_name": "Produção do âncora",
            "report_code": "production",
            "filters": {
                "period_start": at(anchor, days=-2).isoformat(),
                "period_end": at(anchor, days=2).isoformat(),
            },
        },
        idempotency_key=seed_uuid("view1"),
    )
    create_snapshot(
        session,
        principal,
        "production",
        {
            "period_start": at(anchor, days=-2).isoformat(),
            "period_end": at(anchor, days=2).isoformat(),
        },
        idempotency_key=seed_uuid("snap1"),
    )


def seed_ai(session: Session, world: DemoWorld) -> None:
    principal = world.principals["demo-formulator"]
    gateway = FakeModelGateway()
    result = ingest(
        session,
        IngestRequest(
            source_kind="technical",
            authority_level="curated",
            title="Manual sintético de pão (Demo)",
            content="Criar pão com farinha de trigo. Fonte sintética não normativa.",
            organization_id=world.organization.id,
        ),
    )
    review_source_version(result.version, decision="reviewed", reviewed_by_user_id=world.users["demo-formulator"].id)
    flour = world.ingredients["FAR-TRIGO"]
    awaiting = propose_recipe(
        session,
        principal,
        {
            "intent": "create_recipe",
            "objective": "Criar pão com farinha de trigo",
            "product_type": "pão",
            "allowed_ingredient_version_ids": [str(flour.id)],
        },
        idempotency_key=seed_uuid("ai1"),
        gateway=gateway,
    )
    propose_recipe(
        session,
        principal,
        {"intent": "create_recipe", "objective": "Proposta sem evidência útil"},
        idempotency_key=seed_uuid("ai-empty"),
        gateway=gateway,
    )
    if awaiting is not None:
        review_changes(
            session,
            principal,
            awaiting.id,
            decisions=[{"change_key": "added:" + str(flour.id), "decision": "accepted"}],
            expected_version=awaiting.row_version,
        )
        decide_proposal(
            session,
            principal,
            awaiting.id,
            decision="accepted",
            notes="aceite demo",
            confirm=True,
            idempotency_key=seed_uuid("ai-dec"),
            expected_version=None,
        )
        materialize_recipe_proposal(
            session,
            principal,
            awaiting.id,
            idempotency_key=seed_uuid("ai-mat"),
            expected_version=None,
        )


def seed_demo(session: Session, *, anchor: date, dry_run: bool = False) -> DemoWorld:
    seed_reference(session)
    world = seed_identity(session)
    seed_ingredients(session, world)
    seed_recipes(session, world)
    seed_production(session, world, anchor)

    def _safe(label: str, fn) -> None:
        try:
            with session.begin_nested():
                fn()
        except Exception as exc:
            world.gaps.append(f"{label}: {exc}")

    _safe("estoque", lambda: seed_inventory(session, world, anchor))
    _safe("conformidade", lambda: seed_compliance(session, world, anchor))
    _safe("custos", lambda: seed_costing(session, world, anchor))
    _safe("relatorios", lambda: seed_reporting(session, world, anchor))
    _safe("ia", lambda: seed_ai(session, world))
    if dry_run:
        session.flush()
    return world
