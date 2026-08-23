from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.calculation_engine.nutrition import (
    calculate_nutrition,
    persist_nutrition_calculation,
)
from app.modules.calculation_engine.scale import (
    calculate_final_units,
    calculate_total_dough_mass,
    persist_scale_calculation,
)
from app.modules.formula_lab.models import (
    Approval,
    Formulation,
    FormulationCommand,
    FormulationItem,
    FormulationRecipeReference,
    FormulationVersion,
    ProcessStep,
    RecipeReference,
    TechnicalProduct,
    Trial,
    TrialMeasurement,
)
from app.modules.formula_lab.version_references import (
    attach_identity_reference_to_current_draft,
    copy_version_references,
)
from app.modules.formula_lab.rules import (
    FlourBasisEmptyError,
    IngredientVersionNotPublishedError,
    PublishedFormulationFrozenError,
    PublishRequiresApprovalError,
    ensure_formulation_version_editable,
    publish_formulation_version,
    retire_published_version,
)
from app.modules.identity_organization.authorization import (
    PERMISSION_RECIPE_APPROVE,
    PERMISSION_RECIPE_CREATE,
    PERMISSION_RECIPE_PUBLISH,
    PERMISSION_RECIPE_READ,
    PERMISSION_RECIPE_REFERENCE_MANAGE,
    PERMISSION_RECIPE_RETIRE,
    PERMISSION_RECIPE_REVIEW,
    PERMISSION_RECIPE_SCALE,
    PERMISSION_RECIPE_TECHNICAL_SHEET_READ,
    PERMISSION_RECIPE_TRIAL_MANAGE,
    PERMISSION_RECIPE_UPDATE_DRAFT,
    PERMISSION_RECIPE_VERSION_CREATE,
    Principal,
    require_permission,
)
from app.modules.ingredient_catalog.models import IngredientVersion, MeasurementUnit
from app.modules.production_planning.errors import (
    ConcurrencyError,
    IdempotencyConflictError,
    ImmutableError,
    InvalidStateError,
    ValidationError,
)
from app.modules.production_planning.support import as_decimal, digest, require_positive

ITEM_ROLES = {"ingredient", "preparation", "additive"}
REFERENCE_ROLES = {"inspiration", "source", "comparison"}
SOURCE_TYPES = {"book", "url", "internal", "oral", "other"}
TRIAL_STATUSES = {"planned", "in_progress", "completed", "cancelled"}
MEASUREMENT_TYPES = {
    "dough_mass",
    "units_produced",
    "final_unit_weight",
    "actual_loss",
    "duration",
    "temperature",
}
APPROVAL_DECISIONS = {"submitted", "approved", "rejected", "revoked"}
RECIPE_STATUSES = {"development", "active", "retired"}


def require_read(principal: Principal) -> None:
    require_permission(principal, PERMISSION_RECIPE_READ)


def require_sheet_read(principal: Principal) -> None:
    require_permission(principal, PERMISSION_RECIPE_TECHNICAL_SHEET_READ)


def _org(principal: Principal) -> UUID:
    if principal.selected is None:
        raise ValidationError("organizacao_nao_selecionada")
    return principal.selected.organization_id


def _bump(row) -> None:
    row.row_version = int(row.row_version) + 1
    if hasattr(row, "updated_at"):
        row.updated_at = datetime.now(UTC)


def _match(row, expected: int | None) -> None:
    if expected is None:
        return
    if int(row.row_version) != int(expected):
        raise ConcurrencyError("versao_conflito")


def _replay(
    session: Session, organization_id: UUID, idempotency_key: UUID, command: str, payload: dict
):
    row = session.scalar(
        select(FormulationCommand).where(
            FormulationCommand.organization_id == organization_id,
            FormulationCommand.idempotency_key == idempotency_key,
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
) -> FormulationCommand:
    row = FormulationCommand(
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


def _text(value: str, label: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValidationError(f"{label} obrigatório")
    return cleaned


def _mass_unit(session: Session, unit_id: UUID) -> MeasurementUnit:
    unit = session.get(MeasurementUnit, unit_id)
    if unit is None or unit.dimension != "mass":
        raise ValidationError("unidade deve ser de massa")
    return unit


def _published_ingredient(
    session: Session, organization_id: UUID, ingredient_version_id: UUID
) -> IngredientVersion:
    row = session.get(IngredientVersion, ingredient_version_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError("recurso_nao_encontrado")
    if row.status != "published":
        raise ValidationError("item deve apontar versão publicada de ingrediente")
    return row


def _version(session: Session, organization_id: UUID, version_id: UUID) -> FormulationVersion:
    row = session.get(FormulationVersion, version_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError("recurso_nao_encontrado")
    return row


def _wrap_domain(exc: Exception) -> None:
    if isinstance(exc, PublishedFormulationFrozenError):
        raise ImmutableError("published_frozen") from exc
    if isinstance(exc, PublishRequiresApprovalError):
        raise InvalidStateError("aprovacao_obrigatoria") from exc
    if isinstance(exc, IngredientVersionNotPublishedError):
        raise ValidationError("item deve apontar versão publicada de ingrediente") from exc
    if isinstance(exc, FlourBasisEmptyError):
        raise ValidationError("base de farinha deve ser maior que zero") from exc
    raise exc


def create_recipe(
    session: Session,
    principal: Principal,
    *,
    product_code: str,
    product_name: str,
    recipe_code: str,
    recipe_name: str,
    idempotency_key: UUID,
) -> Formulation:
    require_permission(principal, PERMISSION_RECIPE_CREATE)
    organization_id = _org(principal)
    payload = {
        "product_code": product_code,
        "recipe_code": recipe_code,
        "recipe_name": recipe_name,
    }
    replay = _replay(session, organization_id, idempotency_key, "formulation.create", payload)
    if replay is not None:
        return session.get(Formulation, replay.resource_id)
    product = TechnicalProduct(
        organization_id=organization_id,
        code=_text(product_code, "código do produto"),
        display_name=_text(product_name, "nome do produto"),
        status="development",
    )
    session.add(product)
    session.flush()
    recipe = Formulation(
        organization_id=organization_id,
        technical_product_id=product.id,
        code=_text(recipe_code, "código da receita"),
        display_name=_text(recipe_name, "nome da receita"),
        status="development",
    )
    session.add(recipe)
    session.flush()
    session.add(
        FormulationVersion(
            organization_id=organization_id,
            formulation_id=recipe.id,
            version_number=1,
            status="draft",
            created_by_user_id=principal.user_id,
        )
    )
    try:
        session.flush()
    except IntegrityError as exc:
        raise ValidationError("código já existe nesta organização") from exc
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="formulation.create",
        payload=payload,
        resource_type="formulation",
        resource_id=recipe.id,
        actor_user_id=principal.user_id,
    )
    return recipe


def update_identity(
    session: Session,
    principal: Principal,
    formulation_id: UUID,
    *,
    display_name: str | None,
    status: str | None,
    expected_version: int | None,
) -> Formulation:
    require_permission(principal, PERMISSION_RECIPE_UPDATE_DRAFT)
    organization_id = _org(principal)
    row = session.scalar(
        select(Formulation).where(
            Formulation.id == formulation_id, Formulation.organization_id == organization_id
        )
    )
    if row is None:
        raise ValidationError("recurso_nao_encontrado")
    _match(row, expected_version)
    if display_name is not None:
        row.display_name = _text(display_name, "nome")
    if status is not None:
        if status not in RECIPE_STATUSES:
            raise ValidationError("situação inválida")
        row.status = status
    _bump(row)
    session.flush()
    return row


def update_draft(
    session: Session,
    principal: Principal,
    version_id: UUID,
    *,
    notes: str | None,
    yield_units: int | None,
    target_unit_weight_g: str | None,
    expected_bake_loss_rate: str | None,
    expected_version: int | None,
) -> FormulationVersion:
    require_permission(principal, PERMISSION_RECIPE_UPDATE_DRAFT)
    version = _version(session, _org(principal), version_id)
    _match(version, expected_version)
    try:
        ensure_formulation_version_editable(version)
    except PublishedFormulationFrozenError as exc:
        _wrap_domain(exc)
    if notes is not None:
        version.notes = notes.strip() or None
    if yield_units is not None:
        if yield_units < 1:
            raise ValidationError("rendimento deve ser positivo")
        version.yield_units = yield_units
    if target_unit_weight_g is not None:
        version.target_unit_weight_g = require_positive(
            as_decimal(target_unit_weight_g, "peso"), "peso"
        )
    if expected_bake_loss_rate is not None:
        rate = as_decimal(expected_bake_loss_rate, "perda")
        if rate < 0 or rate >= 1:
            raise ValidationError("perda deve estar entre 0 e menor que 1")
        version.expected_bake_loss_rate = rate
    _bump(version)
    session.flush()
    return version


def create_version(
    session: Session,
    principal: Principal,
    formulation_id: UUID,
    *,
    source_version_id: UUID | None,
    idempotency_key: UUID,
) -> FormulationVersion:
    require_permission(principal, PERMISSION_RECIPE_VERSION_CREATE)
    organization_id = _org(principal)
    recipe = session.scalar(
        select(Formulation).where(
            Formulation.id == formulation_id, Formulation.organization_id == organization_id
        )
    )
    if recipe is None:
        raise ValidationError("recurso_nao_encontrado")
    payload = {
        "formulation_id": str(formulation_id),
        "source_version_id": str(source_version_id) if source_version_id else None,
    }
    replay = _replay(
        session, organization_id, idempotency_key, "formulation.version.create", payload
    )
    if replay is not None:
        return _version(session, organization_id, replay.resource_id)
    next_number = (
        session.scalar(
            select(func.coalesce(func.max(FormulationVersion.version_number), 0)).where(
                FormulationVersion.formulation_id == recipe.id
            )
        )
        or 0
    ) + 1
    source = None
    if source_version_id:
        source = _version(session, organization_id, source_version_id)
        if source.formulation_id != recipe.id:
            raise ValidationError("recurso_nao_encontrado")
    row = FormulationVersion(
        organization_id=organization_id,
        formulation_id=recipe.id,
        version_number=next_number,
        status="draft",
        yield_units=None if source is None else source.yield_units,
        target_unit_weight_g=None if source is None else source.target_unit_weight_g,
        expected_bake_loss_rate=None if source is None else source.expected_bake_loss_rate,
        notes=None if source is None else source.notes,
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    if source is not None:
        for item in session.scalars(
            select(FormulationItem)
            .where(FormulationItem.formulation_version_id == source.id)
            .order_by(FormulationItem.sequence)
        ):
            session.add(
                FormulationItem(
                    organization_id=organization_id,
                    formulation_version_id=row.id,
                    ingredient_version_id=item.ingredient_version_id,
                    sequence=item.sequence,
                    net_quantity=item.net_quantity,
                    measurement_unit_id=item.measurement_unit_id,
                    correction_factor=item.correction_factor,
                    is_flour_basis=item.is_flour_basis,
                    role=item.role,
                    notes=item.notes,
                )
            )
        for step in session.scalars(
            select(ProcessStep)
            .where(ProcessStep.formulation_version_id == source.id)
            .order_by(ProcessStep.sequence)
        ):
            session.add(
                ProcessStep(
                    organization_id=organization_id,
                    formulation_version_id=row.id,
                    sequence=step.sequence,
                    title=step.title,
                    instructions=step.instructions,
                    duration_seconds=step.duration_seconds,
                    temperature_celsius=step.temperature_celsius,
                )
            )
        copy_version_references(session, source, row)
        session.flush()
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="formulation.version.create",
        payload=payload,
        resource_type="formulation_version",
        resource_id=row.id,
        actor_user_id=principal.user_id,
    )
    return row


def upsert_item(
    session: Session,
    principal: Principal,
    version_id: UUID,
    *,
    ingredient_version_id: UUID,
    sequence: int,
    net_quantity: str,
    measurement_unit_id: UUID,
    correction_factor: str,
    is_flour_basis: bool,
    role: str,
    notes: str | None,
    expected_version: int | None,
) -> FormulationItem:
    require_permission(principal, PERMISSION_RECIPE_UPDATE_DRAFT)
    organization_id = _org(principal)
    version = _version(session, organization_id, version_id)
    _match(version, expected_version)
    try:
        ensure_formulation_version_editable(version)
    except PublishedFormulationFrozenError as exc:
        _wrap_domain(exc)
    if role not in ITEM_ROLES:
        raise ValidationError("papel de item inválido")
    if sequence < 1:
        raise ValidationError("sequência deve ser positiva")
    _published_ingredient(session, organization_id, ingredient_version_id)
    _mass_unit(session, measurement_unit_id)
    net = require_positive(as_decimal(net_quantity, "quantidade"), "quantidade")
    factor = as_decimal(correction_factor, "fator")
    if factor <= 0:
        raise ValidationError("fator de correção deve ser positivo")
    row = session.scalar(
        select(FormulationItem).where(
            FormulationItem.formulation_version_id == version.id,
            FormulationItem.sequence == sequence,
        )
    )
    if row is None:
        row = FormulationItem(
            organization_id=organization_id,
            formulation_version_id=version.id,
            sequence=sequence,
        )
        session.add(row)
    row.ingredient_version_id = ingredient_version_id
    row.net_quantity = net
    row.measurement_unit_id = measurement_unit_id
    row.correction_factor = factor
    row.is_flour_basis = is_flour_basis
    row.role = role
    row.notes = None if notes is None else notes.strip() or None
    _bump(version)
    session.flush()
    return row


def remove_item(
    session: Session,
    principal: Principal,
    version_id: UUID,
    item_id: UUID,
    expected_version: int | None,
) -> None:
    require_permission(principal, PERMISSION_RECIPE_UPDATE_DRAFT)
    organization_id = _org(principal)
    version = _version(session, organization_id, version_id)
    _match(version, expected_version)
    try:
        ensure_formulation_version_editable(version)
    except PublishedFormulationFrozenError as exc:
        _wrap_domain(exc)
    row = session.get(FormulationItem, item_id)
    if row is None or row.formulation_version_id != version.id:
        raise ValidationError("recurso_nao_encontrado")
    session.delete(row)
    _bump(version)
    session.flush()


def upsert_step(
    session: Session,
    principal: Principal,
    version_id: UUID,
    *,
    sequence: int,
    title: str,
    instructions: str,
    duration_seconds: int | None,
    temperature_celsius: str | None,
    expected_version: int | None,
) -> ProcessStep:
    require_permission(principal, PERMISSION_RECIPE_UPDATE_DRAFT)
    organization_id = _org(principal)
    version = _version(session, organization_id, version_id)
    _match(version, expected_version)
    try:
        ensure_formulation_version_editable(version)
    except PublishedFormulationFrozenError as exc:
        _wrap_domain(exc)
    if sequence < 1:
        raise ValidationError("sequência deve ser positiva")
    row = session.scalar(
        select(ProcessStep).where(
            ProcessStep.formulation_version_id == version.id,
            ProcessStep.sequence == sequence,
        )
    )
    if row is None:
        row = ProcessStep(
            organization_id=organization_id,
            formulation_version_id=version.id,
            sequence=sequence,
        )
        session.add(row)
    row.title = _text(title, "título")
    row.instructions = _text(instructions, "instruções")
    row.duration_seconds = duration_seconds
    row.temperature_celsius = (
        None if temperature_celsius is None else as_decimal(temperature_celsius, "temperatura")
    )
    _bump(version)
    session.flush()
    return row


def remove_step(
    session: Session,
    principal: Principal,
    version_id: UUID,
    step_id: UUID,
    expected_version: int | None,
) -> None:
    require_permission(principal, PERMISSION_RECIPE_UPDATE_DRAFT)
    organization_id = _org(principal)
    version = _version(session, organization_id, version_id)
    _match(version, expected_version)
    try:
        ensure_formulation_version_editable(version)
    except PublishedFormulationFrozenError as exc:
        _wrap_domain(exc)
    row = session.get(ProcessStep, step_id)
    if row is None or row.formulation_version_id != version.id:
        raise ValidationError("recurso_nao_encontrado")
    session.delete(row)
    _bump(version)
    session.flush()


def record_approval(
    session: Session,
    principal: Principal,
    version_id: UUID,
    *,
    decision: str,
    notes: str | None,
    idempotency_key: UUID,
) -> Approval:
    if decision == "submitted":
        require_permission(principal, PERMISSION_RECIPE_REVIEW)
    else:
        require_permission(principal, PERMISSION_RECIPE_APPROVE)
    organization_id = _org(principal)
    if decision not in APPROVAL_DECISIONS:
        raise ValidationError("decisão inválida")
    payload = {"version_id": str(version_id), "decision": decision}
    replay = _replay(session, organization_id, idempotency_key, "formulation.approve", payload)
    if replay is not None:
        return session.get(Approval, replay.resource_id)
    version = _version(session, organization_id, version_id)
    row = Approval(
        organization_id=organization_id,
        formulation_version_id=version.id,
        actor_user_id=principal.user_id,
        decision=decision,
        notes=None if notes is None else notes.strip() or None,
    )
    session.add(row)
    session.flush()
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="formulation.approve",
        payload=payload,
        resource_type="approval",
        resource_id=row.id,
        actor_user_id=principal.user_id,
    )
    return row


def publish_version(
    session: Session,
    principal: Principal,
    version_id: UUID,
    *,
    expected_version: int | None,
    idempotency_key: UUID,
) -> FormulationVersion:
    require_permission(principal, PERMISSION_RECIPE_PUBLISH)
    organization_id = _org(principal)
    payload = {"version_id": str(version_id)}
    replay = _replay(session, organization_id, idempotency_key, "formulation.publish", payload)
    if replay is not None:
        return _version(session, organization_id, replay.resource_id)
    version = _version(session, organization_id, version_id)
    _match(version, expected_version)
    try:
        publish_formulation_version(session, version)
    except Exception as exc:
        _wrap_domain(exc)
    _bump(version)
    session.flush()
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="formulation.publish",
        payload=payload,
        resource_type="formulation_version",
        resource_id=version.id,
        actor_user_id=principal.user_id,
    )
    return version


def retire_version(
    session: Session,
    principal: Principal,
    version_id: UUID,
    *,
    expected_version: int | None,
    idempotency_key: UUID,
) -> FormulationVersion:
    require_permission(principal, PERMISSION_RECIPE_RETIRE)
    organization_id = _org(principal)
    payload = {"version_id": str(version_id)}
    replay = _replay(session, organization_id, idempotency_key, "formulation.retire", payload)
    if replay is not None:
        return _version(session, organization_id, replay.resource_id)
    version = _version(session, organization_id, version_id)
    _match(version, expected_version)
    try:
        retire_published_version(version)
    except ValueError as exc:
        raise InvalidStateError("transicao_invalida") from exc
    _bump(version)
    session.flush()
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="formulation.retire",
        payload=payload,
        resource_type="formulation_version",
        resource_id=version.id,
        actor_user_id=principal.user_id,
    )
    return version


def record_scale(
    session: Session,
    principal: Principal,
    version_id: UUID,
    *,
    mode: str,
    target_total_dough_mass: str | None,
    unit_count: int | None,
    final_unit_weight_g: str | None,
    bake_loss_rate: str | None,
    idempotency_key: UUID,
):
    require_permission(principal, PERMISSION_RECIPE_SCALE)
    organization_id = _org(principal)
    payload = {"version_id": str(version_id), "mode": mode}
    replay = _replay(session, organization_id, idempotency_key, "formulation.scale", payload)
    if replay is not None:
        from app.modules.formula_lab.models import ScaleCalculation

        return session.get(ScaleCalculation, replay.resource_id)
    version = _version(session, organization_id, version_id)
    items = list(
        session.scalars(
            select(FormulationItem)
            .where(FormulationItem.formulation_version_id == version.id)
            .order_by(FormulationItem.sequence)
        )
    )
    try:
        if mode == "total_dough_mass":
            result = calculate_total_dough_mass(
                items, as_decimal(target_total_dough_mass or "0", "massa")
            )
        elif mode == "final_units":
            result = calculate_final_units(
                items,
                int(unit_count or 0),
                as_decimal(final_unit_weight_g or "0", "peso"),
                as_decimal(bake_loss_rate or "0", "perda"),
            )
        else:
            raise ValidationError("modo de escala inválido")
        row = persist_scale_calculation(session, version, result, principal.user_id)
    except Exception as exc:
        raise ValidationError("cálculo de escala inválido") from exc
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="formulation.scale",
        payload=payload,
        resource_type="scale_calculation",
        resource_id=row.id,
        actor_user_id=principal.user_id,
    )
    return row


def simulate_scale(
    session: Session,
    principal: Principal,
    version_id: UUID,
    *,
    mode: str,
    target_total_dough_mass: str | None,
    unit_count: int | None,
    final_unit_weight_g: str | None,
    bake_loss_rate: str | None,
):
    require_permission(principal, PERMISSION_RECIPE_SCALE)
    version = _version(session, _org(principal), version_id)
    items = list(
        session.scalars(
            select(FormulationItem)
            .where(FormulationItem.formulation_version_id == version.id)
            .order_by(FormulationItem.sequence)
        )
    )
    try:
        if mode == "total_dough_mass":
            return calculate_total_dough_mass(
                items, as_decimal(target_total_dough_mass or "0", "massa")
            )
        if mode == "final_units":
            return calculate_final_units(
                items,
                int(unit_count or 0),
                as_decimal(final_unit_weight_g or "0", "peso"),
                as_decimal(bake_loss_rate or "0", "perda"),
            )
        raise ValidationError("modo de escala inválido")
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError("cálculo de escala inválido") from exc


def record_nutrition(
    session: Session,
    principal: Principal,
    version_id: UUID,
    *,
    idempotency_key: UUID,
):
    require_permission(principal, PERMISSION_RECIPE_SCALE)
    organization_id = _org(principal)
    payload = {"version_id": str(version_id), "kind": "nutrition"}
    replay = _replay(session, organization_id, idempotency_key, "formulation.nutrition", payload)
    if replay is not None:
        from app.modules.nutrition_calculation.models import NutritionCalculation

        return session.get(NutritionCalculation, replay.resource_id)
    version = _version(session, organization_id, version_id)
    try:
        result = calculate_nutrition(session, version)
        row = persist_nutrition_calculation(session, version, result, principal.user_id)
    except Exception as exc:
        raise ValidationError("cálculo nutricional técnico inválido") from exc
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="formulation.nutrition",
        payload=payload,
        resource_type="nutrition_calculation",
        resource_id=row.id,
        actor_user_id=principal.user_id,
    )
    return row


def create_reference(
    session: Session,
    principal: Principal,
    *,
    title: str,
    source_type: str,
    source_url: str | None,
    author: str | None,
    notes: str | None,
    idempotency_key: UUID,
) -> RecipeReference:
    require_permission(principal, PERMISSION_RECIPE_REFERENCE_MANAGE)
    organization_id = _org(principal)
    if source_type not in SOURCE_TYPES:
        raise ValidationError("tipo de fonte inválido")
    payload = {"title": title, "source_type": source_type}
    replay = _replay(session, organization_id, idempotency_key, "recipe_reference.create", payload)
    if replay is not None:
        return session.get(RecipeReference, replay.resource_id)
    row = RecipeReference(
        organization_id=organization_id,
        title=_text(title, "título"),
        source_type=source_type,
        source_url=None if source_url is None else source_url.strip() or None,
        author=None if author is None else author.strip() or None,
        notes=None if notes is None else notes.strip() or None,
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="recipe_reference.create",
        payload=payload,
        resource_type="recipe_reference",
        resource_id=row.id,
        actor_user_id=principal.user_id,
    )
    return row


def link_reference(
    session: Session,
    principal: Principal,
    formulation_id: UUID,
    recipe_reference_id: UUID,
    role: str,
    expected_version: int | None,
) -> FormulationRecipeReference:
    require_permission(principal, PERMISSION_RECIPE_REFERENCE_MANAGE)
    organization_id = _org(principal)
    if role not in REFERENCE_ROLES:
        raise ValidationError("papel de referência inválido")
    recipe = session.scalar(
        select(Formulation).where(
            Formulation.id == formulation_id, Formulation.organization_id == organization_id
        )
    )
    ref = session.scalar(
        select(RecipeReference).where(
            RecipeReference.id == recipe_reference_id,
            RecipeReference.organization_id == organization_id,
        )
    )
    if recipe is None or ref is None:
        raise ValidationError("recurso_nao_encontrado")
    _match(recipe, expected_version)
    row = FormulationRecipeReference(
        organization_id=organization_id,
        formulation_id=recipe.id,
        recipe_reference_id=ref.id,
        role=role,
    )
    session.add(row)
    _bump(recipe)
    try:
        session.flush()
    except IntegrityError as exc:
        raise ValidationError("referência já associada") from exc
    attach_identity_reference_to_current_draft(session, recipe.id, ref, role)
    return row


def unlink_reference(
    session: Session,
    principal: Principal,
    formulation_id: UUID,
    link_id: UUID,
    expected_version: int | None,
) -> None:
    require_permission(principal, PERMISSION_RECIPE_REFERENCE_MANAGE)
    organization_id = _org(principal)
    recipe = session.scalar(
        select(Formulation).where(
            Formulation.id == formulation_id, Formulation.organization_id == organization_id
        )
    )
    if recipe is None:
        raise ValidationError("recurso_nao_encontrado")
    _match(recipe, expected_version)
    row = session.get(FormulationRecipeReference, link_id)
    if row is None or row.formulation_id != recipe.id:
        raise ValidationError("recurso_nao_encontrado")
    session.delete(row)
    _bump(recipe)
    session.flush()


def record_trial(
    session: Session,
    principal: Principal,
    version_id: UUID,
    *,
    code: str,
    notes: str | None,
    idempotency_key: UUID,
) -> Trial:
    require_permission(principal, PERMISSION_RECIPE_TRIAL_MANAGE)
    organization_id = _org(principal)
    payload = {"version_id": str(version_id), "code": code}
    replay = _replay(session, organization_id, idempotency_key, "formulation.trial.create", payload)
    if replay is not None:
        return session.get(Trial, replay.resource_id)
    version = _version(session, organization_id, version_id)
    row = Trial(
        organization_id=organization_id,
        formulation_version_id=version.id,
        code=_text(code, "código"),
        status="planned",
        notes=None if notes is None else notes.strip() or None,
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        raise ValidationError("código já existe nesta organização") from exc
    _remember(
        session,
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        command="formulation.trial.create",
        payload=payload,
        resource_type="trial",
        resource_id=row.id,
        actor_user_id=principal.user_id,
    )
    return row


def record_trial_measurement(
    session: Session,
    principal: Principal,
    trial_id: UUID,
    *,
    measurement_type: str,
    value: str,
    measurement_unit_id: UUID | None,
    notes: str | None,
) -> TrialMeasurement:
    require_permission(principal, PERMISSION_RECIPE_TRIAL_MANAGE)
    organization_id = _org(principal)
    trial = session.scalar(
        select(Trial).where(Trial.id == trial_id, Trial.organization_id == organization_id)
    )
    if trial is None:
        raise ValidationError("recurso_nao_encontrado")
    if trial.status not in {"planned", "in_progress"}:
        raise InvalidStateError("transicao_invalida")
    if measurement_type not in MEASUREMENT_TYPES:
        raise ValidationError("tipo de medição inválido")
    if trial.status == "planned":
        trial.status = "in_progress"
    row = TrialMeasurement(
        organization_id=organization_id,
        trial_id=trial.id,
        measurement_type=_text(measurement_type, "tipo"),
        value=as_decimal(value, "medida"),
        measurement_unit_id=measurement_unit_id,
        notes=None if notes is None else notes.strip() or None,
    )
    session.add(row)
    session.flush()
    return row


def update_trial_status(
    session: Session,
    principal: Principal,
    trial_id: UUID,
    *,
    status: str,
    notes: str | None,
) -> Trial:
    require_permission(principal, PERMISSION_RECIPE_TRIAL_MANAGE)
    organization_id = _org(principal)
    if status not in TRIAL_STATUSES:
        raise ValidationError("situação de ensaio inválida")
    trial = session.scalar(
        select(Trial).where(Trial.id == trial_id, Trial.organization_id == organization_id)
    )
    if trial is None:
        raise ValidationError("recurso_nao_encontrado")
    if trial.status in {"completed", "cancelled"}:
        raise InvalidStateError("transicao_invalida")
    allowed = {
        "planned": {"in_progress", "cancelled"},
        "in_progress": {"completed", "cancelled"},
    }
    if status not in allowed.get(trial.status, set()):
        raise InvalidStateError("transicao_invalida")
    trial.status = status
    if notes is not None:
        trial.notes = notes.strip() or None
    if status == "completed":
        trial.executed_on = datetime.now(UTC).date()
    session.flush()
    return trial
