"""Gestão global de utilizadores — espelho do PanelDX /admin/usuarios."""

from __future__ import annotations

import os
import uuid
from typing import Any

from sqlalchemy import func, or_
from werkzeug.security import generate_password_hash

from app.core.dev_users import DEV_TEAM_TENANT_ID
from app.core.rbac.constants import ROLE_LABELS, ROLE_LED, SYSTEM_ROLES
from app.database.models import LeadAccess, Tenant, TenantFramework, TenantUser, User, db
from app.infrastructure.email_service import dispatch_access_code_email
from app.services.lead_auth_service import LeadAuthService

_DEV_PASSWORD_HINTS = {
    "executor@paneldx.com.br": "PanelDX1!",
    "sysadmin@leaction.com.br": "LeAction1!",
}


class AdminUsersService:
    def list_users(
        self,
        *,
        search: str | None = None,
        system_role: str | None = None,
        tenant_id: str | None = None,
        include_inactive: bool = True,
    ) -> list[dict[str, Any]]:
        query = User.query.order_by(User.name.asc())

        if not include_inactive:
            query = query.filter(User.is_active.is_(True))

        if search and len(search.strip()) >= 2:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(User.name.ilike(term), User.email.ilike(term))
            )

        users = query.all()
        results: list[dict[str, Any]] = []

        for user in users:
            memberships = (
                TenantUser.query.join(Tenant, TenantUser.tenant_id == Tenant.id)
                .filter(TenantUser.user_id == user.id)
                .all()
            )
            if system_role:
                if not any(m.role == system_role for m in memberships):
                    continue
            if tenant_id:
                tid = uuid.UUID(str(tenant_id))
                if not any(m.tenant_id == tid for m in memberships):
                    continue

            primary = self._pick_primary_membership(memberships)
            tenant = db.session.get(Tenant, primary.tenant_id) if primary else None
            lead_access = (
                LeadAccess.query.filter_by(user_id=user.id)
                .order_by(LeadAccess.created_at.desc())
                .first()
            )

            results.append(
                {
                    "user_id": str(user.id),
                    "name": user.name,
                    "email": user.email,
                    "system_role": primary.role if primary else None,
                    "role_label": ROLE_LABELS.get(primary.role, primary.role) if primary else None,
                    "is_active": user.is_active,
                    "tenant_id": str(primary.tenant_id) if primary else None,
                    "tenant_name": tenant.name if tenant else None,
                    "operational_site_id": str(primary.operational_site_id)
                    if primary and primary.operational_site_id
                    else None,
                    "has_password": bool(user.password_hash),
                    "has_lead_access": lead_access is not None,
                    "access_code": lead_access.access_code if lead_access else None,
                    "memberships": [
                        {
                            "tenant_id": str(m.tenant_id),
                            "tenant_name": db.session.get(Tenant, m.tenant_id).name
                            if db.session.get(Tenant, m.tenant_id)
                            else None,
                            "role": m.role,
                            "role_label": ROLE_LABELS.get(m.role, m.role),
                        }
                        for m in memberships
                    ],
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                }
            )

        return results

    def list_tenant_options(self) -> list[dict[str, Any]]:
        tenants = Tenant.query.order_by(Tenant.name.asc()).all()
        return [
            {"tenant_id": str(t.id), "name": t.name, "document": t.document}
            for t in tenants
        ]

    def get_user_access(self, user_id: uuid.UUID | str) -> dict[str, Any]:
        user_uuid = self._as_uuid(user_id)
        user = db.session.get(User, user_uuid)
        if not user:
            raise ValueError("Utilizador não encontrado.")

        lead_access = (
            LeadAccess.query.filter_by(user_id=user.id)
            .order_by(LeadAccess.created_at.desc())
            .first()
        )
        dev_password = _DEV_PASSWORD_HINTS.get(user.email.lower()) if self._is_local_dev() else None

        return {
            "user_id": str(user.id),
            "email": user.email,
            "auth_type": "lead" if lead_access and not user.password_hash else (
                "team" if user.password_hash else "none"
            ),
            "access_code": lead_access.access_code if lead_access else None,
            "dev_password_hint": dev_password,
            "has_password": bool(user.password_hash),
        }

    def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = (payload.get("name") or "").strip()
        email = (payload.get("email") or "").lower().strip()
        system_role = (payload.get("system_role") or "").strip().lower()
        password = payload.get("password") or payload.get("senha")
        tenant_id_raw = payload.get("tenant_id")

        if not name or not email or not system_role:
            raise ValueError("Campos obrigatórios: name, email, system_role.")
        if system_role not in SYSTEM_ROLES:
            raise ValueError("Papel inválido (sysadmin, led, consultor, executor).")

        if User.query.filter(func.lower(User.email) == email).first():
            raise ValueError("E-mail já cadastrado.")

        tenant_id = self._resolve_tenant_id(system_role, tenant_id_raw)
        site_id = self._optional_site_id(
            payload.get("site_id") or payload.get("operational_site_id"),
            tenant_id=tenant_id,
        )

        user = User(name=name, email=email, is_active=True)
        if system_role != ROLE_LED:
            if not password:
                raise ValueError("Senha é obrigatória para perfis de equipe.")
            user.password_hash = generate_password_hash(str(password))

        db.session.add(user)
        db.session.flush()

        db.session.add(TenantUser(
            tenant_id=tenant_id, user_id=user.id, role=system_role, operational_site_id=site_id
        ))

        if system_role == ROLE_LED:
            if not TenantFramework.query.filter_by(tenant_id=tenant_id, status="active").first():
                raise ValueError("Tenant sem framework ativo. Vincule um setor ao cliente.")
            access_code = LeadAuthService._generate_access_code()
            db.session.add(
                LeadAccess(tenant_id=tenant_id, user_id=user.id, access_code=access_code)
            )
            db.session.commit()
            dispatch_access_code_email(email, access_code)
            return {
                "user_id": str(user.id),
                "message": f"Utilizador lead criado. Código enviado para {email}.",
                "access_code": access_code if self._is_local_dev() else None,
            }

        db.session.commit()
        return {"user_id": str(user.id), "message": "Utilizador criado com sucesso."}

    def update_user(self, user_id: uuid.UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        user_uuid = self._as_uuid(user_id)
        user = db.session.get(User, user_uuid)
        if not user:
            raise ValueError("Utilizador não encontrado.")

        if "name" in payload and payload["name"]:
            user.name = str(payload["name"]).strip()
        if "email" in payload and payload["email"]:
            email = str(payload["email"]).lower().strip()
            existing = User.query.filter(func.lower(User.email) == email).first()
            if existing and existing.id != user.id:
                raise ValueError("E-mail já utilizado por outro utilizador.")
            user.email = email
        if "is_active" in payload:
            user.is_active = bool(payload["is_active"])

        password = payload.get("password") or payload.get("senha")
        if password:
            user.password_hash = generate_password_hash(str(password))

        system_role = payload.get("system_role")
        tenant_id_raw = payload.get("tenant_id")
        membership = TenantUser.query.filter_by(user_id=user.id).first()
        if system_role:
            system_role = str(system_role).strip().lower()
            if system_role not in SYSTEM_ROLES:
                raise ValueError("Papel inválido.")
            tenant_id = self._resolve_tenant_id(system_role, tenant_id_raw or payload.get("tenant_id"))
            if membership:
                membership.role = system_role
                membership.tenant_id = tenant_id
            else:
                membership = TenantUser(tenant_id=tenant_id, user_id=user.id, role=system_role)
                db.session.add(membership)

        if "site_id" in payload or "operational_site_id" in payload:
            if not membership:
                membership = TenantUser.query.filter_by(user_id=user.id).first()
            if membership:
                membership.operational_site_id = self._optional_site_id(
                    payload.get("site_id") or payload.get("operational_site_id"),
                    tenant_id=membership.tenant_id,
                )

        db.session.commit()
        return {"user_id": str(user.id), "message": "Utilizador atualizado."}

    def deactivate_user(self, user_id: uuid.UUID | str) -> dict[str, Any]:
        user_uuid = self._as_uuid(user_id)
        user = db.session.get(User, user_uuid)
        if not user:
            raise ValueError("Utilizador não encontrado.")
        user.is_active = False
        db.session.commit()
        return {"user_id": str(user.id), "message": "Utilizador desativado."}

    def regenerate_lead_code(self, user_id: uuid.UUID | str) -> dict[str, Any]:
        user_uuid = self._as_uuid(user_id)
        user = db.session.get(User, user_uuid)
        if not user:
            raise ValueError("Utilizador não encontrado.")
        lead_access = LeadAccess.query.filter_by(user_id=user.id).first()
        if not lead_access:
            raise ValueError("Utilizador sem código LA-*.")
        lead_access.access_code = LeadAuthService._generate_access_code()
        db.session.commit()
        dispatch_access_code_email(user.email, lead_access.access_code)
        result = {"message": f"Novo código enviado para {user.email}."}
        if self._is_local_dev():
            result["access_code"] = lead_access.access_code
        return result

    @staticmethod
    def _pick_primary_membership(memberships: list[TenantUser]) -> TenantUser | None:
        if not memberships:
            return None
        priority = {"sysadmin": 0, "consultor": 1, "executor": 2, "led": 3}
        return sorted(memberships, key=lambda m: priority.get(m.role, 99))[0]

    @staticmethod
    def _resolve_tenant_id(system_role: str, tenant_id_raw: Any) -> uuid.UUID:
        if tenant_id_raw:
            return AdminUsersService._as_uuid(tenant_id_raw, "tenant_id")
        if system_role in ("sysadmin", "consultor", "executor"):
            return DEV_TEAM_TENANT_ID
        raise ValueError("tenant_id é obrigatório para perfil lead.")

    @staticmethod
    def _as_uuid(value: Any, field_name: str = "id") -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"UUID inválido em '{field_name}'.") from exc

    @staticmethod
    def _optional_site_id(value: Any, tenant_id: uuid.UUID | None = None) -> uuid.UUID | None:
        if value in (None, ""):
            return None
        try:
            site_uuid = uuid.UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError("operational_site_id inválido.") from exc

        from app.models.operational_models import OperationalSite

        query = OperationalSite.query.filter_by(id=site_uuid, is_active=True)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        if not query.first():
            raise ValueError("Unidade operacional inválida.")
        return site_uuid

    @staticmethod
    def _is_local_dev() -> bool:
        return os.getenv("FLASK_DEBUG", "1") == "1"
