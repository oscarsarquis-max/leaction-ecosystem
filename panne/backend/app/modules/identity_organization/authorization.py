"""Autorização interna por permissão explícita. Grupos do IdP não são canônicos."""

from dataclasses import dataclass
from uuid import UUID

PERMISSION_IDENTITY_READ_ME = "identity.read_me"
PERMISSION_ORGANIZATION_READ = "organization.read"
PERMISSION_MEMBERSHIP_READ = "membership.read"
PERMISSION_MEMBERSHIP_ROLE_MANAGE = "membership.role.manage"
PERMISSION_COMPLIANCE_REVIEW = "compliance.review"
PERMISSION_PRODUCTION_PLAN_READ = "production.plan.read"
PERMISSION_PRODUCTION_PLAN_MANAGE = "production.plan.manage"
PERMISSION_PRODUCTION_ORDER_READ = "production.order.read"
PERMISSION_PRODUCTION_ORDER_MANAGE = "production.order.manage"
PERMISSION_PRODUCTION_ORDER_RELEASE = "production.order.release"
PERMISSION_PRODUCTION_ORDER_CANCEL = "production.order.cancel"
PERMISSION_PRODUCTION_BATCH_MANAGE = "production.batch.manage"
PERMISSION_PRODUCTION_BOARD_READ = "production.board.read"
PERMISSION_PRODUCTION_WEIGHING_RECORD = "production.weighing.record"
PERMISSION_PRODUCTION_WEIGHING_VERIFY = "production.weighing.verify"
PERMISSION_PRODUCTION_CONSUMPTION_RECORD = "production.consumption.record"
PERMISSION_PRODUCTION_STEP_EXECUTE = "production.step.execute"
PERMISSION_PRODUCTION_OCCURRENCE_RECORD = "production.occurrence.record"
PERMISSION_PRODUCTION_OCCURRENCE_RESOLVE = "production.occurrence.resolve"
PERMISSION_PRODUCTION_BATCH_COMPLETE = "production.batch.complete"
PERMISSION_PRODUCTION_ORDER_COMPLETE = "production.order.complete"
PERMISSION_PRODUCTION_ORDER_SHORT_CLOSE = "production.order.short_close"
PERMISSION_PRODUCTION_SHEET_ISSUE = "production.sheet.issue"
PERMISSION_PRODUCTION_TRACEABILITY_READ = "production.traceability.read"
PERMISSION_PRODUCTION_ORDER_POLICY_ADOPT = "production.order.policy_adopt"
PERMISSION_INGREDIENT_READ = "ingredient.read"
PERMISSION_INGREDIENT_CREATE = "ingredient.create"
PERMISSION_INGREDIENT_UPDATE_DRAFT = "ingredient.update_draft"
PERMISSION_INGREDIENT_PUBLISH = "ingredient.publish"
PERMISSION_INGREDIENT_RETIRE = "ingredient.retire"
PERMISSION_SUPPLIER_READ = "supplier.read"
PERMISSION_SUPPLIER_MANAGE = "supplier.manage"
PERMISSION_SUPPLIER_PRICE_RECORD = "supplier.price.record"
PERMISSION_RECIPE_READ = "recipe.read"
PERMISSION_RECIPE_CREATE = "recipe.create"
PERMISSION_RECIPE_UPDATE_DRAFT = "recipe.update_draft"
PERMISSION_RECIPE_VERSION_CREATE = "recipe.version.create"
PERMISSION_RECIPE_SCALE = "recipe.scale"
PERMISSION_RECIPE_TRIAL_MANAGE = "recipe.trial.manage"
PERMISSION_RECIPE_REVIEW = "recipe.review"
PERMISSION_RECIPE_APPROVE = "recipe.approve"
PERMISSION_RECIPE_PUBLISH = "recipe.publish"
PERMISSION_RECIPE_RETIRE = "recipe.retire"
PERMISSION_RECIPE_REFERENCE_MANAGE = "recipe.reference.manage"
PERMISSION_RECIPE_TECHNICAL_SHEET_READ = "recipe.technical_sheet.read"
PERMISSION_RECIPE_AI_PROPOSE = "recipe.ai.propose"
PERMISSION_RECIPE_AI_REVIEW = "recipe.ai.review"
PERMISSION_RECIPE_AI_MATERIALIZE = "recipe.ai.materialize"

FOUNDATION_PERMISSIONS = (
    (PERMISSION_IDENTITY_READ_ME, "Ler o próprio perfil autenticado"),
    (PERMISSION_ORGANIZATION_READ, "Ler a organização da associação ativa"),
    (PERMISSION_MEMBERSHIP_READ, "Ler associações ativas do próprio usuário"),
    (PERMISSION_COMPLIANCE_REVIEW, "Revisar avaliações de conformidade"),
)
API_PERMISSION_DEFINITIONS = (
    (PERMISSION_MEMBERSHIP_ROLE_MANAGE, "Conceder e revogar papéis da associação"),
    (PERMISSION_PRODUCTION_ORDER_POLICY_ADOPT, "Adotar política em ordem liberada sem fatos"),
)
INGREDIENT_PERMISSION_DEFINITIONS = (
    (PERMISSION_INGREDIENT_READ, "Ler ingredientes e catálogos globais visíveis"),
    (PERMISSION_INGREDIENT_CREATE, "Criar identidade e primeira versão em rascunho"),
    (PERMISSION_INGREDIENT_UPDATE_DRAFT, "Editar rascunho de ingrediente"),
    (PERMISSION_INGREDIENT_PUBLISH, "Publicar versão de ingrediente"),
    (PERMISSION_INGREDIENT_RETIRE, "Aposentar versão publicada ou inativar identidade"),
    (PERMISSION_SUPPLIER_READ, "Ler fornecedores, itens e histórico de compra"),
    (PERMISSION_SUPPLIER_MANAGE, "Manter fornecedores e itens"),
    (PERMISSION_SUPPLIER_PRICE_RECORD, "Registrar valor de compra observado"),
)
RECIPE_PERMISSION_DEFINITIONS = (
    (PERMISSION_RECIPE_READ, "Ler receitas e versões da organização"),
    (PERMISSION_RECIPE_CREATE, "Criar receita, produto técnico e primeira versão"),
    (PERMISSION_RECIPE_UPDATE_DRAFT, "Editar rascunho de receita"),
    (PERMISSION_RECIPE_VERSION_CREATE, "Criar nova versão de receita"),
    (PERMISSION_RECIPE_SCALE, "Simular e gravar escala e nutrição técnica"),
    (PERMISSION_RECIPE_TRIAL_MANAGE, "Planejar, executar e concluir ensaios"),
    (PERMISSION_RECIPE_REVIEW, "Enviar versão para revisão"),
    (PERMISSION_RECIPE_APPROVE, "Aprovar, rejeitar ou revogar versão"),
    (PERMISSION_RECIPE_PUBLISH, "Publicar versão aprovada"),
    (PERMISSION_RECIPE_RETIRE, "Aposentar versão publicada"),
    (PERMISSION_RECIPE_REFERENCE_MANAGE, "Associar referências visíveis à receita"),
    (PERMISSION_RECIPE_TECHNICAL_SHEET_READ, "Ler ficha técnica derivada da versão"),
    (PERMISSION_RECIPE_AI_PROPOSE, "Gerar proposta assistida de receita"),
    (PERMISSION_RECIPE_AI_REVIEW, "Revisar proposta assistida de receita"),
    (PERMISSION_RECIPE_AI_MATERIALIZE, "Materializar proposta assistida em rascunho"),
)
PRODUCTION_PERMISSION_DEFINITIONS = (
    (PERMISSION_PRODUCTION_PLAN_READ, "Ler planos de produção"),
    (PERMISSION_PRODUCTION_PLAN_MANAGE, "Criar e programar planos de produção"),
    (PERMISSION_PRODUCTION_ORDER_READ, "Ler ordens de produção"),
    (PERMISSION_PRODUCTION_ORDER_MANAGE, "Criar e programar ordens de produção"),
    (PERMISSION_PRODUCTION_ORDER_RELEASE, "Liberar ordem com snapshot"),
    (PERMISSION_PRODUCTION_ORDER_CANCEL, "Cancelar ordem de produção"),
    (PERMISSION_PRODUCTION_BATCH_MANAGE, "Criar e dividir bateladas"),
    (PERMISSION_PRODUCTION_BOARD_READ, "Ler o quadro de produção"),
)
PRODUCTION_EXECUTION_PERMISSION_DEFINITIONS = (
    (PERMISSION_PRODUCTION_WEIGHING_RECORD, "Registrar pesagem de produção"),
    (PERMISSION_PRODUCTION_WEIGHING_VERIFY, "Conferir pesagem de produção"),
    (PERMISSION_PRODUCTION_CONSUMPTION_RECORD, "Registrar consumo real de material"),
    (PERMISSION_PRODUCTION_STEP_EXECUTE, "Executar etapa de produção"),
    (PERMISSION_PRODUCTION_OCCURRENCE_RECORD, "Registrar ocorrência de produção"),
    (PERMISSION_PRODUCTION_OCCURRENCE_RESOLVE, "Resolver ocorrência de produção"),
    (PERMISSION_PRODUCTION_BATCH_COMPLETE, "Concluir batelada de produção"),
    (PERMISSION_PRODUCTION_ORDER_COMPLETE, "Concluir ordem de produção"),
    (PERMISSION_PRODUCTION_ORDER_SHORT_CLOSE, "Encerrar ordem abaixo do planejado"),
    (PERMISSION_PRODUCTION_SHEET_ISSUE, "Emitir registro auditável da ficha"),
    (PERMISSION_PRODUCTION_TRACEABILITY_READ, "Ler rastreabilidade de produção"),
)
PERMISSIONS = (
    FOUNDATION_PERMISSIONS
    + PRODUCTION_PERMISSION_DEFINITIONS
    + PRODUCTION_EXECUTION_PERMISSION_DEFINITIONS
    + API_PERMISSION_DEFINITIONS
    + INGREDIENT_PERMISSION_DEFINITIONS
    + RECIPE_PERMISSION_DEFINITIONS
)
API_PERMISSIONS = (
    PERMISSION_MEMBERSHIP_ROLE_MANAGE,
    PERMISSION_PRODUCTION_ORDER_POLICY_ADOPT,
)
INGREDIENT_PERMISSIONS = (
    PERMISSION_INGREDIENT_READ,
    PERMISSION_INGREDIENT_CREATE,
    PERMISSION_INGREDIENT_UPDATE_DRAFT,
    PERMISSION_INGREDIENT_PUBLISH,
    PERMISSION_INGREDIENT_RETIRE,
    PERMISSION_SUPPLIER_READ,
    PERMISSION_SUPPLIER_MANAGE,
    PERMISSION_SUPPLIER_PRICE_RECORD,
)
RECIPE_PERMISSIONS = (
    PERMISSION_RECIPE_READ,
    PERMISSION_RECIPE_CREATE,
    PERMISSION_RECIPE_UPDATE_DRAFT,
    PERMISSION_RECIPE_VERSION_CREATE,
    PERMISSION_RECIPE_SCALE,
    PERMISSION_RECIPE_TRIAL_MANAGE,
    PERMISSION_RECIPE_REVIEW,
    PERMISSION_RECIPE_APPROVE,
    PERMISSION_RECIPE_PUBLISH,
    PERMISSION_RECIPE_RETIRE,
    PERMISSION_RECIPE_REFERENCE_MANAGE,
    PERMISSION_RECIPE_TECHNICAL_SHEET_READ,
    PERMISSION_RECIPE_AI_PROPOSE,
    PERMISSION_RECIPE_AI_REVIEW,
    PERMISSION_RECIPE_AI_MATERIALIZE,
)

PRODUCTION_PERMISSIONS = (
    PERMISSION_PRODUCTION_PLAN_READ,
    PERMISSION_PRODUCTION_PLAN_MANAGE,
    PERMISSION_PRODUCTION_ORDER_READ,
    PERMISSION_PRODUCTION_ORDER_MANAGE,
    PERMISSION_PRODUCTION_ORDER_RELEASE,
    PERMISSION_PRODUCTION_ORDER_CANCEL,
    PERMISSION_PRODUCTION_BATCH_MANAGE,
    PERMISSION_PRODUCTION_BOARD_READ,
)
PRODUCTION_EXECUTION_PERMISSIONS = (
    PERMISSION_PRODUCTION_WEIGHING_RECORD,
    PERMISSION_PRODUCTION_WEIGHING_VERIFY,
    PERMISSION_PRODUCTION_CONSUMPTION_RECORD,
    PERMISSION_PRODUCTION_STEP_EXECUTE,
    PERMISSION_PRODUCTION_OCCURRENCE_RECORD,
    PERMISSION_PRODUCTION_OCCURRENCE_RESOLVE,
    PERMISSION_PRODUCTION_BATCH_COMPLETE,
    PERMISSION_PRODUCTION_ORDER_COMPLETE,
    PERMISSION_PRODUCTION_ORDER_SHORT_CLOSE,
    PERMISSION_PRODUCTION_SHEET_ISSUE,
    PERMISSION_PRODUCTION_TRACEABILITY_READ,
)

EXISTING_ROLES = (
    "owner",
    "administrator",
    "technical_responsible",
    "production",
    "commercial",
    "viewer",
)
ADDED_ROLES = (
    "organization_owner",
    "organization_admin",
    "production_manager",
    "baker_operator",
    "regulatory_reviewer",
    "restricted",
)
MEMBERSHIP_ROLES = EXISTING_ROLES + ADDED_ROLES

ROLE_ALIASES = {
    "owner": "organization_owner",
    "administrator": "organization_admin",
    "production": "production_manager",
}

_READ_ME = (
    PERMISSION_IDENTITY_READ_ME,
    PERMISSION_ORGANIZATION_READ,
    PERMISSION_MEMBERSHIP_READ,
)
_REVIEW = _READ_ME + (PERMISSION_COMPLIANCE_REVIEW,)
_ROLE_MANAGE = (PERMISSION_MEMBERSHIP_ROLE_MANAGE,)
_POLICY_ADOPT = (PERMISSION_PRODUCTION_ORDER_POLICY_ADOPT,)
_PRODUCTION_ADMIN = PRODUCTION_PERMISSIONS + PRODUCTION_EXECUTION_PERMISSIONS + _POLICY_ADOPT
_PRODUCTION_READ = (
    PERMISSION_PRODUCTION_PLAN_READ,
    PERMISSION_PRODUCTION_ORDER_READ,
    PERMISSION_PRODUCTION_BOARD_READ,
)
_PRODUCTION_TECHNICAL = _PRODUCTION_READ + (PERMISSION_PRODUCTION_TRACEABILITY_READ,)
_PRODUCTION_BAKER = (
    PERMISSION_PRODUCTION_ORDER_READ,
    PERMISSION_PRODUCTION_BOARD_READ,
    PERMISSION_PRODUCTION_WEIGHING_RECORD,
    PERMISSION_PRODUCTION_WEIGHING_VERIFY,
    PERMISSION_PRODUCTION_CONSUMPTION_RECORD,
    PERMISSION_PRODUCTION_STEP_EXECUTE,
    PERMISSION_PRODUCTION_OCCURRENCE_RECORD,
    PERMISSION_PRODUCTION_TRACEABILITY_READ,
)
_INGREDIENT_ADMIN = INGREDIENT_PERMISSIONS
_INGREDIENT_READ = (PERMISSION_INGREDIENT_READ, PERMISSION_SUPPLIER_READ)
_INGREDIENT_TECHNICAL = (
    PERMISSION_INGREDIENT_READ,
    PERMISSION_INGREDIENT_CREATE,
    PERMISSION_INGREDIENT_UPDATE_DRAFT,
    PERMISSION_INGREDIENT_PUBLISH,
    PERMISSION_INGREDIENT_RETIRE,
    PERMISSION_SUPPLIER_READ,
    PERMISSION_SUPPLIER_MANAGE,
    PERMISSION_SUPPLIER_PRICE_RECORD,
)
_INGREDIENT_COMMERCIAL = (
    PERMISSION_INGREDIENT_READ,
    PERMISSION_SUPPLIER_READ,
    PERMISSION_SUPPLIER_MANAGE,
    PERMISSION_SUPPLIER_PRICE_RECORD,
)
_RECIPE_ADMIN = RECIPE_PERMISSIONS
_RECIPE_READ = (PERMISSION_RECIPE_READ, PERMISSION_RECIPE_TECHNICAL_SHEET_READ)
_RECIPE_TECHNICAL = RECIPE_PERMISSIONS
_RECIPE_REVIEW = _RECIPE_READ + (
    PERMISSION_RECIPE_REVIEW,
    PERMISSION_RECIPE_APPROVE,
    PERMISSION_RECIPE_AI_REVIEW,
)

ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "owner": _REVIEW + _PRODUCTION_ADMIN + _ROLE_MANAGE + _INGREDIENT_ADMIN + _RECIPE_ADMIN,
    "organization_owner": (
        _REVIEW + _PRODUCTION_ADMIN + _ROLE_MANAGE + _INGREDIENT_ADMIN + _RECIPE_ADMIN
    ),
    "administrator": (
        _REVIEW + _PRODUCTION_ADMIN + _ROLE_MANAGE + _INGREDIENT_ADMIN + _RECIPE_ADMIN
    ),
    "organization_admin": (
        _REVIEW + _PRODUCTION_ADMIN + _ROLE_MANAGE + _INGREDIENT_ADMIN + _RECIPE_ADMIN
    ),
    "regulatory_reviewer": _REVIEW + _INGREDIENT_READ + _RECIPE_REVIEW,
    "technical_responsible": (
        _READ_ME + _PRODUCTION_TECHNICAL + _INGREDIENT_TECHNICAL + _RECIPE_TECHNICAL
    ),
    "production": _READ_ME + _PRODUCTION_ADMIN + _INGREDIENT_READ + _RECIPE_READ,
    "production_manager": _READ_ME + _PRODUCTION_ADMIN + _INGREDIENT_READ + _RECIPE_READ,
    "commercial": _READ_ME + _INGREDIENT_COMMERCIAL + _RECIPE_READ,
    "baker_operator": _READ_ME + _PRODUCTION_BAKER + (PERMISSION_INGREDIENT_READ,) + _RECIPE_READ,
    "viewer": _READ_ME + _PRODUCTION_READ + _INGREDIENT_READ + _RECIPE_READ,
    "restricted": (),
}


class AuthorizationError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Association:
    organization_id: UUID
    status: str
    permissions: frozenset[str]
    roles: tuple[str, ...]
    organization_display_name: str = ""
    organization_slug: str = ""


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    display_name: str
    status: str
    issuer: str
    subject: str
    associations: tuple[Association, ...]
    selected: Association | None

    @property
    def permissions(self) -> frozenset[str]:
        if self.selected is None:
            granted: set[str] = set()
            for item in self.associations:
                granted.update(item.permissions)
            return frozenset(granted)
        return self.selected.permissions


def canonical_role(role: str) -> str:
    return ROLE_ALIASES.get(role, role)


def permissions_for_role(role: str) -> frozenset[str]:
    return frozenset(ROLE_PERMISSIONS.get(role, ()))


def require_permission(principal: Principal, code: str) -> None:
    if code not in principal.permissions:
        raise AuthorizationError("permissao_negada")
