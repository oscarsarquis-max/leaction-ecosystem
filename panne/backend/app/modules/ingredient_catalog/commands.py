from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.identity_organization.authorization import (
    PERMISSION_INGREDIENT_CREATE,
    PERMISSION_INGREDIENT_PUBLISH,
    PERMISSION_INGREDIENT_READ,
    PERMISSION_INGREDIENT_RETIRE,
    PERMISSION_INGREDIENT_UPDATE_DRAFT,
    PERMISSION_SUPPLIER_MANAGE,
    PERMISSION_SUPPLIER_PRICE_RECORD,
    PERMISSION_SUPPLIER_READ,
    Principal,
    require_permission,
)
from app.modules.ingredient_catalog.completeness import project_completeness
from app.modules.ingredient_catalog.models import (
    Allergen,
    DataSource,
    Ingredient,
    IngredientAllergen,
    IngredientCommand,
    IngredientComposition,
    IngredientNutrient,
    IngredientVersion,
    MeasurementUnit,
    NutrientDefinition,
    Supplier,
    SupplierItem,
    SupplierItemPrice,
)
from app.modules.ingredient_catalog.rules import (
    CompositionCycleError,
    PublishedVersionFrozenError,
    assert_acyclic_composition,
    ensure_version_editable,
)
from app.modules.production_planning.errors import (
    ConcurrencyError,
    IdempotencyConflictError,
    ImmutableError,
    InvalidStateError,
    ValidationError,
)
from app.modules.production_planning.support import as_decimal, digest, require_positive

TYPES = {"simple", "composite", "preparation"}
PRESENCE = {"contains", "may_contain", "not_declared"}
NUTRIENT_STATUS = {"measured", "known_zero", "below_loq", "not_detected", "unknown"}
COMPONENT_TYPES = {"constituent", "preparation"}
CURRENCIES = {"BRL", "USD", "EUR"}


def _org(principal: Principal) -> UUID:
    if principal.selected is None:
        raise ValidationError("organizacao_nao_selecionada")
    return principal.selected.organization_id


def _bump(row) -> None:
    row.row_version = int(row.row_version) + 1
    row.updated_at = datetime.now(UTC)


def _match(row, expected: int | None) -> None:
    if expected is None:
        return
    if int(row.row_version) != int(expected):
        raise ConcurrencyError("versao_conflito")


def _replay(
    session: Session,
    organization_id: UUID,
    idempotency_key: UUID,
    command: str,
    payload: dict,
):
    row = session.scalar(
        select(IngredientCommand).where(
            IngredientCommand.organization_id == organization_id,
            IngredientCommand.idempotency_key == idempotency_key,
        )
    )
    if row is None:
        return None
    if row.command != command or row.payload_digest != digest(payload):
        raise IdempotencyConflictError("idempotencia_conflito")
    return row


def _remember(
    session: Session,
    *,
    organization_id: UUID,
    idempotency_key: UUID,
    command: str,
    payload: dict,
    resource_type: str,
    resource_id: UUID,
    actor_user_id: UUID,
) -> IngredientCommand:
    row = IngredientCommand(
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command=command,
        payload_digest=digest(payload),
        resource_type=resource_type,
        resource_id=resource_id,
        actor_user_id=actor_user_id,
    )
    session.add(row)
    session.flush()
    return row


def _ingredient(session: Session, organization_id: UUID, ingredient_id: UUID) -> Ingredient:
    row = session.scalar(
        select(Ingredient).where(
            Ingredient.id == ingredient_id,
            Ingredient.organization_id == organization_id,
        )
    )
    if row is None:
        raise ValidationError("recurso_nao_encontrado")
    return row


def _version(
    session: Session, organization_id: UUID, ingredient_id: UUID, version_id: UUID
) -> IngredientVersion:
    row = session.scalar(
        select(IngredientVersion).where(
            IngredientVersion.id == version_id,
            IngredientVersion.ingredient_id == ingredient_id,
            IngredientVersion.organization_id == organization_id,
        )
    )
    if row is None:
        raise ValidationError("recurso_nao_encontrado")
    return row


def _mass_unit(session: Session, unit_id: UUID) -> MeasurementUnit:
    unit = session.get(MeasurementUnit, unit_id)
    if unit is None or unit.dimension != "mass" or unit.status != "active":
        raise ValidationError("unidade de massa inválida")
    return unit


def _text(value: str, label: str, maximum: int = 200) -> str:
    clean = value.strip()
    if not clean:
        raise ValidationError(f"{label} obrigatório")
    if len(clean) > maximum:
        raise ValidationError(f"{label} excede o limite")
    return clean


def create_ingredient(
    session: Session,
    principal: Principal,
    *,
    code: str,
    display_name: str,
    ingredient_type: str,
    nutrition_basis_unit_id: UUID,
    notes: str | None,
    idempotency_key: UUID,
) -> Ingredient:
    require_permission(principal, PERMISSION_INGREDIENT_CREATE)
    organization_id = _org(principal)
    payload = {
        "code": code,
        "display_name": display_name,
        "ingredient_type": ingredient_type,
        "nutrition_basis_unit_id": str(nutrition_basis_unit_id),
        "notes": notes,
    }
    replay = _replay(session, organization_id, idempotency_key, "ingredient.create", payload)
    if replay is not None:
        return _ingredient(session, organization_id, replay.resource_id)
    if ingredient_type not in TYPES:
        raise ValidationError("tipo de ingrediente inválido")
    _mass_unit(session, nutrition_basis_unit_id)
    identity = Ingredient(
        organization_id=organization_id,
        code=_text(code, "código", 80),
        display_name=_text(display_name, "nome"),
        ingredient_type=ingredient_type,
        status="active",
    )
    session.add(identity)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ValidationError("código já utilizado nesta organização") from exc
    session.add(
        IngredientVersion(
            ingredient_id=identity.id,
            organization_id=organization_id,
            version_number=1,
            status="draft",
            nutrition_basis_unit_id=nutrition_basis_unit_id,
            notes=notes.strip() if notes else None,
            created_by_user_id=principal.user_id,
        )
    )
    session.flush()
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="ingredient.create",
        payload=payload,
        resource_type="ingredient",
        resource_id=identity.id,
        actor_user_id=principal.user_id,
    )
    return identity


def update_identity(
    session: Session,
    principal: Principal,
    *,
    ingredient_id: UUID,
    display_name: str | None,
    code: str | None,
    status: str | None,
    expected_version: int | None,
) -> Ingredient:
    require_permission(principal, PERMISSION_INGREDIENT_UPDATE_DRAFT)
    organization_id = _org(principal)
    row = _ingredient(session, organization_id, ingredient_id)
    _match(row, expected_version)
    if code is not None:
        row.code = _text(code, "código", 80)
    if display_name is not None:
        row.display_name = _text(display_name, "nome")
    if status is not None:
        if status not in {"active", "inactive"}:
            raise ValidationError("situação inválida")
        require_permission(principal, PERMISSION_INGREDIENT_RETIRE)
        row.status = status
    _bump(row)
    session.flush()
    return row


def create_version(
    session: Session,
    principal: Principal,
    *,
    ingredient_id: UUID,
    source_version_id: UUID | None,
    nutrition_basis_unit_id: UUID,
    notes: str | None,
    idempotency_key: UUID,
) -> IngredientVersion:
    require_permission(principal, PERMISSION_INGREDIENT_UPDATE_DRAFT)
    organization_id = _org(principal)
    identity = _ingredient(session, organization_id, ingredient_id)
    payload = {
        "ingredient_id": str(ingredient_id),
        "source_version_id": str(source_version_id) if source_version_id else None,
        "nutrition_basis_unit_id": str(nutrition_basis_unit_id),
        "notes": notes,
    }
    replay = _replay(
        session, organization_id, idempotency_key, "ingredient.version.create", payload
    )
    if replay is not None:
        return _version(session, organization_id, ingredient_id, replay.resource_id)
    _mass_unit(session, nutrition_basis_unit_id)
    next_number = (
        session.scalar(
            select(func.coalesce(func.max(IngredientVersion.version_number), 0)).where(
                IngredientVersion.ingredient_id == identity.id
            )
        )
        or 0
    ) + 1
    row = IngredientVersion(
        ingredient_id=identity.id,
        organization_id=organization_id,
        version_number=next_number,
        status="draft",
        nutrition_basis_unit_id=nutrition_basis_unit_id,
        notes=notes.strip() if notes else None,
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    if source_version_id is not None:
        source = _version(session, organization_id, ingredient_id, source_version_id)
        _copy_dossier(session, source, row)
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="ingredient.version.create",
        payload=payload,
        resource_type="ingredient_version",
        resource_id=row.id,
        actor_user_id=principal.user_id,
    )
    return row


def _copy_dossier(session: Session, source: IngredientVersion, target: IngredientVersion) -> None:
    target.data_source_id = source.data_source_id
    for line in session.scalars(
        select(IngredientComposition).where(
            IngredientComposition.parent_ingredient_version_id == source.id
        )
    ):
        session.add(
            IngredientComposition(
                organization_id=target.organization_id,
                parent_ingredient_version_id=target.id,
                component_ingredient_version_id=line.component_ingredient_version_id,
                component_type=line.component_type,
                quantity=line.quantity,
                measurement_unit_id=line.measurement_unit_id,
                sequence=line.sequence,
            )
        )
    for line in session.scalars(
        select(IngredientNutrient).where(IngredientNutrient.ingredient_version_id == source.id)
    ):
        session.add(
            IngredientNutrient(
                organization_id=target.organization_id,
                ingredient_version_id=target.id,
                nutrient_id=line.nutrient_id,
                value=line.value,
                value_status=line.value_status,
                limit_of_quantification=line.limit_of_quantification,
                loq_unit_id=line.loq_unit_id,
                method_or_source=line.method_or_source,
            )
        )
    for line in session.scalars(
        select(IngredientAllergen).where(IngredientAllergen.ingredient_version_id == source.id)
    ):
        session.add(
            IngredientAllergen(
                organization_id=target.organization_id,
                ingredient_version_id=target.id,
                allergen_id=line.allergen_id,
                presence=line.presence,
                data_source_id=line.data_source_id,
                evidence_note=line.evidence_note,
            )
        )
    session.flush()


def update_draft(
    session: Session,
    principal: Principal,
    *,
    ingredient_id: UUID,
    version_id: UUID,
    notes: str | None,
    data_source_id: UUID | None,
    expected_version: int | None,
) -> IngredientVersion:
    require_permission(principal, PERMISSION_INGREDIENT_UPDATE_DRAFT)
    organization_id = _org(principal)
    row = _version(session, organization_id, ingredient_id, version_id)
    _match(row, expected_version)
    try:
        ensure_version_editable(row)
    except PublishedVersionFrozenError as exc:
        raise ImmutableError("published_frozen") from exc
    if data_source_id is not None:
        source = session.get(DataSource, data_source_id)
        if source is None or source.status != "active":
            raise ValidationError("fonte inválida")
        row.data_source_id = data_source_id
    if notes is not None:
        row.notes = notes.strip() or None
    _bump(row)
    session.flush()
    return row


def publish_version(
    session: Session,
    principal: Principal,
    *,
    ingredient_id: UUID,
    version_id: UUID,
    expected_version: int | None,
    idempotency_key: UUID,
) -> IngredientVersion:
    require_permission(principal, PERMISSION_INGREDIENT_PUBLISH)
    organization_id = _org(principal)
    payload = {"ingredient_id": str(ingredient_id), "version_id": str(version_id)}
    replay = _replay(session, organization_id, idempotency_key, "ingredient.publish", payload)
    if replay is not None:
        return _version(session, organization_id, ingredient_id, replay.resource_id)
    identity = _ingredient(session, organization_id, ingredient_id)
    row = _version(session, organization_id, ingredient_id, version_id)
    _match(row, expected_version)
    if row.status != "draft":
        raise InvalidStateError("transicao_invalida")
    projection = project_completeness(session, identity, row)
    if not projection["ready_to_publish"]:
        raise ValidationError(projection["items"][0]["label"])
    current = session.scalar(
        select(IngredientVersion).where(
            IngredientVersion.ingredient_id == identity.id,
            IngredientVersion.status == "published",
        )
    )
    if current is not None:
        current.status = "retired"
        _bump(current)
        session.flush()
    row.status = "published"
    _bump(row)
    session.flush()
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="ingredient.publish",
        payload=payload,
        resource_type="ingredient_version",
        resource_id=row.id,
        actor_user_id=principal.user_id,
    )
    return row


def retire_version(
    session: Session,
    principal: Principal,
    *,
    ingredient_id: UUID,
    version_id: UUID,
    expected_version: int | None,
    idempotency_key: UUID,
) -> IngredientVersion:
    require_permission(principal, PERMISSION_INGREDIENT_RETIRE)
    organization_id = _org(principal)
    payload = {"ingredient_id": str(ingredient_id), "version_id": str(version_id)}
    replay = _replay(session, organization_id, idempotency_key, "ingredient.retire", payload)
    if replay is not None:
        return _version(session, organization_id, ingredient_id, replay.resource_id)
    row = _version(session, organization_id, ingredient_id, version_id)
    _match(row, expected_version)
    if row.status != "published":
        raise InvalidStateError("transicao_invalida")
    row.status = "retired"
    _bump(row)
    session.flush()
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="ingredient.retire",
        payload=payload,
        resource_type="ingredient_version",
        resource_id=row.id,
        actor_user_id=principal.user_id,
    )
    return row


def upsert_composition(
    session: Session,
    principal: Principal,
    *,
    ingredient_id: UUID,
    version_id: UUID,
    component_version_id: UUID,
    component_type: str,
    quantity: str,
    measurement_unit_id: UUID,
    sequence: int,
    expected_version: int | None,
) -> IngredientComposition:
    require_permission(principal, PERMISSION_INGREDIENT_UPDATE_DRAFT)
    organization_id = _org(principal)
    parent = _version(session, organization_id, ingredient_id, version_id)
    _match(parent, expected_version)
    try:
        ensure_version_editable(parent)
    except PublishedVersionFrozenError as exc:
        raise ImmutableError("published_frozen") from exc
    if component_type not in COMPONENT_TYPES:
        raise ValidationError("papel de composição inválido")
    component = session.scalar(
        select(IngredientVersion).where(
            IngredientVersion.id == component_version_id,
            IngredientVersion.organization_id == organization_id,
        )
    )
    if component is None:
        raise ValidationError("componente inexistente")
    _mass_unit(session, measurement_unit_id)
    qty = require_positive(as_decimal(quantity, "quantidade"), "quantidade")
    try:
        assert_acyclic_composition(session, parent.id, component.id, organization_id)
    except CompositionCycleError as exc:
        raise ValidationError("composição cíclica rejeitada") from exc
    row = session.scalar(
        select(IngredientComposition).where(
            IngredientComposition.parent_ingredient_version_id == parent.id,
            IngredientComposition.component_ingredient_version_id == component.id,
        )
    )
    if row is None:
        row = IngredientComposition(
            organization_id=organization_id,
            parent_ingredient_version_id=parent.id,
            component_ingredient_version_id=component.id,
            component_type=component_type,
            quantity=qty,
            measurement_unit_id=measurement_unit_id,
            sequence=sequence,
        )
        session.add(row)
    else:
        row.component_type = component_type
        row.quantity = qty
        row.measurement_unit_id = measurement_unit_id
        row.sequence = sequence
    _bump(parent)
    session.flush()
    return row


def remove_composition(
    session: Session,
    principal: Principal,
    *,
    ingredient_id: UUID,
    version_id: UUID,
    composition_id: UUID,
    expected_version: int | None,
) -> None:
    require_permission(principal, PERMISSION_INGREDIENT_UPDATE_DRAFT)
    organization_id = _org(principal)
    parent = _version(session, organization_id, ingredient_id, version_id)
    _match(parent, expected_version)
    try:
        ensure_version_editable(parent)
    except PublishedVersionFrozenError as exc:
        raise ImmutableError("published_frozen") from exc
    row = session.scalar(
        select(IngredientComposition).where(
            IngredientComposition.id == composition_id,
            IngredientComposition.parent_ingredient_version_id == parent.id,
        )
    )
    if row is None:
        raise ValidationError("recurso_nao_encontrado")
    session.delete(row)
    _bump(parent)
    session.flush()


def upsert_nutrient(
    session: Session,
    principal: Principal,
    *,
    ingredient_id: UUID,
    version_id: UUID,
    nutrient_id: UUID,
    value: str | None,
    value_status: str,
    limit_of_quantification: str | None,
    loq_unit_id: UUID | None,
    method_or_source: str | None,
    expected_version: int | None,
) -> IngredientNutrient:
    require_permission(principal, PERMISSION_INGREDIENT_UPDATE_DRAFT)
    organization_id = _org(principal)
    parent = _version(session, organization_id, ingredient_id, version_id)
    _match(parent, expected_version)
    try:
        ensure_version_editable(parent)
    except PublishedVersionFrozenError as exc:
        raise ImmutableError("published_frozen") from exc
    if value_status not in NUTRIENT_STATUS:
        raise ValidationError("estado nutricional inválido")
    definition = session.get(NutrientDefinition, nutrient_id)
    if definition is None or definition.status != "active":
        raise ValidationError("nutriente inválido")
    parsed = None if value in (None, "") else as_decimal(value, "valor")
    loq = (
        None
        if limit_of_quantification in (None, "")
        else as_decimal(limit_of_quantification, "limite")
    )
    if value_status == "known_zero":
        parsed = Decimal("0")
    if value_status in {"below_loq", "not_detected", "unknown"}:
        parsed = None
    if value_status == "below_loq" and loq is None:
        raise ValidationError("limite de quantificação obrigatório")
    row = session.scalar(
        select(IngredientNutrient).where(
            IngredientNutrient.ingredient_version_id == parent.id,
            IngredientNutrient.nutrient_id == nutrient_id,
        )
    )
    if row is None:
        row = IngredientNutrient(
            organization_id=organization_id,
            ingredient_version_id=parent.id,
            nutrient_id=nutrient_id,
        )
        session.add(row)
    row.value = parsed
    row.value_status = value_status
    row.limit_of_quantification = loq
    row.loq_unit_id = loq_unit_id
    row.method_or_source = method_or_source.strip() if method_or_source else None
    _bump(parent)
    session.flush()
    return row


def upsert_allergen(
    session: Session,
    principal: Principal,
    *,
    ingredient_id: UUID,
    version_id: UUID,
    allergen_id: UUID,
    presence: str,
    data_source_id: UUID | None,
    evidence_note: str | None,
    expected_version: int | None,
) -> IngredientAllergen:
    require_permission(principal, PERMISSION_INGREDIENT_UPDATE_DRAFT)
    organization_id = _org(principal)
    parent = _version(session, organization_id, ingredient_id, version_id)
    _match(parent, expected_version)
    try:
        ensure_version_editable(parent)
    except PublishedVersionFrozenError as exc:
        raise ImmutableError("published_frozen") from exc
    if presence not in PRESENCE:
        raise ValidationError("presença inválida")
    allergen = session.get(Allergen, allergen_id)
    if allergen is None or allergen.status != "active":
        raise ValidationError("alergênico inválido")
    row = session.scalar(
        select(IngredientAllergen).where(
            IngredientAllergen.ingredient_version_id == parent.id,
            IngredientAllergen.allergen_id == allergen_id,
        )
    )
    if row is None:
        row = IngredientAllergen(
            organization_id=organization_id,
            ingredient_version_id=parent.id,
            allergen_id=allergen_id,
        )
        session.add(row)
    row.presence = presence
    row.data_source_id = data_source_id
    row.evidence_note = evidence_note.strip() if evidence_note else None
    _bump(parent)
    session.flush()
    return row


def create_supplier(
    session: Session,
    principal: Principal,
    *,
    code: str,
    display_name: str,
    idempotency_key: UUID,
) -> Supplier:
    require_permission(principal, PERMISSION_SUPPLIER_MANAGE)
    organization_id = _org(principal)
    payload = {"code": code, "display_name": display_name}
    replay = _replay(session, organization_id, idempotency_key, "supplier.create", payload)
    if replay is not None:
        return session.get(Supplier, replay.resource_id)
    row = Supplier(
        organization_id=organization_id,
        code=_text(code, "código", 80),
        display_name=_text(display_name, "nome"),
        status="active",
    )
    session.add(row)
    session.flush()
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="supplier.create",
        payload=payload,
        resource_type="supplier",
        resource_id=row.id,
        actor_user_id=principal.user_id,
    )
    return row


def update_supplier(
    session: Session,
    principal: Principal,
    *,
    supplier_id: UUID,
    display_name: str | None,
    status: str | None,
    expected_version: int | None,
) -> Supplier:
    require_permission(principal, PERMISSION_SUPPLIER_MANAGE)
    organization_id = _org(principal)
    row = session.scalar(
        select(Supplier).where(
            Supplier.id == supplier_id, Supplier.organization_id == organization_id
        )
    )
    if row is None:
        raise ValidationError("recurso_nao_encontrado")
    _match(row, expected_version)
    if display_name is not None:
        row.display_name = _text(display_name, "nome")
    if status is not None:
        if status not in {"active", "inactive"}:
            raise ValidationError("situação inválida")
        row.status = status
    _bump(row)
    session.flush()
    return row


def create_supplier_item(
    session: Session,
    principal: Principal,
    *,
    supplier_id: UUID,
    ingredient_id: UUID,
    supplier_sku: str,
    description: str | None,
    package_quantity: str,
    measurement_unit_id: UUID,
    idempotency_key: UUID,
) -> SupplierItem:
    require_permission(principal, PERMISSION_SUPPLIER_MANAGE)
    organization_id = _org(principal)
    payload = {
        "supplier_id": str(supplier_id),
        "ingredient_id": str(ingredient_id),
        "supplier_sku": supplier_sku,
    }
    replay = _replay(session, organization_id, idempotency_key, "supplier.item.create", payload)
    if replay is not None:
        return session.get(SupplierItem, replay.resource_id)
    supplier = session.scalar(
        select(Supplier).where(
            Supplier.id == supplier_id, Supplier.organization_id == organization_id
        )
    )
    if supplier is None:
        raise ValidationError("recurso_nao_encontrado")
    _ingredient(session, organization_id, ingredient_id)
    _mass_unit(session, measurement_unit_id)
    row = SupplierItem(
        organization_id=organization_id,
        supplier_id=supplier_id,
        ingredient_id=ingredient_id,
        supplier_sku=_text(supplier_sku, "código comercial", 80),
        description=description.strip() if description else None,
        package_quantity=require_positive(as_decimal(package_quantity, "embalagem"), "embalagem"),
        measurement_unit_id=measurement_unit_id,
        status="active",
    )
    session.add(row)
    session.flush()
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="supplier.item.create",
        payload=payload,
        resource_type="supplier_item",
        resource_id=row.id,
        actor_user_id=principal.user_id,
    )
    return row


def record_price(
    session: Session,
    principal: Principal,
    *,
    item_id: UUID,
    unit_price: str,
    currency: str,
    observed_at: datetime,
    source: str | None,
    idempotency_key: UUID,
) -> SupplierItemPrice:
    require_permission(principal, PERMISSION_SUPPLIER_PRICE_RECORD)
    organization_id = _org(principal)
    payload = {
        "item_id": str(item_id),
        "unit_price": unit_price,
        "currency": currency,
        "observed_at": observed_at.isoformat(),
    }
    replay = _replay(session, organization_id, idempotency_key, "supplier.price.record", payload)
    if replay is not None:
        return session.get(SupplierItemPrice, replay.resource_id)
    item = session.scalar(
        select(SupplierItem).where(
            SupplierItem.id == item_id,
            SupplierItem.organization_id == organization_id,
        )
    )
    if item is None:
        raise ValidationError("recurso_nao_encontrado")
    if currency not in CURRENCIES:
        raise ValidationError("moeda não suportada")
    price = as_decimal(unit_price, "valor")
    if price < 0:
        raise ValidationError("valor de compra inválido")
    row = SupplierItemPrice(
        supplier_item_id=item.id,
        unit_price=price,
        currency=currency,
        observed_at=observed_at,
        source=source.strip() if source else None,
    )
    session.add(row)
    session.flush()
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="supplier.price.record",
        payload=payload,
        resource_type="supplier_item_price",
        resource_id=row.id,
        actor_user_id=principal.user_id,
    )
    return row


def require_read(principal: Principal) -> None:
    require_permission(principal, PERMISSION_INGREDIENT_READ)


def require_supplier_read(principal: Principal) -> None:
    require_permission(principal, PERMISSION_SUPPLIER_READ)
