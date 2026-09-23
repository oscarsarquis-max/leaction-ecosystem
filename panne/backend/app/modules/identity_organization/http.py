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
from app.modules.identity_organization.account_profile import (
    AccountProfileError,
    AccountProfileSource,
    CognitoAccountProfile,
    UnverifiedAccountProfile,
)
from app.modules.identity_organization.authorization import (
    PERMISSION_IDENTITY_READ_ME,
    AuthorizationError,
    Principal,
    require_permission,
)
from app.modules.identity_organization.access_code import (
    NOTICE,
    AccessCodeError,
    confirm_code_change,
    request_code_change,
)
from app.modules.identity_organization.onboarding import (
    AccessView,
    accept_invitation,
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


def get_account_profile() -> AccountProfileSource:
    settings = get_settings()
    if settings.auth_verifier == "cognito":
        return CognitoAccountProfile()
    return UnverifiedAccountProfile()


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
    profile: Annotated[AccountProfileSource, Depends(get_account_profile)],
    session: Annotated[Session, Depends(get_runtime_session)],
    authorization: Annotated[str | None, Header()] = None,
    x_panne_organization_id: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> MeResponse:
    settings = get_settings()
    correlation_id = new_correlation_id(x_request_id)
    try:
        raw_token = _bearer(authorization, settings.max_authorization_header_bytes)
        token = verifier.verify(raw_token)
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
        linked = identity if exc.reason == "sem_associacao" else None
        if exc.reason == "sem_associacao" and linked is not None:
            user = session.get(AppUser, linked.user_id)
            known = user.email.strip().lower() if user is not None and user.email else None
            return _unlinked_response(session, token, linked, known)
        return _recognize(session, token, profile, raw_token)
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


def _recognize(session: Session, token, profile: AccountProfileSource, raw_token: str) -> MeResponse:
    try:
        email = profile.verified_email(raw_token)
    except AccountProfileError as exc:
        if exc.unavailable:
            view = describe_access(session, token, None)
            if view.state == "autorizado":
                return _unlinked_response(session, token, None, None, view)
            raise HTTPException(status_code=503, detail="indisponivel") from None
        return _unlinked_response(
            session,
            token,
            None,
            None,
            AccessView(state="email_nao_confirmado"),
        )
    return _unlinked_response(session, token, None, email)


def _unlinked_response(
    session: Session,
    token,
    identity,
    email: str | None = None,
    view: AccessView | None = None,
) -> MeResponse:
    resolved = view if view is not None else describe_access(session, token, email)
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
        access_state=resolved.state,
        commercial_condition_label=resolved.commercial_condition_label,
        invite_organization_name=resolved.invite_organization_name,
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


def _verified(verifier, profile: AccountProfileSource, session, authorization):
    settings = get_settings()
    try:
        raw_token = _bearer(authorization, settings.max_authorization_header_bytes)
        token = verifier.verify(raw_token)
    except TokenVerificationError as exc:
        if exc.unavailable:
            raise HTTPException(status_code=503, detail="indisponivel") from None
        raise HTTPException(status_code=401, detail="nao_autenticado") from None
    try:
        email = profile.verified_email(raw_token)
    except AccountProfileError as exc:
        if exc.unavailable:
            raise HTTPException(status_code=503, detail="indisponivel") from None
        raise HTTPException(status_code=422, detail=_human("email_invalido")) from None
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
    profile: Annotated[AccountProfileSource, Depends(get_account_profile)],
    session: Annotated[Session, Depends(get_runtime_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> OnboardingCreated:
    if not body.accept_commercial_condition:
        raise HTTPException(
            status_code=422,
            detail="Aceite a condição comercial apresentada para continuar.",
        )
    token, email = _verified(verifier, profile, session, authorization)
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
    profile: Annotated[AccountProfileSource, Depends(get_account_profile)],
    session: Annotated[Session, Depends(get_runtime_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> OnboardingCreated:
    token, email = _verified(verifier, profile, session, authorization)
    try:
        organization = accept_invitation(session, token, email)
    except IdentityResolutionError as exc:
        status = 409 if exc.reason in {"email_ja_vinculado", "email_de_outra_pessoa"} else 403
        raise HTTPException(status_code=status, detail=_human(exc.reason)) from None
    return OnboardingCreated(
        organization_id=organization.id,
        display_name=organization.display_name,
        establishment_name="",
        created=False,
    )


class CodeChangeRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class CodeChangeConfirm(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    confirmation: str = Field(min_length=10, max_length=200)


@router.post("/api/v1/access/code-change")
def request_access_code_change(
    body: CodeChangeRequest,
    session: Annotated[Session, Depends(get_runtime_session)],
) -> dict[str, str]:
    apply_tenant_context(session, organization_id=None, user_id=None, actor_email=body.email)
    try:
        from app.modules.identity_organization.access_code_aws import SesMailer

        request_code_change(session, body.email, SesMailer())
    except AccessCodeError:
        session.rollback()
    return {"notice": NOTICE}


@router.post("/api/v1/access/code-change/confirm")
def confirm_access_code_change(
    body: CodeChangeConfirm,
    session: Annotated[Session, Depends(get_runtime_session)],
) -> dict[str, str]:
    apply_tenant_context(session, organization_id=None, user_id=None, actor_email=body.email)
    try:
        from app.modules.identity_organization.access_code_aws import CognitoDirectory, SesMailer

        confirm_code_change(session, body.email, body.confirmation, CognitoDirectory(), SesMailer())
    except AccessCodeError:
        session.rollback()
    return {"notice": NOTICE}
