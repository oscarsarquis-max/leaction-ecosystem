from decimal import Decimal

from app.modules.formula_lab.models import (
    Approval,
    Formulation,
    FormulationItem,
    FormulationVersion,
    ProcessStep,
    TechnicalProduct,
)
from app.modules.identity_organization.authorization import (
    Association,
    Principal,
    permissions_for_role,
)
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
    IngredientNutrient,
    IngredientVersion,
    MeasurementUnit,
    NutrientDefinition,
    Supplier,
)
from app.modules.knowledge_grounding.models import (
    KnowledgeTag,
    NutritionExpectationProfile,
    NutritionExpectationProfileItem,
)
from sqlalchemy.orm import Session


def org(session: Session, slug: str) -> Organization:
    row = Organization(
        slug=slug,
        legal_name=f"{slug} LTDA",
        display_name=slug,
        status="active",
    )
    session.add(row)
    session.flush()
    return row


def establishment(session: Session, organization: Organization, code: str) -> Establishment:
    row = Establishment(
        organization_id=organization.id,
        code=code,
        display_name=code,
        status="active",
    )
    session.add(row)
    session.flush()
    return row


def user(session: Session, email: str) -> AppUser:
    row = AppUser(email=email, display_name=email.split("@")[0], status="active")
    session.add(row)
    session.flush()
    return row


def auth_identity(
    session: Session,
    app_user: AppUser,
    issuer: str,
    subject: str,
) -> AuthIdentity:
    row = AuthIdentity(user_id=app_user.id, issuer=issuer, subject=subject, status="active")
    session.add(row)
    session.flush()
    return row


def membership(
    session: Session, organization: Organization, app_user: AppUser, role: str = "owner"
) -> OrganizationMembership:
    row = OrganizationMembership(
        organization_id=organization.id,
        user_id=app_user.id,
        legacy_role_label=role,
        status="active",
    )
    session.add(row)
    session.flush()
    session.add(
        OrganizationMembershipRole(
            organization_id=organization.id,
            membership_id=row.id,
            role=role,
            granted_by_user_id=app_user.id,
            reason="test",
        )
    )
    session.flush()
    return row


def gram(session: Session) -> MeasurementUnit:
    existing = session.query(MeasurementUnit).filter_by(code="g").one_or_none()
    if existing:
        return existing
    row = MeasurementUnit(
        code="g",
        name="grama",
        plural_name="gramas",
        dimension="mass",
        si_factor=Decimal("0.001"),
        symbol="g",
        status="active",
    )
    session.add(row)
    session.flush()
    return row


def kilogram(session: Session) -> MeasurementUnit:
    existing = session.query(MeasurementUnit).filter_by(code="kg").one_or_none()
    if existing:
        return existing
    row = MeasurementUnit(
        code="kg",
        name="quilograma",
        plural_name="quilogramas",
        dimension="mass",
        si_factor=Decimal("1"),
        symbol="kg",
        status="active",
    )
    session.add(row)
    session.flush()
    return row


def milliliter(session: Session) -> MeasurementUnit:
    existing = session.query(MeasurementUnit).filter_by(code="ml").one_or_none()
    if existing:
        return existing
    row = MeasurementUnit(
        code="ml",
        name="mililitro",
        plural_name="mililitros",
        dimension="volume",
        si_factor=Decimal("0.000001"),
        symbol="ml",
        status="active",
    )
    session.add(row)
    session.flush()
    return row


def nutrient(session: Session, unit: MeasurementUnit, code: str = "protein") -> NutrientDefinition:
    row = NutrientDefinition(
        code=code,
        name=code,
        unit_id=unit.id,
        status="active",
    )
    session.add(row)
    session.flush()
    return row


def allergen(session: Session, code: str = "gluten") -> Allergen:
    row = Allergen(code=code, name=code, status="active")
    session.add(row)
    session.flush()
    return row


def ingredient(
    session: Session,
    organization: Organization,
    code: str,
    ingredient_type: str = "simple",
) -> Ingredient:
    row = Ingredient(
        organization_id=organization.id,
        code=code,
        display_name=code,
        ingredient_type=ingredient_type,
        status="active",
    )
    session.add(row)
    session.flush()
    return row


def version(
    session: Session,
    item: Ingredient,
    unit: MeasurementUnit,
    number: int = 1,
    status: str = "draft",
) -> IngredientVersion:
    row = IngredientVersion(
        ingredient_id=item.id,
        organization_id=item.organization_id,
        version_number=number,
        status=status,
        nutrition_basis_type="per_100g",
        nutrition_basis_quantity=Decimal("100"),
        nutrition_basis_unit_id=unit.id,
    )
    session.add(row)
    session.flush()
    return row


def technical_product(
    session: Session,
    organization: Organization,
    code: str,
    status: str = "active",
) -> TechnicalProduct:
    # Compatibilidade com seeds/testes antigos (development/approved/retired).
    mapped = {
        "development": "active",
        "approved": "active",
        "retired": "inactive",
    }.get(status, status)
    row = TechnicalProduct(
        organization_id=organization.id,
        code=code,
        display_name=code,
        status=mapped,
        purpose="final",
        supply_mode="produced",
    )
    session.add(row)
    session.flush()
    return row


def formulation(
    session: Session,
    product: TechnicalProduct,
    code: str,
    status: str = "development",
) -> Formulation:
    row = Formulation(
        organization_id=product.organization_id,
        technical_product_id=product.id,
        code=code,
        display_name=code,
        status=status,
    )
    session.add(row)
    session.flush()
    return row


def formulation_version(
    session: Session,
    recipe: Formulation,
    number: int = 1,
    status: str = "draft",
    created_by_user_id=None,
) -> FormulationVersion:
    row = FormulationVersion(
        organization_id=recipe.organization_id,
        formulation_id=recipe.id,
        version_number=number,
        status=status,
        created_by_user_id=created_by_user_id,
    )
    session.add(row)
    session.flush()
    return row


def formulation_item(
    session: Session,
    version: FormulationVersion,
    ingredient_version: IngredientVersion,
    unit: MeasurementUnit,
    sequence: int,
    net_quantity: Decimal,
    correction_factor: Decimal = Decimal("1"),
    is_flour_basis: bool = False,
    role: str = "ingredient",
) -> FormulationItem:
    row = FormulationItem(
        organization_id=version.organization_id,
        formulation_version_id=version.id,
        ingredient_version_id=ingredient_version.id,
        sequence=sequence,
        net_quantity=net_quantity,
        measurement_unit_id=unit.id,
        correction_factor=correction_factor,
        is_flour_basis=is_flour_basis,
        role=role,
    )
    session.add(row)
    session.flush()
    return row


def process_step(
    session: Session,
    version: FormulationVersion,
    sequence: int,
    title: str = "misturar",
    instructions: str = "misturar até homogêneo",
) -> ProcessStep:
    row = ProcessStep(
        organization_id=version.organization_id,
        formulation_version_id=version.id,
        sequence=sequence,
        title=title,
        instructions=instructions,
        duration_seconds=600,
        temperature_celsius=Decimal("24"),
    )
    session.add(row)
    session.flush()
    return row


def principal_for(app_user: AppUser, organization: Organization, role: str) -> Principal:
    association = Association(
        organization_id=organization.id,
        status="active",
        permissions=permissions_for_role(role),
        roles=(role,),
        organization_display_name=organization.display_name,
        organization_slug=organization.slug,
    )
    return Principal(
        user_id=app_user.id,
        display_name=app_user.display_name,
        status="active",
        issuer="test",
        subject=str(app_user.id),
        associations=(association,),
        selected=association,
    )


def approve_version(
    session: Session,
    version: FormulationVersion,
    actor: AppUser,
    decision: str = "approved",
) -> Approval:
    row = Approval(
        organization_id=version.organization_id,
        formulation_version_id=version.id,
        actor_user_id=actor.id,
        decision=decision,
    )
    session.add(row)
    session.flush()
    return row


def ensure_published_recipe(
    session: Session,
    product: TechnicalProduct,
    actor: AppUser,
    code: str | None = None,
) -> FormulationVersion:
    """Publica receita mínima para liberar OP de produto produzido (CURSOR-028-C)."""
    from app.modules.formula_lab.rules import publish_formulation_version

    recipe = formulation(session, product, code or f"F-{product.code}")
    row = formulation_version(session, recipe)
    approve_version(session, row, actor)
    publish_formulation_version(session, row)
    return row


def ingredient_nutrient(
    session: Session,
    version: IngredientVersion,
    definition: NutrientDefinition,
    value: Decimal | None,
    value_status: str = "measured",
    limit_of_quantification: Decimal | None = None,
    loq_unit_id=None,
    method_or_source: str | None = None,
) -> IngredientNutrient:
    row = IngredientNutrient(
        organization_id=version.organization_id,
        ingredient_version_id=version.id,
        nutrient_id=definition.id,
        value=value,
        value_status=value_status,
        limit_of_quantification=limit_of_quantification,
        loq_unit_id=loq_unit_id,
        method_or_source=method_or_source,
    )
    session.add(row)
    session.flush()
    return row


def published_ingredient(
    session: Session,
    organization: Organization,
    unit: MeasurementUnit,
    code: str,
    ingredient_type: str = "simple",
) -> IngredientVersion:
    item = ingredient(session, organization, code, ingredient_type=ingredient_type)
    return version(session, item, unit, status="published")


def draft_ingredient(
    session: Session,
    organization: Organization,
    unit: MeasurementUnit,
    code: str,
    ingredient_type: str = "simple",
) -> IngredientVersion:
    item = ingredient(session, organization, code, ingredient_type=ingredient_type)
    return version(session, item, unit, status="draft")


def publish_ingredient_version(session: Session, row: IngredientVersion) -> IngredientVersion:
    row.status = "published"
    session.flush()
    return row


def published_dossier(
    session: Session,
    organization: Organization,
    unit: MeasurementUnit,
    code: str,
    nutrients: dict[NutrientDefinition, Decimal],
    ingredient_type: str = "simple",
) -> IngredientVersion:
    row = draft_ingredient(session, organization, unit, code, ingredient_type=ingredient_type)
    for definition, value in nutrients.items():
        ingredient_nutrient(session, row, definition, value)
    return publish_ingredient_version(session, row)


def supplier(session: Session, organization: Organization, code: str) -> Supplier:
    row = Supplier(
        organization_id=organization.id,
        code=code,
        display_name=code,
        status="active",
    )
    session.add(row)
    session.flush()
    return row


def knowledge_tag(
    session: Session,
    code: str,
    category: str = "norm",
    display_name: str | None = None,
) -> KnowledgeTag:
    row = KnowledgeTag(
        code=code,
        display_name=display_name or code,
        category=category,
        status="active",
    )
    session.add(row)
    session.flush()
    return row


def expectation_profile(
    session: Session,
    code: str,
    nutrients: list[NutrientDefinition],
    organization: Organization | None = None,
    purpose: str = "technical",
) -> NutritionExpectationProfile:
    row = NutritionExpectationProfile(
        organization_id=organization.id if organization else None,
        code=code,
        display_name=code,
        purpose=purpose,
        status="active",
    )
    session.add(row)
    session.flush()
    for sequence, definition in enumerate(nutrients, start=1):
        session.add(
            NutritionExpectationProfileItem(
                profile_id=row.id,
                nutrient_definition_id=definition.id,
                required=True,
                sequence=sequence,
            )
        )
    session.flush()
    return row
