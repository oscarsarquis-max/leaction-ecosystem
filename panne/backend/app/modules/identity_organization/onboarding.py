"""Onboarding do cliente da Panne. A gratuidade vem da autorização, não do formulário."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import re
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.identity_organization.access_tokens import VerifiedAccessToken
from app.modules.identity_organization.authorization import MEMBERSHIP_ROLES
from app.modules.identity_organization.models import (
    AppUser,
    AuthIdentity,
    Establishment,
    OnboardingAuthorization,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
    OrganizationMembershipRole,
)
from app.modules.identity_organization.services import (
    IdentityResolutionError,
    ProductiveOnboardingResult,
    record_audit,
)
from app.modules.identity_organization.tenant_context import apply_tenant_context

_CODE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CAPABILITIES = frozenset({"sale", "stock", "production"})
CONDITION_LABELS = {
    "complimentary": "Acesso sem cobrança da Panne nesta etapa",
    "standard": "Condição comercial padrão da Panne",
}


@dataclass(frozen=True)
class AccessView:
    state: str
    commercial_condition_label: str | None = None
    invite_organization_name: str | None = None
    user_id: UUID | None = None
    display_name: str = ""


def actor_email(token: VerifiedAccessToken) -> str | None:
    for key in ("email", "username", "cognito:username"):
        value = token.raw_claims.get(key)
        if isinstance(value, str) and "@" in value and " " not in value:
            return value.strip().lower()
    return None


def issue_onboarding_authorization(
    session: Session,
    *,
    email: str,
    commercial_condition: str,
    valid_hours: int = 72,
    actor_user_id: UUID | None = None,
) -> OnboardingAuthorization:
    """Emite uma autorização individual, temporária e de um único cliente."""
    email_key = _email(email)
    if commercial_condition not in CONDITION_LABELS:
        raise IdentityResolutionError("condicao_invalida")
    if valid_hours < 1 or valid_hours > 24 * 30:
        raise IdentityResolutionError("prazo_invalido")
    row = OnboardingAuthorization(
        email_normalized=email_key,
        commercial_condition=commercial_condition,
        max_clients=1,
        clients_created=0,
        status="issued",
        expires_at=datetime.now(UTC) + timedelta(hours=valid_hours),
    )
    session.add(row)
    session.flush()
    record_audit(
        session,
        event_type="onboarding.authorization_issued",
        aggregate_type="onboarding_authorization",
        aggregate_id=row.id,
        actor_user_id=actor_user_id,
        payload={"commercial_condition": commercial_condition, "max_clients": 1},
    )
    return row


@dataclass(frozen=True)
class AuthorizationRecord:
    """Consulta administrativa. Não inclui e-mail, documento nem segredo."""

    id: UUID
    status: str
    commercial_condition: str
    expires_at: datetime
    clients_created: int
    bound: bool
    organization_id: UUID | None


def list_onboarding_authorizations(session: Session, email: str) -> list[AuthorizationRecord]:
    email_key = _email(email)
    rows = session.scalars(
        select(OnboardingAuthorization)
        .where(OnboardingAuthorization.email_normalized == email_key)
        .order_by(OnboardingAuthorization.created_at)
    )
    return [_record(row) for row in rows]


def revoke_onboarding_authorization(
    session: Session,
    authorization_id: UUID,
    *,
    actor_user_id: UUID | None = None,
) -> AuthorizationRecord:
    row = session.get(OnboardingAuthorization, authorization_id)
    if row is None:
        raise IdentityResolutionError("autorizacao_ausente")
    if row.status not in {"issued", "bound"}:
        raise IdentityResolutionError("autorizacao_encerrada")
    previous = row.status
    row.status = "revoked"
    session.flush()
    record_audit(
        session,
        event_type="onboarding.authorization_revoked",
        aggregate_type="onboarding_authorization",
        aggregate_id=row.id,
        actor_user_id=actor_user_id,
        payload={"from": previous, "to": "revoked"},
    )
    return _record(row)


def _record(row: OnboardingAuthorization) -> AuthorizationRecord:
    return AuthorizationRecord(
        id=row.id,
        status=row.status,
        commercial_condition=row.commercial_condition,
        expires_at=row.expires_at,
        clients_created=row.clients_created,
        bound=row.issuer is not None and row.subject is not None,
        organization_id=row.organization_id,
    )


def describe_access(
    session: Session,
    token: VerifiedAccessToken,
    email: str | None,
) -> AccessView:
    """O e-mail vem da conta autenticada no provedor, não das claims nem do formulário."""
    email_key = _email(email) if email else None
    _context(session, token, email_key, None, None)
    invite = _pending_invite(session, email_key)
    if invite is not None:
        organization = session.get(Organization, invite.organization_id)
        return AccessView(
            state="convidado",
            invite_organization_name=organization.display_name if organization else "",
        )
    authorization = _open_authorization(session, email_key, token.issuer, token.subject)
    if authorization is not None:
        if authorization.issuer is None:
            authorization.issuer = token.issuer
            authorization.subject = token.subject
            session.flush()
        elif authorization.issuer != token.issuer or authorization.subject != token.subject:
            return AccessView(state="autorizacao_de_outra_conta")
        return AccessView(
            state="autorizado",
            commercial_condition_label=CONDITION_LABELS[authorization.commercial_condition],
        )
    return AccessView(state=_closed_access(session, email_key))


def confirm_client_onboarding(
    session: Session,
    *,
    issuer: str,
    subject: str,
    email: str,
    display_name: str,
    organization_slug: str,
    legal_name: str | None,
    organization_display_name: str,
    establishment_code: str,
    establishment_display_name: str,
    holder_kind: str,
    holder_name: str,
    holder_fiscal_id: str,
    formalization_state: str,
    establishment_nature: str,
    capabilities: tuple[str, ...] | list[str],
) -> ProductiveOnboardingResult:
    issuer_n = _text(issuer, "identidade_invalida")
    subject_n = _text(subject, "identidade_invalida")
    email_key = _email(email)
    person_name = _text(holder_name or display_name, "nome_exibido_ausente")
    trade_name = _text(organization_display_name, "nome_organizacao_ausente")
    slug = _code(organization_slug, "codigo_invalido")
    establishment_code_n = _code(establishment_code, "codigo_invalido")
    establishment_name = _text(establishment_display_name, "estabelecimento_ausente")
    fiscal_type, fiscal_digits, legal, state = _holder(
        holder_kind, formalization_state, legal_name, holder_fiscal_id
    )
    nature, caps = _place(establishment_nature, capabilities)
    _lock(session, email_key, issuer_n, subject_n, slug)
    _context(session, _token(issuer_n, subject_n, email_key), email_key, None, None)
    nested = session.begin_nested()
    try:
        result = _apply(
            session,
            issuer=issuer_n,
            subject=subject_n,
            email=email_key,
            person_name=person_name,
            slug=slug,
            legal=legal,
            trade_name=trade_name,
            establishment_code=establishment_code_n,
            establishment_name=establishment_name,
            holder_kind=holder_kind,
            fiscal_type=fiscal_type,
            fiscal_digits=fiscal_digits,
            state=state,
            nature=nature,
            capabilities=caps,
        )
        nested.commit()
        return result
    except IntegrityError:
        nested.rollback()
    except IdentityResolutionError:
        nested.rollback()
        raise
    return _recover(
        session,
        issuer=issuer_n,
        subject=subject_n,
        email_key=email_key,
        person_name=person_name,
        slug=slug,
        legal=legal,
        trade_name=trade_name,
        establishment_code=establishment_code_n,
        establishment_name=establishment_name,
        holder_kind=holder_kind,
        fiscal_type=fiscal_type,
        fiscal_digits=fiscal_digits,
        state=state,
        nature=nature,
        capabilities=caps,
    )


def accept_invitation(
    session: Session,
    token: VerifiedAccessToken,
    email: str | None = None,
) -> Organization:
    email_key = _email(email) if email else actor_email(token)
    if email_key is None:
        raise IdentityResolutionError("convite_ausente")
    _context(session, token, email_key, None, None)
    invite = _pending_invite(session, email_key)
    if invite is None:
        raise IdentityResolutionError("convite_ausente")
    organization = session.get(Organization, invite.organization_id)
    if organization is None:
        raise IdentityResolutionError("convite_ausente")
    identity = _identity(session, token.issuer, token.subject)
    user = session.scalar(select(AppUser).where(func.lower(AppUser.email) == email_key))
    if identity is not None and user is not None and identity.user_id != user.id:
        raise IdentityResolutionError("email_de_outra_pessoa")
    if identity is None and user is not None:
        raise IdentityResolutionError("email_ja_vinculado")
    if identity is None:
        user_id = uuid4()
        _context(session, token, email_key, organization.id, user_id)
        user = AppUser(
            id=user_id, email=email_key, display_name="Conta convidada", status="active"
        )
        session.add(user)
        session.flush()
        identity = AuthIdentity(
            user_id=user.id, issuer=token.issuer, subject=token.subject, status="active"
        )
        session.add(identity)
        session.flush()
    else:
        user = session.get(AppUser, identity.user_id)
    if user is None:
        raise IdentityResolutionError("convite_ausente")
    _context(session, token, email_key, organization.id, user.id)
    membership = session.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization.id,
            OrganizationMembership.user_id == user.id,
        )
    )
    if membership is None:
        membership = OrganizationMembership(
            organization_id=organization.id,
            user_id=user.id,
            legacy_role_label=invite.role,
            status="active",
        )
        session.add(membership)
        session.flush()
        session.add(
            OrganizationMembershipRole(
                organization_id=organization.id,
                membership_id=membership.id,
                role=invite.role,
                granted_by_user_id=user.id,
                reason="convite_aceito",
            )
        )
    invite.status = "accepted"
    invite.accepted_at = datetime.now(UTC)
    session.flush()
    record_audit(
        session,
        event_type="invitation.accepted",
        aggregate_type="organization_invitation",
        aggregate_id=invite.id,
        organization_id=organization.id,
        actor_user_id=user.id,
        payload={"role": invite.role},
    )
    return organization


def create_organization_invitation(
    session: Session,
    *,
    organization_id: UUID,
    email: str,
    role: str,
    valid_hours: int = 168,
    actor_user_id: UUID | None = None,
) -> OrganizationInvitation:
    if role not in MEMBERSHIP_ROLES:
        raise IdentityResolutionError("papel_invalido")
    if valid_hours < 1 or valid_hours > 24 * 30:
        raise IdentityResolutionError("prazo_invalido")
    row = OrganizationInvitation(
        organization_id=organization_id,
        email_normalized=_email(email),
        role=role,
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(hours=valid_hours),
    )
    session.add(row)
    session.flush()
    record_audit(
        session,
        event_type="invitation.created",
        aggregate_type="organization_invitation",
        aggregate_id=row.id,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        payload={"role": role},
    )
    return row


def formalize_organization(
    session: Session,
    *,
    organization_id: UUID,
    actor_user_id: UUID,
    legal_name: str,
    cnpj: str,
) -> Organization:
    apply_tenant_context(
        session,
        organization_id=organization_id,
        user_id=actor_user_id,
    )
    owner = session.scalar(
        select(OrganizationMembershipRole.id)
        .join(
            OrganizationMembership,
            OrganizationMembership.id == OrganizationMembershipRole.membership_id,
        )
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == actor_user_id,
            OrganizationMembership.status == "active",
            OrganizationMembershipRole.role == "owner",
            OrganizationMembershipRole.revoked_at.is_(None),
        )
    )
    organization = session.get(Organization, organization_id)
    if organization is None or owner is None:
        raise IdentityResolutionError("formalizacao_invalida")
    if organization.formalization_state not in {"not_formalized", "self_employed"}:
        raise IdentityResolutionError("formalizacao_invalida")
    if organization.holder_kind != "natural_person":
        raise IdentityResolutionError("formalizacao_invalida")
    legal = _text(legal_name, "formalizacao_invalida")
    digits = _digits(cnpj)
    if len(digits) != 14 or len(set(digits)) == 1:
        raise IdentityResolutionError("identificador_invalido")
    previous = organization.formalization_state
    organization.holder_kind = "legal_entity"
    organization.legal_name = legal
    organization.holder_fiscal_id_type = "cnpj"
    organization.holder_fiscal_id = digits
    organization.fiscal_id_status = "recorded"
    organization.formalization_state = "formalized"
    session.flush()
    record_audit(
        session,
        event_type="organization.formalized",
        aggregate_type="organization",
        aggregate_id=organization.id,
        organization_id=organization.id,
        actor_user_id=actor_user_id,
        payload={"from": previous, "to": "formalized"},
    )
    return organization


def _apply(session: Session, **kwargs) -> ProductiveOnboardingResult:
    issuer = kwargs["issuer"]
    subject = kwargs["subject"]
    email_key = kwargs["email"]
    identity = _identity(session, issuer, subject)
    user_by_email = session.scalar(select(AppUser).where(func.lower(AppUser.email) == email_key))
    if identity is not None and user_by_email is not None and identity.user_id != user_by_email.id:
        raise IdentityResolutionError("email_de_outra_pessoa")
    if identity is None and user_by_email is not None:
        raise IdentityResolutionError("email_ja_vinculado")
    if identity is not None:
        _context(session, _token(issuer, subject, email_key), email_key, None, identity.user_id)
        return _replay(session, identity=identity, **kwargs)
    authorization = _require_authorization(session, email_key, issuer, subject)
    if session.scalar(select(Organization.id).where(Organization.slug == kwargs["slug"])) is not None:
        raise IdentityResolutionError("slug_indisponivel")
    authorization.issuer = issuer
    authorization.subject = subject
    authorization.status = "bound"
    session.flush()
    organization_id = uuid4()
    user_id = uuid4()
    _context(session, _token(issuer, subject, email_key), email_key, organization_id, user_id)
    organization = Organization(
        id=organization_id,
        slug=kwargs["slug"],
        legal_name=kwargs["legal"],
        display_name=kwargs["trade_name"],
        holder_kind=kwargs["holder_kind"],
        holder_name=kwargs["person_name"],
        holder_fiscal_id_type=kwargs["fiscal_type"],
        holder_fiscal_id=kwargs["fiscal_digits"],
        fiscal_id_status="recorded",
        formalization_state=kwargs["state"],
        commercial_condition=authorization.commercial_condition,
        status="active",
    )
    user = AppUser(
        id=user_id, email=email_key, display_name=kwargs["person_name"], status="active"
    )
    session.add_all([organization, user])
    session.flush()
    linked = AuthIdentity(user_id=user.id, issuer=issuer, subject=subject, status="active")
    session.add(linked)
    session.flush()
    _context(session, _token(issuer, subject, email_key), email_key, organization.id, user.id)
    establishment = Establishment(
        organization_id=organization.id,
        code=kwargs["establishment_code"],
        display_name=kwargs["establishment_name"],
        nature=kwargs["nature"],
        capabilities=list(kwargs["capabilities"]),
        status="active",
    )
    membership = OrganizationMembership(
        organization_id=organization.id,
        user_id=user.id,
        legacy_role_label="owner",
        status="active",
    )
    session.add_all([establishment, membership])
    session.flush()
    session.add(
        OrganizationMembershipRole(
            organization_id=organization.id,
            membership_id=membership.id,
            role="owner",
            granted_by_user_id=user.id,
            reason="onboarding_produtivo",
        )
    )
    authorization.clients_created = 1
    authorization.status = "consumed"
    authorization.consumed_at = datetime.now(UTC)
    authorization.organization_id = organization.id
    session.flush()
    record_audit(
        session,
        event_type="organization.onboarded",
        aggregate_type="organization",
        aggregate_id=organization.id,
        organization_id=organization.id,
        actor_user_id=user.id,
        payload={
            "created": True,
            "holder_kind": kwargs["holder_kind"],
            "formalization_state": kwargs["state"],
            "commercial_condition": authorization.commercial_condition,
        },
    )
    session.flush()
    return ProductiveOnboardingResult(
        organization=organization,
        establishment=establishment,
        user=user,
        membership=membership,
        identity=linked,
        created=True,
    )


def _recover(session: Session, **kwargs) -> ProductiveOnboardingResult:
    identity = _identity(session, kwargs["issuer"], kwargs["subject"])
    user_by_email = session.scalar(
        select(AppUser).where(func.lower(AppUser.email) == kwargs["email_key"])
    )
    if identity is not None and user_by_email is not None and identity.user_id != user_by_email.id:
        raise IdentityResolutionError("email_de_outra_pessoa")
    if identity is None and user_by_email is not None:
        raise IdentityResolutionError("email_ja_vinculado")
    if identity is not None:
        _context(
            session,
            _token(kwargs["issuer"], kwargs["subject"], kwargs["email_key"]),
            kwargs["email_key"],
            None,
            identity.user_id,
        )
        return _replay(session, identity=identity, email=kwargs["email_key"], **kwargs)
    if session.scalar(select(Organization.id).where(Organization.slug == kwargs["slug"])) is not None:
        raise IdentityResolutionError("slug_indisponivel")
    raise IdentityResolutionError("conflito_de_cadastro")


def _replay(session: Session, *, identity: AuthIdentity, **kwargs) -> ProductiveOnboardingResult:
    user = session.get(AppUser, identity.user_id)
    email_key = kwargs["email"]
    if user is None or user.email.lower() != email_key:
        raise IdentityResolutionError("email_de_outra_pessoa")
    memberships = list(
        session.scalars(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.status == "active",
            )
        )
    )
    if len(memberships) != 1:
        raise IdentityResolutionError("identidade_vinculada_a_outra_organizacao")
    membership = memberships[0]
    _context(
        session,
        _token(kwargs["issuer"], kwargs["subject"], email_key),
        email_key,
        membership.organization_id,
        user.id,
    )
    organization = session.get(Organization, membership.organization_id)
    if organization is None or organization.slug != kwargs["slug"]:
        raise IdentityResolutionError("identidade_vinculada_a_outra_organizacao")
    establishment = session.scalar(
        select(Establishment).where(
            Establishment.organization_id == organization.id,
            Establishment.code == kwargs["establishment_code"],
            Establishment.status == "active",
        )
    )
    role = session.scalar(
        select(OrganizationMembershipRole).where(
            OrganizationMembershipRole.membership_id == membership.id,
            OrganizationMembershipRole.role == "owner",
            OrganizationMembershipRole.revoked_at.is_(None),
        )
    )
    same = (
        user.display_name == kwargs["person_name"]
        and organization.display_name == kwargs["trade_name"]
        and organization.legal_name == kwargs["legal"]
        and organization.holder_kind == kwargs["holder_kind"]
        and organization.holder_fiscal_id == kwargs["fiscal_digits"]
        and organization.formalization_state == kwargs["state"]
        and establishment is not None
        and establishment.display_name == kwargs["establishment_name"]
        and establishment.nature == kwargs["nature"]
        and tuple(establishment.capabilities or []) == tuple(kwargs["capabilities"])
        and role is not None
    )
    if not same or establishment is None:
        raise IdentityResolutionError("dados_confirmados_divergem")
    return ProductiveOnboardingResult(
        organization=organization,
        establishment=establishment,
        user=user,
        membership=membership,
        identity=identity,
        created=False,
    )


def _require_authorization(session: Session, email_key: str, issuer: str, subject: str):
    row = _open_authorization(session, email_key, issuer, subject)
    if row is not None:
        if row.issuer is not None and (row.issuer != issuer or row.subject != subject):
            raise IdentityResolutionError("autorizacao_de_outra_conta")
        return row
    expired = session.scalar(
        select(OnboardingAuthorization.id).where(
            OnboardingAuthorization.email_normalized == email_key,
            OnboardingAuthorization.status.in_(("issued", "bound")),
            OnboardingAuthorization.expires_at <= func.now(),
        )
    )
    if expired is not None:
        raise IdentityResolutionError("autorizacao_expirada")
    used = session.scalar(
        select(OnboardingAuthorization.id).where(
            OnboardingAuthorization.email_normalized == email_key,
            OnboardingAuthorization.status == "consumed",
        )
    )
    if used is not None:
        raise IdentityResolutionError("autorizacao_usada")
    raise IdentityResolutionError("sem_autorizacao")


def _open_authorization(session: Session, email_key: str | None, issuer: str, subject: str):
    identity_match = and_(
        OnboardingAuthorization.issuer == issuer,
        OnboardingAuthorization.subject == subject,
    )
    if email_key:
        match = or_(
            identity_match,
            and_(
                OnboardingAuthorization.issuer.is_(None),
                OnboardingAuthorization.email_normalized == email_key,
            ),
        )
    else:
        match = identity_match
    return session.scalar(
        select(OnboardingAuthorization)
        .where(
            match,
            OnboardingAuthorization.status.in_(("issued", "bound")),
            OnboardingAuthorization.expires_at > func.now(),
            OnboardingAuthorization.clients_created < OnboardingAuthorization.max_clients,
        )
        .with_for_update()
    )


def _closed_access(session: Session, email_key: str | None) -> str:
    if not email_key:
        return "sem_autorizacao"
    row = session.scalar(
        select(OnboardingAuthorization)
        .where(OnboardingAuthorization.email_normalized == email_key)
        .order_by(OnboardingAuthorization.created_at.desc())
    )
    if row is None:
        return "sem_autorizacao"
    if row.status == "consumed" or row.clients_created >= row.max_clients:
        return "autorizacao_usada"
    if row.status in {"issued", "bound"} and row.expires_at <= datetime.now(UTC):
        return "autorizacao_expirada"
    if row.issuer is not None and row.subject is not None:
        return "autorizacao_de_outra_conta"
    return "sem_autorizacao"


def _pending_invite(session: Session, email_key: str | None) -> OrganizationInvitation | None:
    if not email_key:
        return None
    return session.scalar(
        select(OrganizationInvitation).where(
            OrganizationInvitation.email_normalized == email_key,
            OrganizationInvitation.status == "pending",
            OrganizationInvitation.expires_at > func.now(),
        )
    )


def _identity(session: Session, issuer: str, subject: str) -> AuthIdentity | None:
    return session.scalar(
        select(AuthIdentity).where(
            AuthIdentity.issuer == issuer,
            AuthIdentity.subject == subject,
            AuthIdentity.status == "active",
        )
    )


def _context(session, token, email_key, organization_id, user_id) -> None:
    apply_tenant_context(
        session,
        organization_id=organization_id,
        user_id=user_id,
        issuer=token.issuer,
        subject=token.subject,
        actor_email=email_key,
    )


def _token(issuer: str, subject: str, email_key: str) -> VerifiedAccessToken:
    return VerifiedAccessToken(
        issuer=issuer,
        subject=subject,
        client_id=None,
        scopes=frozenset(),
        raw_claims={"email": email_key},
    )


def _lock(session: Session, email_key: str, issuer: str, subject: str, slug: str) -> None:
    for key in (f"email:{email_key}", f"identity:{issuer}|{subject}", f"slug:{slug}"):
        session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key})


def _text(value: str | None, reason: str) -> str:
    text_value = (value or "").strip()
    if not text_value:
        raise IdentityResolutionError(reason)
    return text_value


def _email(value: str) -> str:
    email = _text(value, "email_invalido").lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise IdentityResolutionError("email_invalido")
    return email


def _code(value: str, reason: str) -> str:
    code = _text(value, reason).lower()
    if not _CODE.fullmatch(code) or not 2 <= len(code) <= 48:
        raise IdentityResolutionError(reason)
    return code


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def _holder(kind: str, state: str, legal_name: str | None, fiscal_id: str):
    digits = _digits(fiscal_id)
    if kind == "legal_entity":
        if state != "formalized":
            raise IdentityResolutionError("formalizacao_invalida")
        legal = _text(legal_name, "formalizacao_invalida")
        if len(digits) != 14 or len(set(digits)) == 1:
            raise IdentityResolutionError("identificador_invalido")
        return "cnpj", digits, legal, "formalized"
    if kind == "natural_person":
        if state not in {"not_formalized", "self_employed"} or (legal_name or "").strip():
            raise IdentityResolutionError("formalizacao_invalida")
        if len(digits) != 11 or len(set(digits)) == 1:
            raise IdentityResolutionError("identificador_invalido")
        return "cpf", digits, None, state
    raise IdentityResolutionError("titular_invalido")


def _place(nature: str, capabilities) -> tuple[str, tuple[str, ...]]:
    if nature not in {"integrated", "specialized"}:
        raise IdentityResolutionError("estabelecimento_invalido")
    chosen = tuple(dict.fromkeys(capabilities))
    if not chosen or any(item not in _CAPABILITIES for item in chosen):
        raise IdentityResolutionError("capacidade_invalida")
    return nature, chosen
