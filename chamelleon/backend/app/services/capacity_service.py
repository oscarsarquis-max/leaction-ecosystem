"""Serviço de Capacity Planning — profissionais e squads 1:1 por sprint."""

from __future__ import annotations

import logging
import secrets
import string
import uuid
from typing import Any

from flask import g
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from werkzeug.security import generate_password_hash

from app.core.rbac.constants import ROLE_SQUAD_MEMBER
from app.database.models import TenantUser, User, db
from app.models.capacity_models import (
    PROFESSIONAL_LICENSE_LIMIT,
    PROFESSIONAL_ROLES,
    SQUAD_MAX_EXECUTION_ALLOCATIONS,
    SQUAD_MAX_SPECIALISTS,
    SQUAD_MAX_TOTAL_MEMBERS,
    Professional,
    ProfessionalRole,
    SprintSquad,
    sprintsquad_members,
)
from app.models.td_models import TdKanbanStage, TdSprint

logger = logging.getLogger(__name__)


class LicenseLimitError(Exception):
    """Quota de licenças do plano atingida."""

    def __init__(self, message: str, *, used: int, limit: int):
        super().__init__(message)
        self.used = used
        self.limit = limit
        self.code = "LICENSE_LIMIT"


def send_welcome_email(email: str, password: str) -> None:
    """Mock de envio de credenciais — loga no terminal do backend."""
    print(
        f"\n📧 [MOCK EMAIL] Welcome → {email}\n"
        f"   Senha temporária: {password}\n"
        f"   (Simulação — SES/SMTP ainda não ligado)\n",
        flush=True,
    )
    logger.info("Welcome email mock enviado para %s", email)


class CapacityService:
    def _tenant_id(self) -> uuid.UUID:
        tenant_id = getattr(g, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("Contexto de tenant obrigatório.")
        return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))

    @staticmethod
    def _parse_uuid(value: Any, field: str) -> uuid.UUID:
        try:
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} inválido.") from exc

    @staticmethod
    def _validate_role(role: str) -> str:
        role = str(role or "").strip()
        if role not in PROFESSIONAL_ROLES:
            raise ValueError(
                f"role inválido. Use um de: {', '.join(PROFESSIONAL_ROLES)}"
            )
        return role

    @staticmethod
    def _generate_temp_password(length: int = 8) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def count_active_professionals(self) -> int:
        return Professional.query.filter_by(
            tenant_id=self._tenant_id(), is_active=True
        ).count()

    def get_license_usage(self) -> dict[str, Any]:
        used = self.count_active_professionals()
        limit = PROFESSIONAL_LICENSE_LIMIT
        return {
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used),
            "plan": "basico",
            "plan_label": "Plano Básico",
            "at_limit": used >= limit,
        }

    # ── Professionals CRUD ─────────────────────────────────────────────

    def list_professionals(self, *, active_only: bool = False) -> list[Professional]:
        query = Professional.query.filter_by(tenant_id=self._tenant_id())
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(Professional.name.asc()).all()

    def create_professional(self, payload: dict[str, Any]) -> Professional:
        name = str(payload.get("name") or "").strip()
        email = str(payload.get("email") or "").strip().lower()
        observations = str(payload.get("observations") or "").strip() or None
        if not name:
            raise ValueError("Campo obrigatório: name.")
        if not email or "@" not in email:
            raise ValueError("Campo obrigatório: email corporativo válido.")

        role = self._validate_role(payload.get("role"))
        tenant_id = self._tenant_id()

        used = self.count_active_professionals()
        if used >= PROFESSIONAL_LICENSE_LIMIT:
            raise LicenseLimitError(
                f"Limite de licenças atingido ({PROFESSIONAL_LICENSE_LIMIT}/{PROFESSIONAL_LICENSE_LIMIT}). "
                "Faça upgrade do seu plano para adicionar mais profissionais.",
                used=used,
                limit=PROFESSIONAL_LICENSE_LIMIT,
            )

        existing_prof = Professional.query.filter(
            Professional.tenant_id == tenant_id,
            func.lower(Professional.email) == email,
        ).first()
        if existing_prof:
            raise ValueError("Já existe um profissional com este e-mail neste tenant.")

        existing_user = User.query.filter(func.lower(User.email) == email).first()
        temp_password: str | None
        if existing_user:
            membership = TenantUser.query.filter_by(
                tenant_id=tenant_id, user_id=existing_user.id
            ).first()
            if not membership:
                raise ValueError(
                    "Este e-mail já pertence a um utilizador de outro contexto. Use outro e-mail."
                )
            user = existing_user
            temp_password = None
        else:
            temp_password = self._generate_temp_password(8)
            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(temp_password),
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()
            db.session.add(
                TenantUser(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    role=ROLE_SQUAD_MEMBER,
                )
            )

        professional = Professional(
            tenant_id=tenant_id,
            name=name,
            email=email,
            observations=observations,
            role=role,
            user_id=user.id,
            is_active=bool(payload.get("is_active", True)),
        )
        db.session.add(professional)
        db.session.commit()
        db.session.refresh(professional)

        if temp_password:
            send_welcome_email(email, temp_password)

        return professional

    def update_professional(
        self, professional_id: str, payload: dict[str, Any]
    ) -> Professional:
        professional = self._get_professional_or_404(professional_id)
        if "name" in payload:
            name = str(payload.get("name") or "").strip()
            if not name:
                raise ValueError("name não pode ser vazio.")
            professional.name = name
        if "email" in payload:
            email = str(payload.get("email") or "").strip().lower()
            if not email or "@" not in email:
                raise ValueError("email inválido.")
            clash = Professional.query.filter(
                Professional.tenant_id == professional.tenant_id,
                func.lower(Professional.email) == email,
                Professional.id != professional.id,
            ).first()
            if clash:
                raise ValueError("Já existe um profissional com este e-mail neste tenant.")
            professional.email = email
        if "observations" in payload:
            raw = payload.get("observations")
            professional.observations = (
                str(raw).strip() if raw is not None and str(raw).strip() else None
            )
        if "role" in payload:
            professional.role = self._validate_role(payload.get("role"))
        if "is_active" in payload:
            becoming_active = bool(payload.get("is_active"))
            if becoming_active and not professional.is_active:
                used = self.count_active_professionals()
                if used >= PROFESSIONAL_LICENSE_LIMIT:
                    raise LicenseLimitError(
                        f"Limite de licenças atingido ({PROFESSIONAL_LICENSE_LIMIT}/{PROFESSIONAL_LICENSE_LIMIT}). "
                        "Faça upgrade do seu plano para adicionar mais profissionais.",
                        used=used,
                        limit=PROFESSIONAL_LICENSE_LIMIT,
                    )
            professional.is_active = becoming_active
        db.session.commit()
        db.session.refresh(professional)
        return professional

    def delete_professional(self, professional_id: str) -> Professional:
        """Soft-delete: desativa o profissional (libera licença)."""
        professional = self._get_professional_or_404(professional_id)
        professional.is_active = False
        db.session.commit()
        db.session.refresh(professional)
        return professional

    def _get_professional_or_404(self, professional_id: str) -> Professional:
        pid = self._parse_uuid(professional_id, "professional_id")
        professional = Professional.query.filter_by(
            id=pid, tenant_id=self._tenant_id()
        ).first()
        if not professional:
            raise ValueError("Profissional não encontrado.")
        return professional

    # ── Sprint Squad ───────────────────────────────────────────────────

    def get_squad(self, sprint_id: str) -> SprintSquad | None:
        sprint = self._get_sprint_or_404(sprint_id)
        return (
            SprintSquad.query.options(
                joinedload(SprintSquad.po),
                joinedload(SprintSquad.sm),
                joinedload(SprintSquad.members),
            )
            .filter_by(sprint_id=sprint.id, tenant_id=self._tenant_id())
            .first()
        )

    def upsert_squad(self, sprint_id: str, payload: dict[str, Any]) -> SprintSquad:
        sprint = self._get_sprint_or_404(sprint_id)
        po_raw = payload.get("po_id")
        sm_raw = payload.get("sm_id")

        # REGRA 3 — papéis obrigatórios
        if not po_raw or not sm_raw:
            raise ValueError(
                "É obrigatório enviar po_id e sm_id para formar a Squad da sprint."
            )

        po_id = self._parse_uuid(po_raw, "po_id")
        sm_id = self._parse_uuid(sm_raw, "sm_id")
        member_ids_raw = payload.get("member_ids") or payload.get("members") or []
        if not isinstance(member_ids_raw, list):
            raise ValueError("member_ids deve ser uma lista de IDs.")

        member_ids: list[uuid.UUID] = []
        seen: set[uuid.UUID] = set()
        for raw in member_ids_raw:
            mid = self._parse_uuid(raw, "member_id")
            if mid in (po_id, sm_id):
                continue  # PO/SM já contam no total; não duplicar como especialista
            if mid in seen:
                continue
            seen.add(mid)
            member_ids.append(mid)

        # REGRA 1 — tamanho máximo (PO + SM + até 6 especialistas ≤ 8)
        if len(member_ids) > SQUAD_MAX_SPECIALISTS:
            raise ValueError(
                f"A equipe técnica pode ter no máximo {SQUAD_MAX_SPECIALISTS} especialistas."
            )
        total_unique = len({po_id, sm_id, *member_ids})
        if total_unique > SQUAD_MAX_TOTAL_MEMBERS:
            raise ValueError(
                f"A SprintSquad não pode ter mais de {SQUAD_MAX_TOTAL_MEMBERS} "
                "membros no total (PO + SM + até 6 especialistas)."
            )

        po = self._require_active_professional(po_id, expected_role=ProfessionalRole.PO.value)
        sm = self._require_active_professional(
            sm_id, expected_role=ProfessionalRole.SCRUM_MASTER.value
        )
        members = [self._require_active_professional(mid) for mid in member_ids]

        squad = SprintSquad.query.filter_by(
            sprint_id=sprint.id, tenant_id=self._tenant_id()
        ).first()

        # REGRA 2 — prevenção de burnout (máx. 3 sprints Em Execução)
        self._assert_no_burnout(
            professional_ids={po_id, sm_id, *member_ids},
            exclude_squad_id=squad.id if squad else None,
            sprint=sprint,
        )

        if squad:
            squad.po_id = po.id
            squad.sm_id = sm.id
            squad.members = members
        else:
            squad = SprintSquad(
                tenant_id=self._tenant_id(),
                sprint_id=sprint.id,
                po_id=po.id,
                sm_id=sm.id,
            )
            squad.members = members
            db.session.add(squad)

        db.session.commit()
        return self.get_squad(str(sprint.id)) or squad

    def assert_squad_ready_for_execution(self, sprint: TdSprint) -> None:
        """Bloqueia movimento para Em Execução sem Squad válida (PO + SM)."""
        squad = SprintSquad.query.filter_by(
            sprint_id=sprint.id, tenant_id=sprint.tenant_id
        ).first()
        if not squad or not squad.is_complete():
            raise ValueError(
                "Não é possível mover a sprint para Em Execução sem uma SprintSquad "
                "válida e completa (Product Owner e Scrum Master obrigatórios)."
            )

    def _require_active_professional(
        self,
        professional_id: uuid.UUID,
        *,
        expected_role: str | None = None,
    ) -> Professional:
        professional = Professional.query.filter_by(
            id=professional_id, tenant_id=self._tenant_id()
        ).first()
        if not professional:
            raise ValueError(f"Profissional {professional_id} não encontrado.")
        if not professional.is_active:
            raise ValueError(f"Profissional '{professional.name}' está inativo.")
        if expected_role and professional.role != expected_role:
            raise ValueError(
                f"Profissional '{professional.name}' deve ter o cargo {expected_role} "
                f"(atual: {professional.role})."
            )
        return professional

    def _assert_no_burnout(
        self,
        *,
        professional_ids: set[uuid.UUID],
        exclude_squad_id: uuid.UUID | None,
        sprint: TdSprint,
    ) -> None:
        """
        Um profissional não pode estar em >3 SprintSquads cujas sprints
        estejam Em Execução. Se esta sprint já está (ou ficará) em Execução,
        a alocação conta; caso contrário, só conta as outras.
        """
        counts_toward_execution = sprint.kanban_stage == TdKanbanStage.EXECUCAO.value

        for pid in professional_ids:
            count = self._count_execution_allocations(
                professional_id=pid,
                exclude_squad_id=exclude_squad_id,
            )
            projected = count + (1 if counts_toward_execution else 0)
            # Ao salvar squad de sprint já em execução, a própria squad é excluída
            # do count e recontada via projected — ok.
            # Ao salvar squad de sprint NÃO em execução, projected == count; o
            # bloqueio só dispara se já estiver em 3+ outras (não pode entrar em
            # mais uma execução depois). Para seleção preventiva: se count >= 3,
            # bloquear mesmo fora de execução (não pode montar equipe sobrecarregada).
            if count >= SQUAD_MAX_EXECUTION_ALLOCATIONS:
                raise ValueError(
                    "Este profissional já está alocado em 3 Sprints em execução."
                )
            if counts_toward_execution and projected > SQUAD_MAX_EXECUTION_ALLOCATIONS:
                raise ValueError(
                    "Este profissional já está alocado em 3 Sprints em execução."
                )

    def _count_execution_allocations(
        self,
        *,
        professional_id: uuid.UUID,
        exclude_squad_id: uuid.UUID | None,
    ) -> int:
        query = (
            db.session.query(SprintSquad.id)
            .join(TdSprint, TdSprint.id == SprintSquad.sprint_id)
            .outerjoin(
                sprintsquad_members,
                sprintsquad_members.c.sprintsquad_id == SprintSquad.id,
            )
            .filter(
                SprintSquad.tenant_id == self._tenant_id(),
                TdSprint.kanban_stage == TdKanbanStage.EXECUCAO.value,
                or_(
                    SprintSquad.po_id == professional_id,
                    SprintSquad.sm_id == professional_id,
                    sprintsquad_members.c.professional_id == professional_id,
                ),
            )
            .distinct()
        )
        if exclude_squad_id:
            query = query.filter(SprintSquad.id != exclude_squad_id)
        return query.count()

    def _get_sprint_or_404(self, sprint_id: str) -> TdSprint:
        sid = self._parse_uuid(sprint_id, "sprint_id")
        sprint = TdSprint.query.filter_by(id=sid, tenant_id=self._tenant_id()).first()
        if not sprint:
            raise ValueError("Sprint não encontrada.")
        return sprint
