"""Contrato HTTP mínimo autenticado. Sem CRUD de negócio."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_runtime_session
from app.modules.identity_organization.access_tokens import (
    AccessTokenVerifier,
    TokenVerificationError,
)
from app.modules.identity_organization.authorization import (
    PERMISSION_IDENTITY_READ_ME,
    AuthorizationError,
    Principal,
    require_permission,
)
from app.modules.identity_organization.onboarding import (
    accept_invitation,
    actor_email,
    confirm_client_onboarding,
    describe_access,
)
from app.modules.identity_organization.services import (
    IdentityResolutionError,
    load_principal,
    lookup_identity,
    new_correlation_id,
    parse_organization_header,
    record_audit,
)
from app.modules.identity_organization.models import AppUser
from app.modules.identity_organization.tenant_context import apply_tenant_context

router = APIRouter()


class AssociationResponse(BaseModel):
    organization_id: UUID
    display_name: str = ""
    slug: str = ""
    roles: list[str] = Field(default_factory=list)
    status: str
    permissions: list[str]


class MeResponse(BaseModel):
    user_id: UUID | None = None
    display_name: str
    status: str
    selected_organization_id: UUID | None = None
    associations: list[AssociationResponse]
    roles: list[str]
    permissions: list[str] = Field(default_factory=list)
    access_state: str = "associado"
    commercial_condition_label: str | None = None
    invite_organization_name: str | None = None


def get_access_token_verifier() -> AccessTokenVerifier:
    from app.modules.identity_organization.access_tokens import (
        CognitoAccessTokenVerifier,
        FakeAccessTokenVerifier,
    )

    settings = get_settings()
    if settings.auth_verifier == "cognito":
        scopes = frozenset(part for part in settings.oidc_required_scope.split() if part)
        return CognitoAccessTokenVerifier(
            settings.oidc_issuer,
            settings.oidc_client_id,
            audience=settings.oidc_audience or None,
            required_scopes=scopes,
            jwks_timeout=settings.jwks_timeout_seconds,
        )
    return FakeAccessTokenVerifier()


def _bearer(authorization: str | None, max_bytes: int) -> str:
    if authorization is None or not authorization.strip():
        raise HTTPException(status_code=401, detail="nao_autenticado")
    if len(authorization.encode("utf-8")) > max_bytes:
        raise HTTPException(status_code=401, detail="nao_autenticado")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="nao_autenticado")
    return token.strip()


def _to_response(principal: Principal, *, access_state: str = "associado") -> MeResponse:
    associations = [
        AssociationResponse(
            organization_id=item.organization_id,
            display_name=item.organization_display_name,
            slug=item.organization_slug,
            roles=list(item.roles),
            status=item.status,
            permissions=sorted(item.permissions),
        )
        for item in principal.associations
    ]
    roles = [role for item in principal.associations for role in item.roles]
    if principal.selected is not None:
        roles = list(principal.selected.roles)
    return MeResponse(
        user_id=principal.user_id,
        display_name=principal.display_name,
        status=principal.status,
        selected_organization_id=(
            principal.selected.organization_id if principal.selected else None
        ),
        associations=associations,
        roles=roles,
        permissions=sorted(principal.permissions),
        access_state=access_state,
    )


@router.get("/api/v1/me", response_model=MeResponse)
def read_me(
    verifier: Annotated[AccessTokenVerifier, Depends(get_access_token_verifier)],
    session: Annotated[Session, Depends(get_runtime_session)],
    authorization: Annotated[str | None, Header()] = None,
    x_panne_organization_id: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> MeResponse:
    settings = get_settings()
    correlation_id = new_correlation_id(x_request_id)
    try:
        token = verifier.verify(_bearer(authorization, settings.max_authorization_header_bytes))
        requested = parse_organization_header(x_panne_organization_id)
    except TokenVerificationError as exc:
        if exc.unavailable:
            raise HTTPException(status_code=503, detail="indisponivel") from None
        raise HTTPException(status_code=401, detail="nao_autenticado") from None
    except AuthorizationError:
        raise HTTPException(status_code=403, detail="nao_autorizado") from None

    apply_tenant_context(
        session,
        organization_id=None,
        user_id=None,
        issuer=token.issuer,
        subject=token.subject,
    )
    identity = None
    try:
        identity = lookup_identity(session, token)
        apply_tenant_context(
            session,
            organization_id=None,
            user_id=identity.user_id,
            issuer=token.issuer,
            subject=token.subject,
        )
        principal = load_principal(session, identity, token, requested)
        apply_tenant_context(
            session,
            organization_id=(principal.selected.organization_id if principal.selected else None),
            user_id=principal.user_id,
            issuer=token.issuer,
            subject=token.subject,
        )
        require_permission(principal, PERMISSION_IDENTITY_READ_ME)
        record_audit(
            session,
            event_type="identity.authenticated",
            aggregate_type="app_user",
            aggregate_id=principal.user_id,
            organization_id=(principal.selected.organization_id if principal.selected else None),
            actor_user_id=principal.user_id,
            correlation_id=correlation_id,
            payload={"associations": len(principal.associations)},
        )
        return _to_response(principal)
    except IdentityResolutionError as exc:
        if exc.reason not in {"identidade_desconhecida", "sem_associacao"}:
            raise HTTPException(status_code=403, detail=_human(exc.reason)) from None
        return _unlinked_response(session, token, identity if exc.reason == "sem_associacao" else None)
    except AuthorizationError:
        raise HTTPException(status_code=403, detail="nao_autorizado") from None


_HUMAN = {
    "sem_autorizacao": "Esta conta não tem autorização para cadastrar um cliente.",
    "autorizacao_expirada": "A autorização para cadastrar expirou.",
    "autorizacao_usada": "Esta autorização já foi utilizada.",
    "autorizacao_de_outra_conta": "Esta autorização não corresponde a esta conta.",
    "email_ja_vinculado": "Este e-mail já está ligado a outra conta.",
    "email_de_outra_pessoa": "Este e-mail já está ligado a outra conta.",
    "slug_indisponivel": "Este código de cliente já está em uso.",
    "dados_confirmados_divergem": "Os dados não conferem com o cadastro já confirmado. Revise antes de continuar.",
    "convite_ausente": "Não há convite pendente para esta conta.",
    "identificador_invalido": "O identificador informado não confere com o tipo de titular.",
    "formalizacao_invalida": "A formalização não confere com o tipo de titular.",
    "codigo_invalido": "Use um código curto, com letras minúsculas e hífens.",
    "capacidade_invalida": "Escolha ao menos uma capacidade do estabelecimento.",
    "estabelecimento_invalido": "Escolha a natureza do estabelecimento.",
    "titular_invalido": "Escolha se o titular é pessoa física ou pessoa jurídica.",
    "nome_exibido_ausente": "Informe o nome do titular.",
    "nome_organizacao_ausente": "Informe o nome comercial.",
    "estabelecimento_ausente": "Informe o estabelecimento.",
    "identidade_vinculada_a_outra_organizacao": "Esta conta já está ligada a um cliente.",
    "conflito_de_cadastro": "O cadastro encontrou um conflito. Tente de novo.",
    "email_invalido": "Não foi possível confirmar o e-mail desta conta.",
}


def _human(reason: str) -> str:
    return _HUMAN.get(reason, "Não foi possível concluir o cadastro.")


def _unlinked_response(session: Session, token, identity) -> MeResponse:
    view = describe_access(session, token)
    display = ""
    user_id = None
    if identity is not None:
        user = session.get(AppUser, identity.user_id)
        user_id = identity.user_id
        display = user.display_name if user else ""
    return MeResponse(
        user_id=user_id,
        display_name=display,
        status="active",
        associations=[],
        roles=[],
        permissions=[],
        access_state=view.state,
        commercial_condition_label=view.commercial_condition_label,
        invite_organization_name=view.invite_organization_name,
    )


class OnboardingBody(BaseModel):
    trade_name: str
    holder_kind: str
    holder_name: str
    holder_fiscal_id: str
    formalization_state: str
    legal_name: str | None = None
    organization_code: str
    establishment_name: str
    establishment_code: str
    establishment_nature: str
    capabilities: list[str]
    accept_commercial_condition: bool = False


class OnboardingCreated(BaseModel):
    organization_id: UUID
    display_name: str
    establishment_name: str
    created: bool


def _verified(verifier, session, authorization):
    settings = get_settings()
    try:
        token = verifier.verify(_bearer(authorization, settings.max_authorization_header_bytes))
    except TokenVerificationError as exc:
        if exc.unavailable:
            raise HTTPException(status_code=503, detail="indisponivel") from None
        raise HTTPException(status_code=401, detail="nao_autenticado") from None
    email = actor_email(token)
    if email is None:
        raise HTTPException(status_code=422, detail=_human("email_invalido"))
    apply_tenant_context(
        session,
        organization_id=None,
        user_id=None,
        issuer=token.issuer,
        subject=token.subject,
        actor_email=email,
    )
    return token, email


@router.post("/api/v1/onboarding", response_model=OnboardingCreated)
def create_client(
    body: OnboardingBody,
    verifier: Annotated[AccessTokenVerifier, Depends(get_access_token_verifier)],
    session: Annotated[Session, Depends(get_runtime_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> OnboardingCreated:
    if not body.accept_commercial_condition:
        raise HTTPException(
            status_code=422,
            detail="Aceite a condição comercial apresentada para continuar.",
        )
    token, email = _verified(verifier, session, authorization)
    try:
        result = confirm_client_onboarding(
            session,
            issuer=token.issuer,
            subject=token.subject,
            email=email,
            display_name=body.holder_name,
            organization_slug=body.organization_code,
            legal_name=body.legal_name,
            organization_display_name=body.trade_name,
            establishment_code=body.establishment_code,
            establishment_display_name=body.establishment_name,
            holder_kind=body.holder_kind,
            holder_name=body.holder_name,
            holder_fiscal_id=body.holder_fiscal_id,
            formalization_state=body.formalization_state,
            establishment_nature=body.establishment_nature,
            capabilities=body.capabilities,
        )
    except IdentityResolutionError as exc:
        if exc.reason in {
            "slug_indisponivel",
            "email_ja_vinculado",
            "email_de_outra_pessoa",
            "dados_confirmados_divergem",
            "identidade_vinculada_a_outra_organizacao",
            "conflito_de_cadastro",
            "autorizacao_usada",
        }:
            status = 409
        elif exc.reason in {"sem_autorizacao", "autorizacao_expirada", "autorizacao_de_outra_conta"}:
            status = 403
        else:
            status = 422
        raise HTTPException(status_code=status, detail=_human(exc.reason)) from None
    return OnboardingCreated(
        organization_id=result.organization.id,
        display_name=result.organization.display_name,
        establishment_name=result.establishment.display_name,
        created=result.created,
    )


@router.post("/api/v1/onboarding/convite", response_model=OnboardingCreated)
def accept_client_invitation(
    verifier: Annotated[AccessTokenVerifier, Depends(get_access_token_verifier)],
    session: Annotated[Session, Depends(get_runtime_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> OnboardingCreated:
    token, _email = _verified(verifier, session, authorization)
    try:
        organization = accept_invitation(session, token)
    except IdentityResolutionError as exc:
        status = 409 if exc.reason in {"email_ja_vinculado", "email_de_outra_pessoa"} else 403
        raise HTTPException(status_code=status, detail=_human(exc.reason)) from None
    return OnboardingCreated(
        organization_id=organization.id,
        display_name=organization.display_name,
        establishment_name="",
        created=False,
    )
