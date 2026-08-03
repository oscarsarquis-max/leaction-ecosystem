"""Platform audit append-only helper (domain-docs-v0)."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection


def write_audit(
    conn: Connection,
    *,
    organization_id: UUID | None,
    actor_type: str,
    action: str,
    resource_type: str,
    resource_id: UUID,
    result: str = "success",
    actor_user_id: UUID | None = None,
    actor_membership_id: UUID | None = None,
    actor_service_id: str | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
    metadata: dict[str, Any] | None = None,
    correlation_id: UUID | None = None,
) -> UUID:
    event_id = uuid4()
    corr = correlation_id or uuid4()
    conn.execute(
        text(
            """
            INSERT INTO platform_audit_events (
              id, organization_id, actor_type, actor_user_id, actor_membership_id,
              actor_service_id, action, resource_type, resource_id,
              from_status, to_status, correlation_id, result, metadata
            ) VALUES (
              :id, :org, :actor_type, :actor_user, :actor_mem,
              :actor_svc, :action, :rtype, :rid,
              :from_s, :to_s, :corr, :result, CAST(:meta AS jsonb)
            )
            """
        ),
        {
            "id": event_id,
            "org": organization_id,
            "actor_type": actor_type,
            "actor_user": actor_user_id,
            "actor_mem": actor_membership_id,
            "actor_svc": actor_service_id,
            "action": action,
            "rtype": resource_type,
            "rid": resource_id,
            "from_s": from_status,
            "to_s": to_status,
            "corr": corr,
            "result": result,
            "meta": __import__("json").dumps(metadata or {}),
        },
    )
    return event_id
