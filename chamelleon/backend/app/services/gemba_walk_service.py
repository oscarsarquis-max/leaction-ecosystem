"""Gestão de Gemba Walks e checklists operacionais."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from flask import g
from sqlalchemy.orm import selectinload

from app.database.models import User, db
from app.models.kaizen_models import (
    GEMBA_FOCUS_AREAS,
    GEMBA_WALK_STATUSES,
    WALK_AGENDADO,
    WALK_CONCLUIDO,
    WALK_EM_ANDAMENTO,
    GembaChecklistItem,
    GembaWalk,
)


class GembaWalkService:
    def list_walks(
        self,
        *,
        status: str | None = None,
        scheduled_date: date | None = None,
    ) -> list[dict[str, Any]]:
        query = GembaWalk.query.filter_by(tenant_id=self._tenant_id())
        if status:
            self._validate_walk_status(status)
            query = query.filter_by(status=status)
        if scheduled_date:
            query = query.filter_by(scheduled_date=scheduled_date)
        walks = query.order_by(
            GembaWalk.scheduled_date.desc(),
            GembaWalk.created_at.desc(),
        ).all()
        return [walk.to_dict() for walk in walks]

    def get_walk(self, walk_id: str) -> dict[str, Any]:
        walk = self._get_walk_or_404(walk_id, with_checklist=True)
        return walk.to_dict(include_checklist=True)

    def create_walk(self, payload: dict[str, Any]) -> GembaWalk:
        scheduled = self._parse_scheduled_date(payload.get("scheduled_date"))
        focus_area = str(payload.get("focus_area") or "").strip()
        if not focus_area:
            raise ValueError("Campo obrigatório: focus_area.")
        self._validate_focus_area(focus_area)

        status = str(payload.get("status") or WALK_AGENDADO).strip()
        self._validate_walk_status(status)

        conducted_by = self._parse_optional_user_id(payload.get("conducted_by"))
        if conducted_by is None and status != WALK_AGENDADO:
            conducted_by = self._current_user_id()

        walk = GembaWalk(
            tenant_id=self._tenant_id(),
            scheduled_date=scheduled,
            focus_area=focus_area,
            status=status,
            conducted_by=conducted_by,
        )
        db.session.add(walk)
        db.session.commit()
        return walk

    def add_checklist_items(self, walk_id: str, payload: dict[str, Any]) -> GembaWalk:
        walk = self._get_walk_or_404(walk_id)
        self._assert_walk_editable(walk)

        items = payload.get("items")
        if items is None:
            items = payload if isinstance(payload, list) else []
        if not isinstance(items, list) or not items:
            raise ValueError("Envie 'items' como lista com ao menos uma pergunta.")

        if walk.status == WALK_AGENDADO:
            walk.status = WALK_EM_ANDAMENTO
            if not walk.conducted_by:
                walk.conducted_by = self._current_user_id()

        added = 0
        for raw in items:
            if not isinstance(raw, dict):
                continue
            question = str(raw.get("question") or "").strip()
            if not question:
                continue
            walk.checklist_items.append(
                GembaChecklistItem(
                    question=question,
                    is_compliant=raw.get("is_compliant"),
                    immediate_action_taken=self._optional_text(raw.get("immediate_action_taken")),
                )
            )
            added += 1

        if added == 0:
            raise ValueError("Nenhum item válido em 'items'.")

        db.session.commit()
        db.session.refresh(walk)
        return walk

    def update_checklist_item(
        self,
        walk_id: str,
        item_id: str,
        payload: dict[str, Any],
    ) -> GembaChecklistItem:
        walk = self._get_walk_or_404(walk_id)
        self._assert_walk_editable(walk)

        item_uuid = self._parse_uuid(item_id, "item_id")
        item = db.session.get(GembaChecklistItem, item_uuid)
        if not item or item.gemba_walk_id != walk.id:
            raise ValueError("Item de checklist não encontrado.")

        if "is_compliant" in payload:
            value = payload.get("is_compliant")
            item.is_compliant = None if value is None else bool(value)

        if "immediate_action_taken" in payload:
            item.immediate_action_taken = self._optional_text(payload.get("immediate_action_taken"))

        if walk.status == WALK_AGENDADO:
            walk.status = WALK_EM_ANDAMENTO
            if not walk.conducted_by:
                walk.conducted_by = self._current_user_id()

        db.session.commit()
        return item

    def complete_walk(self, walk_id: str) -> GembaWalk:
        walk = self._get_walk_or_404(walk_id)
        if walk.status == WALK_CONCLUIDO:
            raise ValueError("Gemba Walk já está concluído.")
        walk.status = WALK_CONCLUIDO
        if not walk.conducted_by:
            walk.conducted_by = self._current_user_id()
        db.session.commit()
        return walk

    def _get_walk_or_404(self, walk_id: str, *, with_checklist: bool = False) -> GembaWalk:
        walk_uuid = self._parse_uuid(walk_id, "walk_id")
        query = GembaWalk.query.filter_by(id=walk_uuid, tenant_id=self._tenant_id())
        if with_checklist:
            query = query.options(selectinload(GembaWalk.checklist_items))
        walk = query.first()
        if not walk:
            raise ValueError("Gemba Walk não encontrado.")
        return walk

    @staticmethod
    def _assert_walk_editable(walk: GembaWalk) -> None:
        if walk.status == WALK_CONCLUIDO:
            raise ValueError("Gemba Walk concluído não pode ser alterado.")

    @staticmethod
    def _tenant_id() -> uuid.UUID:
        tenant_id = getattr(g, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("Contexto de tenant ausente.")
        return tenant_id

    @staticmethod
    def _current_user_id() -> uuid.UUID | None:
        return getattr(g, "user_id", None)

    @staticmethod
    def _parse_uuid(value: Any, field: str) -> uuid.UUID:
        try:
            return uuid.UUID(str(value).strip())
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"{field} inválido (UUID esperado).") from exc

    @staticmethod
    def _parse_optional_user_id(value: Any) -> uuid.UUID | None:
        if value is None or str(value).strip() == "":
            return None
        user_id = GembaWalkService._parse_uuid(value, "conducted_by")
        if not db.session.get(User, user_id):
            raise ValueError("conducted_by inválido (usuário não encontrado).")
        return user_id

    @staticmethod
    def _parse_scheduled_date(value: Any) -> date:
        if value is None or str(value).strip() == "":
            raise ValueError("Campo obrigatório: scheduled_date.")
        text = str(value).strip()
        try:
            if "T" in text:
                return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
            return date.fromisoformat(text[:10])
        except ValueError as exc:
            raise ValueError("scheduled_date inválido (use ISO-8601, ex.: 2026-07-07).") from exc

    @staticmethod
    def _validate_focus_area(value: str) -> None:
        if value not in GEMBA_FOCUS_AREAS:
            allowed = ", ".join(GEMBA_FOCUS_AREAS)
            raise ValueError(f"focus_area inválido. Use: {allowed}.")

    @staticmethod
    def _validate_walk_status(value: str) -> None:
        if value not in GEMBA_WALK_STATUSES:
            allowed = ", ".join(GEMBA_WALK_STATUSES)
            raise ValueError(f"status inválido. Use: {allowed}.")

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
