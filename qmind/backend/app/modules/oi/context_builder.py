"""Map Core Organization Profile facts → OrganizationContextInput (OI-001).

No inference beyond copying stored profile fields.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from app.modules.oi.schemas import (
    SCHEMA_VERSION_V1,
    EnvelopeMetadata,
    OrganizationContextInput,
    OrganizationContextPayload,
    OrganizationProfileFacts,
    SourceRef,
)
from app.modules.orgs.schemas import OrganizationProfileOut
from app.openapi_contract import API_VERSION

_Env = Literal["local", "test", "homolog", "prod"]


def build_organization_context_input(
    profile: OrganizationProfileOut,
    *,
    core_organization_id: UUID,
    request_id: str | None = None,
    correlation_id: str | None = None,
    occurred_at: datetime | None = None,
    environment: str | None = None,
) -> OrganizationContextInput:
    """
    Build the Core→OI envelope from the persistent Organization Profile.

    ``core_organization_id`` must come from OrgContext — never from the client body.
    """
    rid = request_id or str(uuid4())
    cid = correlation_id or rid
    when = occurred_at or datetime.now(UTC)

    facts = OrganizationProfileFacts(
        trade_name=profile.trade_name,
        legal_name=profile.legal_name,
        summary=profile.summary,
        industry=profile.industry,
        business_model=profile.business_model,
        employee_range=profile.employee_range,
        unit_count=profile.unit_count,
        certification_status=profile.certification_status,
        quality_structure=profile.quality_structure,
    )

    env_meta: _Env | None = environment if environment in ("local", "test", "homolog", "prod") else None

    return OrganizationContextInput(
        schema_version=SCHEMA_VERSION_V1,
        core_organization_id=core_organization_id,
        request_id=rid,
        correlation_id=cid,
        occurred_at=when,
        source=SourceRef(system="qmind-core", component="organizational-intelligence"),
        context=OrganizationContextPayload(organization=None, profile=facts),
        metadata=EnvelopeMetadata(
            producer_version=API_VERSION,
            environment=env_meta,
        ),
    )
