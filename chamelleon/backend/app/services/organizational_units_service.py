"""CRUD de unidades organizacionais (filiais/escritórios/depósitos)."""

from __future__ import annotations

import uuid
from typing import Any

from flask import g

from app.database.models import db
from app.models.organization_models import ORGANIZATIONAL_UNIT_TYPES, OrganizationalUnit


class OrganizationalUnitsService:
    def _tenant_id(self) -> uuid.UUID:
        tenant_id = getattr(g, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("Contexto de tenant obrigatório.")
        return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))

    def list_units(self, *, active_only: bool = False) -> list[dict[str, Any]]:
        query = OrganizationalUnit.query.filter_by(tenant_id=self._tenant_id())
        if active_only:
            query = query.filter_by(is_active=True)
        return [u.to_dict() for u in query.order_by(OrganizationalUnit.name.asc()).all()]

    def create_unit(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Campo obrigatório: name.")
        unit_type = str(payload.get("unit_type") or "Filial").strip()
        if unit_type not in ORGANIZATIONAL_UNIT_TYPES:
            raise ValueError(
                f"unit_type inválido. Use um de: {', '.join(ORGANIZATIONAL_UNIT_TYPES)}"
            )
        email = str(payload.get("responsible_email") or "").strip() or None
        if email and "@" not in email:
            raise ValueError("E-mail do responsável inválido.")

        unit = OrganizationalUnit(
            tenant_id=self._tenant_id(),
            name=name,
            unit_type=unit_type,
            address=str(payload.get("address") or "").strip() or None,
            responsible_name=str(payload.get("responsible_name") or "").strip() or None,
            responsible_email=email,
            responsible_phone=str(payload.get("responsible_phone") or "").strip() or None,
        )
        db.session.add(unit)
        db.session.commit()
        return unit.to_dict()

    def update_unit(self, unit_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        unit = self._get_unit_or_404(unit_id)
        if "name" in payload:
            name = str(payload.get("name") or "").strip()
            if not name:
                raise ValueError("name não pode ser vazio.")
            unit.name = name
        if "unit_type" in payload:
            unit_type = str(payload.get("unit_type") or "").strip()
            if unit_type not in ORGANIZATIONAL_UNIT_TYPES:
                raise ValueError(
                    f"unit_type inválido. Use um de: {', '.join(ORGANIZATIONAL_UNIT_TYPES)}"
                )
            unit.unit_type = unit_type
        if "address" in payload:
            unit.address = str(payload.get("address") or "").strip() or None
        if "responsible_name" in payload:
            unit.responsible_name = str(payload.get("responsible_name") or "").strip() or None
        if "responsible_email" in payload:
            email = str(payload.get("responsible_email") or "").strip() or None
            if email and "@" not in email:
                raise ValueError("E-mail do responsável inválido.")
            unit.responsible_email = email
        if "responsible_phone" in payload:
            unit.responsible_phone = str(payload.get("responsible_phone") or "").strip() or None
        if "is_active" in payload:
            unit.is_active = bool(payload.get("is_active"))
        db.session.commit()
        return unit.to_dict()

    def deactivate_unit(self, unit_id: str) -> dict[str, Any]:
        unit = self._get_unit_or_404(unit_id)
        unit.is_active = False
        db.session.commit()
        return unit.to_dict()

    def _get_unit_or_404(self, unit_id: str) -> OrganizationalUnit:
        try:
            uid = uuid.UUID(str(unit_id))
        except (TypeError, ValueError) as exc:
            raise ValueError("unit_id inválido.") from exc
        unit = OrganizationalUnit.query.filter_by(
            id=uid, tenant_id=self._tenant_id()
        ).first()
        if not unit:
            raise ValueError("Unidade organizacional não encontrada.")
        return unit
