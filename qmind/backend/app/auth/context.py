"""Authenticated principal + active organization context."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: UUID
    idp_sub: str
    email: str


@dataclass(frozen=True, slots=True)
class OrgContext:
    principal: Principal
    organization_id: UUID
    membership_id: UUID
    roles: tuple[str, ...]
