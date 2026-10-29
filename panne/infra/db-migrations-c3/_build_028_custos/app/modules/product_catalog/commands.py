from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.formula_lab.models import Formulation, FormulationVersion, ProductFamily, TechnicalProduct
from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCT_ACTIVATE,
    PERMISSION_PRODUCT_CREATE,
    PERMISSION_PRODUCT_FAMILY_MANAGE,
    PERMISSION_PRODUCT_READ,
    PERMISSION_PRODUCT_UPDATE,
    Principal,
    require_permission,
)
from app.modules.ingredient_catalog.models import MeasurementUnit
from app.modules.product_catalog.constants import (
    FAMILY_STATUSES,
    PRODUCT_PURPOSES,
    PRODUCT_STATUSES,
    PRODUCT_SUPPLY_MODES,
    PURPOSE_FINAL,
    STATUS_ACTIVE,
    STATUS_INACTIVE,
    SUPPLY_COMBO,
    SUPPLY_MIXED,
    SUPPLY_MODES_OPERATIONAL,
    SUPPLY_PRODUCED,
    SUPPLY_PURCHASED,
)
from app.modules.production_planning.errors import CycleError, ValidationError
from app.modules.production_planning.models import ProductionOrder


def _org(principal: Principal) -> UUID:
    if principal.selected is None:
        raise ValidationError("organizacao_nao_selecionada")
    return principal.selected.organization_id


def require_product_read(principal: Principal) -> None:
    require_permission(principal, PERMISSION_PRODUCT_READ)


def _require_unit(session: Session, unit_id: UUID | None, label: str) -> UUID | None:
    if unit_id is None:
        return None
    row = session.get(MeasurementUnit, unit_id)
    if row is None:
        raise ValidationError(f"{label} inválida")
    return unit_id


def _require_family(session: Session, organization_id: UUID, family_id: UUID | None) -> UUID | None:
    if family_id is None:
        return None
    row = session.get(ProductFamily, family_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError("família inválida")
    return family_id


def _normalize_text(value: str | None, *, required: bool, label: str) -> str | None:
    if value is None:
        if required:
            raise ValidationError(f"{label} obrigatório")
        return None
    cleaned = value.strip()
    if required and not cleaned:
        raise ValidationError(f"{label} obrigatório")
    return cleaned or None


def has_published_recipe(session: Session, product_id: UUID, organization_id: UUID) -> bool:
    stmt = (
        select(FormulationVersion.id)
        .join(Formulation, Formulation.id == FormulationVersion.formulation_id)
        .where(
            Formulation.technical_product_id == product_id,
            Formulation.organization_id == organization_id,
            FormulationVersion.organization_id == organization_id,
            FormulationVersion.status == "published",
        )
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none() is not None


def assert_product_allows_production(
    session: Session,
    *,
    organization_id: UUID,
    technical_product_id: UUID,
) -> TechnicalProduct:
    product = session.get(TechnicalProduct, technical_product_id)
    if product is None or product.organization_id != organization_id:
        raise ValidationError("Produto não encontrado nesta organização.")
    if product.status != STATUS_ACTIVE:
        raise ValidationError("Produto inativo não pode gerar ordem de produção.")
    if product.supply_mode == SUPPLY_PURCHASED:
        raise ValidationError("Produto comprado não gera ordem de produção.")
    if product.supply_mode in {SUPPLY_MIXED, SUPPLY_COMBO}:
        raise ValidationError(
            "Esta modalidade de abastecimento ainda está em preparação. "
            "Use produto produzido ou comprado nesta fase."
        )
    if product.supply_mode == SUPPLY_PRODUCED and not has_published_recipe(
        session, product.id, organization_id
    ):
        raise ValidationError(
            "Sem receita vigente. "
            "Vincule e publique uma receita antes de planejar ou criar a ordem."
        )
    return product


def create_product(
    session: Session,
    principal: Principal,
    *,
    code: str,
    display_name: str,
    description: str | None = None,
    purpose: str = PURPOSE_FINAL,
    supply_mode: str = SUPPLY_PRODUCED,
    family_id: UUID | None = None,
    stock_unit_id: UUID | None = None,
    sale_unit_id: UUID | None = None,
    net_content: Decimal | str | None = None,
    net_content_unit_id: UUID | None = None,
    default_shelf_life_days: int | None = None,
    packaging_description: str | None = None,
    status: str = STATUS_ACTIVE,
) -> TechnicalProduct:
    require_permission(principal, PERMISSION_PRODUCT_CREATE)
    organization_id = _org(principal)
    code_n = _normalize_text(code, required=True, label="código")
    name_n = _normalize_text(display_name, required=True, label="nome")
    if purpose not in PRODUCT_PURPOSES:
        raise ValidationError("finalidade inválida")
    if supply_mode not in PRODUCT_SUPPLY_MODES:
        raise ValidationError("modalidade inválida")
    if status not in PRODUCT_STATUSES:
        raise ValidationError("situação inválida")
    if supply_mode not in SUPPLY_MODES_OPERATIONAL:
        # Permitir gravar o valor no contrato, mas a UI marca como em preparação;
        # criação via API ainda aceita o enum para testes de contrato — operação é bloqueada.
        pass
    content = None
    if net_content is not None and str(net_content).strip() != "":
        content = Decimal(str(net_content))
        if content <= 0:
            raise ValidationError("conteúdo líquido deve ser positivo")
    if default_shelf_life_days is not None and default_shelf_life_days < 0:
        raise ValidationError("validade padrão inválida")
    row = TechnicalProduct(
        organization_id=organization_id,
        code=code_n,
        display_name=name_n,
        description=_normalize_text(description, required=False, label="descrição"),
        purpose=purpose,
        supply_mode=supply_mode,
        status=status,
        family_id=_require_family(session, organization_id, family_id),
        stock_unit_id=_require_unit(session, stock_unit_id, "unidade de estoque"),
        sale_unit_id=_require_unit(session, sale_unit_id, "unidade de venda"),
        net_content=content,
        net_content_unit_id=_require_unit(session, net_content_unit_id, "unidade do conteúdo"),
        default_shelf_life_days=default_shelf_life_days,
        packaging_description=_normalize_text(
            packaging_description, required=False, label="embalagem"
        ),
        created_by_user_id=principal.user_id,
        updated_by_user_id=principal.user_id,
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        raise ValidationError("código já existe nesta organização") from exc
    return row


def update_product(
    session: Session,
    principal: Principal,
    *,
    product_id: UUID,
    expected_row_version: int | None,
    **fields,
) -> TechnicalProduct:
    require_permission(principal, PERMISSION_PRODUCT_UPDATE)
    organization_id = _org(principal)
    row = session.get(TechnicalProduct, product_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError("recurso_nao_encontrado")
    if expected_row_version is not None and row.row_version != expected_row_version:
        raise ValidationError("conflito_de_versao")
    if "code" in fields and fields["code"] is not None:
        row.code = _normalize_text(fields["code"], required=True, label="código")  # type: ignore[assignment]
    if "display_name" in fields and fields["display_name"] is not None:
        row.display_name = _normalize_text(fields["display_name"], required=True, label="nome")  # type: ignore[assignment]
    if "description" in fields:
        row.description = _normalize_text(fields["description"], required=False, label="descrição")
    if "purpose" in fields and fields["purpose"] is not None:
        if fields["purpose"] not in PRODUCT_PURPOSES:
            raise ValidationError("finalidade inválida")
        row.purpose = fields["purpose"]
    if "supply_mode" in fields and fields["supply_mode"] is not None:
        if fields["supply_mode"] not in PRODUCT_SUPPLY_MODES:
            raise ValidationError("modalidade inválida")
        row.supply_mode = fields["supply_mode"]
    if "family_id" in fields:
        row.family_id = _require_family(session, organization_id, fields["family_id"])
    if "stock_unit_id" in fields:
        row.stock_unit_id = _require_unit(session, fields["stock_unit_id"], "unidade de estoque")
    if "sale_unit_id" in fields:
        row.sale_unit_id = _require_unit(session, fields["sale_unit_id"], "unidade de venda")
    if "net_content" in fields:
        raw = fields["net_content"]
        if raw is None or str(raw).strip() == "":
            row.net_content = None
        else:
            content = Decimal(str(raw))
            if content <= 0:
                raise ValidationError("conteúdo líquido deve ser positivo")
            row.net_content = content
    if "net_content_unit_id" in fields:
        row.net_content_unit_id = _require_unit(
            session, fields["net_content_unit_id"], "unidade do conteúdo"
        )
    if "default_shelf_life_days" in fields:
        days = fields["default_shelf_life_days"]
        if days is not None and days < 0:
            raise ValidationError("validade padrão inválida")
        row.default_shelf_life_days = days
    if "packaging_description" in fields:
        row.packaging_description = _normalize_text(
            fields["packaging_description"], required=False, label="embalagem"
        )
    row.updated_by_user_id = principal.user_id
    row.row_version += 1
    try:
        session.flush()
    except IntegrityError as exc:
        raise ValidationError("código já existe nesta organização") from exc
    return row


def set_product_status(
    session: Session,
    principal: Principal,
    *,
    product_id: UUID,
    status: str,
    expected_row_version: int | None,
) -> TechnicalProduct:
    require_permission(principal, PERMISSION_PRODUCT_ACTIVATE)
    organization_id = _org(principal)
    if status not in PRODUCT_STATUSES:
        raise ValidationError("situação inválida")
    row = session.get(TechnicalProduct, product_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError("recurso_nao_encontrado")
    if expected_row_version is not None and row.row_version != expected_row_version:
        raise ValidationError("conflito_de_versao")
    row.status = status
    row.updated_by_user_id = principal.user_id
    row.row_version += 1
    session.flush()
    return row


def _family_ancestors(session: Session, organization_id: UUID, family_id: UUID) -> set[UUID]:
    seen: set[UUID] = set()
    current = family_id
    while current is not None:
        if current in seen:
            raise CycleError("família formaria um ciclo")
        seen.add(current)
        row = session.get(ProductFamily, current)
        if row is None or row.organization_id != organization_id:
            raise ValidationError("família inválida")
        current = row.parent_id  # type: ignore[assignment]
    return seen


def create_family(
    session: Session,
    principal: Principal,
    *,
    code: str,
    display_name: str,
    description: str | None = None,
    parent_id: UUID | None = None,
    status: str = STATUS_ACTIVE,
) -> ProductFamily:
    require_permission(principal, PERMISSION_PRODUCT_FAMILY_MANAGE)
    organization_id = _org(principal)
    if status not in FAMILY_STATUSES:
        raise ValidationError("situação inválida")
    if parent_id is not None:
        _family_ancestors(session, organization_id, parent_id)
    row = ProductFamily(
        organization_id=organization_id,
        code=_normalize_text(code, required=True, label="código"),  # type: ignore[arg-type]
        display_name=_normalize_text(display_name, required=True, label="nome"),  # type: ignore[arg-type]
        description=_normalize_text(description, required=False, label="descrição"),
        parent_id=parent_id,
        status=status,
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        raise ValidationError("código de família já existe nesta organização") from exc
    return row


def update_family(
    session: Session,
    principal: Principal,
    *,
    family_id: UUID,
    expected_row_version: int | None,
    **fields,
) -> ProductFamily:
    require_permission(principal, PERMISSION_PRODUCT_FAMILY_MANAGE)
    organization_id = _org(principal)
    row = session.get(ProductFamily, family_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError("recurso_nao_encontrado")
    if expected_row_version is not None and row.row_version != expected_row_version:
        raise ValidationError("conflito_de_versao")
    if "code" in fields and fields["code"] is not None:
        row.code = _normalize_text(fields["code"], required=True, label="código")  # type: ignore[assignment]
    if "display_name" in fields and fields["display_name"] is not None:
        row.display_name = _normalize_text(fields["display_name"], required=True, label="nome")  # type: ignore[assignment]
    if "description" in fields:
        row.description = _normalize_text(fields["description"], required=False, label="descrição")
    if "status" in fields and fields["status"] is not None:
        if fields["status"] not in FAMILY_STATUSES:
            raise ValidationError("situação inválida")
        row.status = fields["status"]
    if "parent_id" in fields:
        parent_id = fields["parent_id"]
        if parent_id == row.id:
            raise CycleError("família não pode ser pai de si mesma")
        if parent_id is not None:
            ancestors = _family_ancestors(session, organization_id, parent_id)
            if row.id in ancestors:
                raise CycleError("família formaria um ciclo")
        row.parent_id = parent_id
    row.row_version += 1
    try:
        session.flush()
    except IntegrityError as exc:
        raise ValidationError("código de família já existe nesta organização") from exc
    return row


def list_products_query(
    organization_id: UUID,
    *,
    q: str | None = None,
    status: str | None = None,
    purpose: str | None = None,
    supply_mode: str | None = None,
    family_id: UUID | None = None,
    code: str | None = None,
) -> Select[tuple[TechnicalProduct]]:
    stmt = select(TechnicalProduct).where(TechnicalProduct.organization_id == organization_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                TechnicalProduct.display_name.ilike(like),
                TechnicalProduct.code.ilike(like),
            )
        )
    if status:
        stmt = stmt.where(TechnicalProduct.status == status)
    if purpose:
        stmt = stmt.where(TechnicalProduct.purpose == purpose)
    if supply_mode:
        stmt = stmt.where(TechnicalProduct.supply_mode == supply_mode)
    if family_id:
        stmt = stmt.where(TechnicalProduct.family_id == family_id)
    if code:
        stmt = stmt.where(TechnicalProduct.code.ilike(code.strip()))
    return stmt.order_by(TechnicalProduct.display_name, TechnicalProduct.code)


def product_summary(session: Session, organization_id: UUID) -> dict[str, int]:
    rows = list(
        session.execute(
            select(TechnicalProduct).where(TechnicalProduct.organization_id == organization_id)
        ).scalars()
    )
    without_recipe = 0
    for row in rows:
        if (
            row.supply_mode == SUPPLY_PRODUCED
            and row.status == STATUS_ACTIVE
            and not has_published_recipe(session, row.id, organization_id)
        ):
            without_recipe += 1
    return {
        "total": len(rows),
        "active": sum(1 for row in rows if row.status == STATUS_ACTIVE),
        "purchased": sum(1 for row in rows if row.supply_mode == SUPPLY_PURCHASED),
        "intermediate": sum(1 for row in rows if row.purpose == "intermediate"),
        "produced_without_recipe": without_recipe,
    }


def related_recipe_count(session: Session, product_id: UUID, organization_id: UUID) -> int:
    return int(
        session.execute(
            select(func.count())
            .select_from(Formulation)
            .where(
                Formulation.technical_product_id == product_id,
                Formulation.organization_id == organization_id,
            )
        ).scalar_one()
    )


def related_order_count(session: Session, product_id: UUID, organization_id: UUID) -> int:
    return int(
        session.execute(
            select(func.count())
            .select_from(ProductionOrder)
            .where(
                ProductionOrder.technical_product_id == product_id,
                ProductionOrder.organization_id == organization_id,
            )
        ).scalar_one()
    )


def list_families(session: Session, organization_id: UUID) -> list[ProductFamily]:
    return list(
        session.execute(
            select(ProductFamily)
            .where(ProductFamily.organization_id == organization_id)
            .order_by(ProductFamily.display_name, ProductFamily.code)
        ).scalars()
    )


def new_idempotency() -> UUID:
    return uuid4()
