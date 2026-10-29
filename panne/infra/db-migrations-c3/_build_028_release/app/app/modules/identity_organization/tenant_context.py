"""Contexto organizacional local à transação. Sem persistência na sessão do pool."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

ORG_SETTING = "app.current_organization_id"
USER_SETTING = "app.current_user_id"
ISSUER_SETTING = "app.current_issuer"
SUBJECT_SETTING = "app.current_subject"


def _values(
    organization_id: UUID | None,
    user_id: UUID | None,
    issuer: str | None = None,
    subject: str | None = None,
) -> dict[str, str]:
    return {
        ORG_SETTING: "" if organization_id is None else str(organization_id),
        USER_SETTING: "" if user_id is None else str(user_id),
        ISSUER_SETTING: issuer or "",
        SUBJECT_SETTING: subject or "",
    }


def apply_tenant_context(
    session: Session,
    *,
    organization_id: UUID | None,
    user_id: UUID | None,
    issuer: str | None = None,
    subject: str | None = None,
) -> None:
    statement = text("SELECT set_config(:key, :value, true)")
    for key, value in _values(organization_id, user_id, issuer, subject).items():
        session.execute(statement, {"key": key, "value": value})


async def apply_tenant_context_async(
    session: AsyncSession,
    *,
    organization_id: UUID | None,
    user_id: UUID | None,
    issuer: str | None = None,
    subject: str | None = None,
) -> None:
    statement = text("SELECT set_config(:key, :value, true)")
    for key, value in _values(organization_id, user_id, issuer, subject).items():
        await session.execute(statement, {"key": key, "value": value})
