"""Cadastro e login de leads — fluxo LA-* por e-mail."""

from __future__ import annotations

import os
import re
import secrets
import string
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from app.core.dev_users import DEV_FRAMEWORK_CONSTRUCAO_ID, DEV_FRAMEWORK_ID, EMAIL_EXECUTOR_TEST, EMAIL_LEAD_TEST, EMAIL_SYSADMIN
from app.core.rbac.constants import ROLE_LED, ROLE_SYSADMIN, SYSTEM_ROLES
from app.core.tenant_framework_resolver import resolve_framework_for_tenant
from app.database.models import (
    AssessmentSubmission,
    Framework,
    LeadAccess,
    Tenant,
    TenantFramework,
    TenantUser,
    User,
    db,
)
from app.infrastructure.email_service import dispatch_access_code_email

_PROTECTED_RESET_EMAILS = {
    EMAIL_SYSADMIN.lower(),
    EMAIL_EXECUTOR_TEST.lower(),
    EMAIL_LEAD_TEST.lower(),
}


class LeadAuthService:
    def list_sectors(self) -> list[dict[str, Any]]:
        """Setores disponíveis = frameworks publicados/ativos."""
        frameworks = (
            Framework.query.filter_by(is_active=True)
            .order_by(Framework.industry.asc(), Framework.name.asc())
            .all()
        )
        frameworks.sort(key=lambda fw: (0 if fw.id == DEV_FRAMEWORK_ID else 1, fw.industry or ""))
        return [
            {
                "framework_id": fw.id,
                "name": fw.name,
                "industry": fw.industry,
                "version": fw.version,
                "label": self._sector_label(fw),
            }
            for fw in frameworks
        ]

    def register_lead(
        self,
        *,
        name: str,
        email: str,
        company_name: str,
        framework_id: str,
        document: str | None = None,
    ) -> dict[str, Any]:
        name = (name or "").strip()
        email = (email or "").lower().strip()
        company_name = (company_name or "").strip()
        framework_id = (framework_id or "").strip()

        if not name or not email or not company_name or not framework_id:
            raise ValueError("Campos obrigatórios: name, email, company_name, framework_id.")

        framework = db.session.get(Framework, framework_id)
        if not framework or not framework.is_active:
            raise ValueError("Setor/framework inválido ou indisponível.")

        existing_user = User.query.filter(func.lower(User.email) == email).first()
        if existing_user:
            if self._is_orphan_user(existing_user):
                db.session.delete(existing_user)
                db.session.flush()
            else:
                return self._handle_existing_registration(existing_user, email)

        document_value = self._normalize_document(document)
        if document_value and self._document_is_taken(document_value):
            raise ValueError(
                "CNPJ/documento já cadastrado. Utilize outro documento ou deixe o campo em branco."
            )

        tenant = Tenant(
            name=company_name,
            document=document_value,
        )
        db.session.add(tenant)
        db.session.flush()

        user = User(name=name, email=email)
        db.session.add(user)
        db.session.flush()

        db.session.add(TenantUser(tenant_id=tenant.id, user_id=user.id, role=ROLE_LED))
        db.session.add(
            TenantFramework(tenant_id=tenant.id, framework_id=framework.id, status="active")
        )

        access_code = self._generate_access_code()
        db.session.add(
            LeadAccess(
                tenant_id=tenant.id,
                user_id=user.id,
                access_code=access_code,
            )
        )
        try:
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            raise self._integrity_error_to_value_error(exc) from exc

        dispatch_access_code_email(email, access_code)

        return self._with_dev_access_code(
            {
                "status": "created",
                "message": (
                    f"Cadastro realizado! Enviamos o código de acesso para {email}. "
                    f"Setor: {self._sector_label(framework)}."
                ),
                "tenant_id": str(tenant.id),
                "user_id": str(user.id),
                "framework_id": framework.id,
                "email_sent": True,
            },
            access_code,
        )

    def resend_access_code(self, email: str) -> dict[str, Any]:
        """Gera novo código LA-* e reenvia e-mail para lead já cadastrado."""
        email = (email or "").lower().strip()
        if not email:
            raise ValueError("Informe o e-mail.")

        user = User.query.filter(func.lower(User.email) == email).first()
        if not user:
            raise ValueError("E-mail não encontrado. Faça o cadastro primeiro.")

        lead_access = self._ensure_lead_access_for_user(user)
        lead_access.access_code = self._generate_access_code()
        db.session.commit()

        dispatch_access_code_email(email, lead_access.access_code)

        return self._with_dev_access_code(
            {
                "status": "resent",
                "message": f"Enviamos um novo código de acesso para {email}.",
                "tenant_id": str(lead_access.tenant_id),
                "user_id": str(user.id),
                "email_sent": True,
            },
            lead_access.access_code,
        )

    def reset_lead_registration(self, email: str) -> dict[str, Any]:
        """Remove cadastro lead para permitir novo registro (somente desenvolvimento)."""
        if os.getenv("FLASK_DEBUG", "1") != "1":
            raise ValueError("Reset de cadastro disponível apenas em desenvolvimento.")

        email = (email or "").lower().strip()
        if not email:
            raise ValueError("Informe o e-mail.")
        if email in _PROTECTED_RESET_EMAILS:
            raise ValueError("Este e-mail é um utilizador padrão de desenvolvimento e não pode ser removido.")

        user = User.query.filter(func.lower(User.email) == email).first()
        if not user:
            return {"status": "not_found", "message": "Nenhum cadastro encontrado para este e-mail."}

        team_membership = (
            TenantUser.query.filter(
                TenantUser.user_id == user.id,
                TenantUser.role.in_(tuple(SYSTEM_ROLES)),
            ).first()
        )
        lead_access_rows = LeadAccess.query.filter_by(user_id=user.id).all()
        if team_membership and not lead_access_rows:
            raise ValueError("Este e-mail pertence à equipe. Utilize o login com senha.")

        tenant_ids = {row.tenant_id for row in lead_access_rows}
        for tenant_id in tenant_ids:
            tenant = db.session.get(Tenant, tenant_id)
            if tenant:
                db.session.delete(tenant)

        db.session.flush()

        remaining_team = (
            TenantUser.query.filter(
                TenantUser.user_id == user.id,
                TenantUser.role.in_(tuple(SYSTEM_ROLES)),
            ).first()
        )
        if not remaining_team:
            db.session.delete(user)

        db.session.commit()
        return {
            "status": "reset",
            "message": f"Cadastro de {email} removido. Você pode se cadastrar novamente.",
            "email": email,
        }

    def lookup_access_code(self, email: str) -> dict[str, Any]:
        """Consulta vínculo lead_access (desenvolvimento)."""
        if os.getenv("FLASK_DEBUG", "1") != "1":
            raise ValueError("Consulta disponível apenas em desenvolvimento.")

        email = (email or "").lower().strip()
        user = User.query.filter(func.lower(User.email) == email).first()
        if not user:
            raise ValueError("Utilizador não encontrado.")

        lead_access = (
            LeadAccess.query.filter_by(user_id=user.id)
            .order_by(LeadAccess.created_at.desc())
            .first()
        )
        memberships = TenantUser.query.filter_by(user_id=user.id).all()
        return {
            "status": "ok",
            "email": user.email,
            "user_id": str(user.id),
            "access_code": lead_access.access_code if lead_access else None,
            "tenant_id": str(lead_access.tenant_id) if lead_access else None,
            "memberships": [
                {"tenant_id": str(m.tenant_id), "role": m.role} for m in memberships
            ],
        }

    def check_email(self, email: str) -> dict[str, Any]:
        email = (email or "").lower().strip()
        if not email:
            raise ValueError("Informe o e-mail.")

        user = User.query.filter(func.lower(User.email) == email).first()
        if not user:
            return {
                "type": "UNKNOWN",
                "message": "E-mail não encontrado. Faça seu cadastro para receber o código LA-*.",
                "register_url": "/cadastro",
            }

        lead_access = (
            LeadAccess.query.filter_by(user_id=user.id)
            .order_by(LeadAccess.created_at.desc())
            .first()
        )
        if lead_access:
            msg = "Digite o código de acesso enviado no momento do cadastro."
            if user.password_hash:
                msg = (
                    "Este e-mail também possui acesso de equipe. "
                    "Use o código LA-* recebido no cadastro ou a senha de equipe."
                )
            return self._with_dev_access_code(
                {"type": "LEAD", "message": msg},
                lead_access.access_code,
            )

        membership = TenantUser.query.filter_by(user_id=user.id).first()
        if user.password_hash and membership and membership.role in SYSTEM_ROLES:
            if membership.role == ROLE_SYSADMIN:
                return {"type": "TEAM", "message": "Digite sua senha de administrador."}
            return {"type": "TEAM", "message": "Digite sua senha de acesso da equipe."}

        return {
            "type": "UNKNOWN",
            "message": "Conta sem credencial configurada. Entre em contato com o suporte.",
        }

    def login(self, email: str, credential: str) -> dict[str, Any]:
        email = (email or "").lower().strip()
        credential = (credential or "").strip()
        if not email or not credential:
            raise ValueError("Informe e-mail e código/senha.")

        user = User.query.filter(func.lower(User.email) == email).first()
        if not user:
            raise ValueError("E-mail não encontrado.")
        if not user.is_active:
            raise ValueError("Utilizador inativo. Contacte o administrador.")

        lead_access = LeadAccess.query.filter_by(user_id=user.id).order_by(
            LeadAccess.created_at.desc()
        ).first()

        if lead_access and self._codes_match(lead_access.access_code, credential):
            return self._build_session(user, lead_access, auth_type="lead")

        if user.password_hash and check_password_hash(user.password_hash, credential):
            membership = (
                TenantUser.query.filter_by(user_id=user.id)
                .order_by(TenantUser.role.asc())
                .first()
            )
            if not membership:
                raise ValueError("Utilizador sem vínculo de tenant.")
            return self._build_team_session(user, membership)

        if lead_access:
            raise ValueError(
                "Código incorreto. Verifique o código LA-* recebido no cadastro."
            )
        raise ValueError("Credenciais inválidas.")

    def _handle_existing_registration(self, user: User, email: str) -> dict[str, Any]:
        lead_access = self._ensure_lead_access_for_user(user)
        lead_access.access_code = self._generate_access_code()
        db.session.commit()
        dispatch_access_code_email(email, lead_access.access_code)

        return self._with_dev_access_code(
            {
                "status": "resent",
                "message": (
                    f"Este e-mail já possui cadastro. Enviamos um novo código de acesso para {email}."
                ),
                "tenant_id": str(lead_access.tenant_id),
                "user_id": str(user.id),
                "email_sent": True,
            },
            lead_access.access_code,
        )

    def _ensure_lead_access_for_user(self, user: User) -> LeadAccess:
        lead_access = (
            LeadAccess.query.filter_by(user_id=user.id)
            .order_by(LeadAccess.created_at.desc())
            .first()
        )
        if lead_access:
            return lead_access

        membership = (
            TenantUser.query.filter_by(user_id=user.id, role=ROLE_LED)
            .order_by(TenantUser.tenant_id.asc())
            .first()
        )
        if not membership:
            raise ValueError(
                "Este e-mail já está em uso com outro perfil. Utilize o login ou contate o suporte."
            )

        lead_access = LeadAccess(
            tenant_id=membership.tenant_id,
            user_id=user.id,
            access_code=self._generate_access_code(),
        )
        db.session.add(lead_access)
        db.session.flush()
        return lead_access

    def _is_orphan_user(self, user: User) -> bool:
        has_membership = TenantUser.query.filter_by(user_id=user.id).first()
        has_lead = LeadAccess.query.filter_by(user_id=user.id).first()
        return not has_membership and not has_lead

    def _sector_for_framework(
        self, framework_id: str | None, framework: Framework | None
    ) -> str | None:
        if framework:
            metadata = framework.rules_metadata or {}
            return metadata.get("sector") or framework.industry
        if framework_id == DEV_FRAMEWORK_CONSTRUCAO_ID:
            return "Construção Civil"
        return None

    def _build_session(
        self, user: User, lead_access: LeadAccess, auth_type: str
    ) -> dict[str, Any]:
        lead_access.last_used_at = datetime.now(timezone.utc)
        tenant = db.session.get(Tenant, lead_access.tenant_id)
        membership = TenantUser.query.filter_by(
            tenant_id=lead_access.tenant_id, user_id=user.id
        ).first()
        tenant_fw = (
            TenantFramework.query.filter_by(tenant_id=lead_access.tenant_id, status="active")
            .order_by(TenantFramework.started_at.desc())
            .first()
        )
        db.session.commit()

        framework = resolve_framework_for_tenant(lead_access.tenant_id)
        framework_id = framework.id if framework else (tenant_fw.framework_id if tenant_fw else None)
        sector = self._sector_for_framework(framework_id, framework)
        has_diagnostic = (
            AssessmentSubmission.query.filter_by(
                tenant_id=lead_access.tenant_id,
                user_id=user.id,
                status="completed",
            ).first()
            is not None
        )
        return {
            "success": True,
            "auth_type": auth_type,
            "system_role": membership.role if membership else ROLE_LED,
            "user_id": str(user.id),
            "user_name": user.name,
            "email": user.email,
            "tenant_id": str(lead_access.tenant_id),
            "tenant_name": tenant.name if tenant else None,
            "framework_id": framework_id,
            "sector": sector,
            "redirect": "/" if has_diagnostic else "/diagnostico",
        }

    def _build_team_session(self, user: User, membership: TenantUser) -> dict[str, Any]:
        tenant = db.session.get(Tenant, membership.tenant_id)
        tenant_fw = (
            TenantFramework.query.filter_by(tenant_id=membership.tenant_id, status="active")
            .order_by(TenantFramework.started_at.desc())
            .first()
        )
        framework = resolve_framework_for_tenant(membership.tenant_id)
        framework_id = framework.id if framework else (tenant_fw.framework_id if tenant_fw else None)
        sector = self._sector_for_framework(framework_id, framework)

        lead_redirect = "/diagnostico"
        if membership.role == ROLE_LED:
            has_diagnostic = (
                AssessmentSubmission.query.filter_by(
                    tenant_id=membership.tenant_id,
                    user_id=user.id,
                    status="completed",
                ).first()
                is not None
            )
            lead_redirect = "/" if has_diagnostic else "/diagnostico"

        redirects = {
            ROLE_SYSADMIN: "/builder",
            ROLE_LED: lead_redirect,
            "consultor": "/avaliacoes",
            "executor": "/",
        }
        return {
            "success": True,
            "auth_type": "team",
            "system_role": membership.role,
            "user_id": str(user.id),
            "user_name": user.name,
            "email": user.email,
            "tenant_id": str(membership.tenant_id),
            "tenant_name": tenant.name if tenant else None,
            "framework_id": framework_id,
            "sector": sector,
            "redirect": redirects.get(membership.role, "/"),
        }

    @staticmethod
    def _normalize_document(document: str | None) -> str | None:
        if not document:
            return None
        stripped = document.strip()
        return stripped or None

    @staticmethod
    def _document_key(document: str | None) -> str | None:
        if not document:
            return None
        digits = re.sub(r"\D", "", document)
        return digits or None

    def _document_is_taken(self, document: str) -> bool:
        key = self._document_key(document)
        if not key:
            return False
        for tenant in Tenant.query.filter(Tenant.document.isnot(None)).all():
            if self._document_key(tenant.document) == key:
                return True
        return False

    @staticmethod
    def _integrity_error_to_value_error(exc: IntegrityError) -> ValueError:
        message = str(getattr(exc, "orig", exc)).lower()
        if "users_email_key" in message or "users.email" in message:
            return ValueError("Este e-mail já está cadastrado. Utilize o login para acessar.")
        if "tenants_document_key" in message or "tenants.document" in message:
            return ValueError(
                "CNPJ/documento já cadastrado. Utilize outro documento ou deixe o campo em branco."
            )
        if "lead_access_access_code_key" in message:
            return ValueError("Erro ao gerar código de acesso. Tente novamente.")
        return ValueError("Não foi possível concluir o cadastro. Verifique os dados informados.")

    @staticmethod
    def _with_dev_access_code(payload: dict[str, Any], access_code: str) -> dict[str, Any]:
        if os.getenv("FLASK_DEBUG", "1") == "1" or os.getenv("CHAMELLEON_DEV_EXPOSE_ACCESS_CODE", "1") == "1":
            payload["dev_access_code"] = access_code
            payload["dev_hint"] = (
                "Desenvolvimento: se o e-mail não chegar, use este código no login."
            )
        return payload

    @staticmethod
    def _sector_label(fw: Framework) -> str:
        meta = fw.rules_metadata if isinstance(fw.rules_metadata, dict) else {}
        sector = (meta.get("sector") or fw.industry or "").strip()
        if sector:
            return LeadAuthService._format_sector_display(sector)
        cleaned = LeadAuthService._strip_framework_prefix(fw.name or fw.id)
        return LeadAuthService._format_sector_display(cleaned)

    @staticmethod
    def _format_sector_display(value: str) -> str:
        text = (value or "").strip()
        return text.title() if text else text

    @staticmethod
    def _strip_framework_prefix(name: str) -> str:
        text = (name or "").strip()
        for prefix in ("Chamelleon — ", "Chamelleon - ", "PanelDX — ", "PanelDX - "):
            if text.startswith(prefix):
                text = text[len(prefix) :].strip()
        text = re.sub(r"^framework\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*—\s*framework\s+", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bframework\b\s*", "", text, flags=re.IGNORECASE)
        return text.strip()

    @staticmethod
    def _generate_access_code() -> str:
        suffix = "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)
        )
        return f"LA-{suffix}"

    @staticmethod
    def _codes_match(stored: str, provided: str) -> bool:
        s = (stored or "").strip().upper()
        p = (provided or "").strip().upper()
        if not s or not p:
            return False
        if s == p:
            return True
        s_core = s[3:] if s.startswith("LA-") else s
        p_core = p[3:] if p.startswith("LA-") else p
        return s_core == p_core
