"""Persistência das diretrizes operacionais vindas do Chamelleon."""

from __future__ import annotations

import uuid
from typing import Any

from app.extensions import db
from app.models import ProjectDirectives


class DirectiveService:
    def upsert_framework_directives(self, payload: dict[str, Any]) -> ProjectDirectives:
        tenant_id = str(payload.get("tenant_id") or "").strip()
        if not tenant_id:
            raise ValueError("Campo obrigatório: tenant_id.")
        project_id = self._as_uuid(payload.get("project_id"), "project_id")
        framework_id = str(payload.get("framework_id") or "").strip()
        if not framework_id:
            raise ValueError("Campo obrigatório: framework_id.")

        building_blocks = payload.get("building_blocks")
        if building_blocks is None:
            building_blocks = payload.get("directives") or payload.get("rules")
        if building_blocks is None:
            raise ValueError("Campo obrigatório: building_blocks (ou directives).")

        directives_body = {
            "building_blocks": building_blocks,
            "metadata": payload.get("metadata") or {},
            "gemba_focus": payload.get("gemba_focus"),
            "sector": payload.get("sector"),
        }

        existing = (
            ProjectDirectives.query.filter_by(
                tenant_id=tenant_id,
                project_id=project_id,
                framework_id=framework_id,
            )
            .order_by(ProjectDirectives.received_at.desc())
            .first()
        )

        if existing:
            existing.framework_version = payload.get("framework_version")
            existing.directives_payload = directives_body
            existing.source_system = str(payload.get("source_system") or "chamelleon")
            record = existing
        else:
            record = ProjectDirectives(
                tenant_id=tenant_id,
                project_id=project_id,
                framework_id=framework_id,
                framework_version=payload.get("framework_version"),
                source_system=str(payload.get("source_system") or "chamelleon"),
                directives_payload=directives_body,
            )
            db.session.add(record)

        db.session.commit()
        return record

    @staticmethod
    def _as_uuid(value: Any, field_name: str) -> uuid.UUID:
        if value is None:
            raise ValueError(f"Campo obrigatório ausente: {field_name}.")
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"UUID inválido em '{field_name}': {value}") from exc
