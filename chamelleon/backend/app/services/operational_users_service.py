"""Gestão de utilizadores no escopo do tenant — organização operacional."""

from __future__ import annotations

import os
import uuid
from typing import Any

from flask import g
from sqlalchemy import func
from werkzeug.security import generate_password_hash

from app.core.rbac.constants import (
    ROLE_CONSULTOR,
    ROLE_EXECUTOR,
    ROLE_LABELS,
    ROLE_LED,
    SYSTEM_ROLES,
)
from app.database.models import LeadAccess, TenantUser, User, db
from app.infrastructure.email_service import dispatch_access_code_email
from app.models.operational_models import OperationalSite as OpSiteModel
from app.services.lead_auth_service import LeadAuthService


class OperationalUsersService:
    def list_users(self) -> list[dict[str, Any]]:
        tenant_id = g.tenant_id
        memberships = (
            TenantUser.query.filter_by(tenant_id=tenant_id)
            .join(User, TenantUser.user_id == User.id)
            .order_by(User.name.asc())
            .all()
        )
        site_map = {
            str(site.id): site.name
            for site in OpSiteModel.query.filter_by(tenant_id=tenant_id, is_active=True).all()
        }
        results: list[dict[str, Any]] = []
        for membership in memberships:
            user = membership.user
            lead_access = (
                LeadAccess.query.filter_by(user_id=user.id, tenant_id=tenant_id)
                .order_by(LeadAccess.created_at.desc())
                .first()
            )
            site_id = (
                str(membership.operational_site_id) if membership.operational_site_id else None
            )
            results.append(
                {
                    "user_id": str(user.id),
                    "name": user.name,
                    "email": user.email,
                    "system_role": membership.role,
                    "role_label": ROLE_LABELS.get(membership.role, membership.role),
                    "is_active": user.is_active,
                    "operational_site_id": site_id,
                    "operational_site_name": site_map.get(site_id or "", None),
                    "access_code": lead_access.access_code if lead_access else None,
                    "has_password": bool(user.password_hash),
                }
            )
        return results

    def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = g.tenant_id
        name = (payload.get("name") or "").strip()
        email = (payload.get("email") or "").lower().strip()
        system_role = (payload.get("system_role") or ROLE_EXECUTOR).strip().lower()
        password = payload.get("password") or payload.get("senha")
        site_id = self._optional_site_id(payload.get("site_id") or payload.get("operational_site_id"))

        if not name or not email:
            raise ValueError("Campos obrigatórios: name, email.")
        if system_role not in (ROLE_LED, ROLE_EXECUTOR, ROLE_CONSULTOR):
            raise ValueError("Papel inválido para gestão operacional (led, consultor, executor).")

        if User.query.filter(func.lower(User.email) == email).first():
            raise ValueError("E-mail já cadastrado.")

        user = User(name=name, email=email, is_active=True)
        if system_role != ROLE_LED:
            if not password:
                raise ValueError("Senha é obrigatória para executor e consultor.")
            user.password_hash = generate_password_hash(str(password))

        db.session.add(user)
        db.session.flush()
        db.session.add(
            TenantUser(
                tenant_id=tenant_id,
                user_id=user.id,
                role=system_role,
                operational_site_id=site_id,
            )
        )

        if system_role == ROLE_LED:
            access_code = LeadAuthService._generate_access_code()
            db.session.add(
                LeadAccess(tenant_id=tenant_id, user_id=user.id, access_code=access_code)
            )
            db.session.commit()
            dispatch_access_code_email(email, access_code)
            return {
                "user_id": str(user.id),
                "message": f"Lead criado. Código enviado para {email}.",
                "access_code": access_code if self._is_local_dev() else None,
            }

        db.session.commit()
        return {"user_id": str(user.id), "message": "Utilizador criado com sucesso."}

    def update_user(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = g.tenant_id
        user_uuid = self._as_uuid(user_id)
        membership = TenantUser.query.filter_by(tenant_id=tenant_id, user_id=user_uuid).first()
        if not membership:
            raise ValueError("Utilizador não encontrado neste tenant.")

        user = db.session.get(User, user_uuid)
        if not user:
            raise ValueError("Utilizador não encontrado.")

        if "name" in payload and payload["name"]:
            user.name = str(payload["name"]).strip()
        if "email" in payload and payload["email"]:
            email = str(payload["email"]).lower().strip()
            existing = User.query.filter(func.lower(User.email) == email).first()
            if existing and existing.id != user.id:
                raise ValueError("E-mail já utilizado.")
            user.email = email
        if "is_active" in payload:
            user.is_active = bool(payload["is_active"])
        if "system_role" in payload and payload["system_role"]:
            role = str(payload["system_role"]).strip().lower()
            if role not in SYSTEM_ROLES:
                raise ValueError("Papel inválido.")
            membership.role = role
        if "site_id" in payload or "operational_site_id" in payload:
            membership.operational_site_id = self._optional_site_id(
                payload.get("site_id") or payload.get("operational_site_id")
            )

        password = payload.get("password") or payload.get("senha")
        if password:
            user.password_hash = generate_password_hash(str(password))

        db.session.commit()
        return {"user_id": str(user.id), "message": "Utilizador atualizado."}

    def regenerate_lead_code(self, user_id: str) -> dict[str, Any]:
        tenant_id = g.tenant_id
        user_uuid = self._as_uuid(user_id)
        membership = TenantUser.query.filter_by(tenant_id=tenant_id, user_id=user_uuid).first()
        if not membership or membership.role != ROLE_LED:
            raise ValueError("Utilizador lead não encontrado.")
        user = db.session.get(User, user_uuid)
        if not user:
            raise ValueError("Utilizador não encontrado.")
        lead_access = LeadAccess.query.filter_by(user_id=user.id, tenant_id=tenant_id).first()
        if not lead_access:
            raise ValueError("Utilizador sem código LA-*.")
        lead_access.access_code = LeadAuthService._generate_access_code()
        db.session.commit()
        dispatch_access_code_email(user.email, lead_access.access_code)
        result = {"message": f"Novo código enviado para {user.email}."}
        if self._is_local_dev():
            result["access_code"] = lead_access.access_code
        return result

    def _optional_site_id(self, value: Any) -> uuid.UUID | None:
        if value in (None, ""):
            return None
        site_uuid = self._as_uuid(value)
        site = OpSiteModel.query.filter_by(id=site_uuid, tenant_id=g.tenant_id).first()
        if not site:
            raise ValueError("Unidade operacional inválida.")
        return site_uuid

    @staticmethod
    def _as_uuid(value: Any) -> uuid.UUID:
        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError("UUID inválido.") from exc

    @staticmethod
    def _is_local_dev() -> bool:
        return os.getenv("FLASK_DEBUG", "1") == "1"
