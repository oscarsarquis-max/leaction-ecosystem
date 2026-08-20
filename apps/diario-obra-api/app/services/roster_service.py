"""Recebe o roster qualificado (Engenheiro/Mestre de Obras) empurrado pelo Chamelleon."""
from __future__ import annotations

from typing import Any

from app.extensions import db
from app.models import ProjectRosterMember, ProjectSite
from app.services.rdo_service import RdoService


class RosterService:
    def upsert_roster(self, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = str(payload.get("tenant_id") or "").strip()
        project_id_raw = payload.get("project_id")
        roster = payload.get("roster") or []

        if not tenant_id:
            raise ValueError("Campo obrigatório: tenant_id.")
        if not project_id_raw:
            raise ValueError("Campo obrigatório: project_id.")
        if not isinstance(roster, list):
            raise ValueError("'roster' deve ser uma lista.")

        project_uuid = RdoService._as_uuid(project_id_raw, "project_id")
        site = db.session.get(ProjectSite, project_uuid)
        if not site or site.tenant_id != tenant_id:
            raise ValueError("Canteiro (project_id) não encontrado para o tenant.")

        incoming_ids: set[str] = set()
        for item in roster:
            if not isinstance(item, dict):
                continue
            source_id = str(item.get("id") or "").strip()
            name = str(item.get("name") or "").strip()
            if not source_id or not name:
                continue
            incoming_ids.add(source_id)

            member = ProjectRosterMember.query.filter_by(
                project_id=project_uuid, source_professional_id=source_id
            ).first()
            if member:
                member.name = name
                member.role = item.get("role")
                member.is_active = True
            else:
                db.session.add(
                    ProjectRosterMember(
                        project_id=project_uuid,
                        source_professional_id=source_id,
                        name=name,
                        role=item.get("role"),
                        is_active=True,
                    )
                )

        # Quem não veio na lista nova foi removido/desqualificado no hub — desativa, não apaga
        # (preserva histórico de quem assinou RDOs antigos com esse nome).
        stale_query = ProjectRosterMember.query.filter_by(project_id=project_uuid)
        if incoming_ids:
            stale_query = stale_query.filter(
                ~ProjectRosterMember.source_professional_id.in_(incoming_ids)
            )
        for member in stale_query.all():
            member.is_active = False

        db.session.commit()
        return {"project_id": str(project_uuid), "roster_count": len(incoming_ids)}
