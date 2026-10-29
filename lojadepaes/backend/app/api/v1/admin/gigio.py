from typing import Any
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import AdminUser, DbSession
from app.domain.gigio.editorial import list_notes, note_view, save_note
from app.domain.gigio.pairing import (
    create_reference,
    list_references,
    reference_admin_view,
    save_reference,
)

router = APIRouter(prefix="/admin/gigio", tags=["admin-gigio"])


class GigioNoteIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=4000)
    editorial_status: str = Field(default="draft")


class GigioPairingIn(BaseModel):
    profile_key: str = Field(default="", max_length=80)
    category: str = Field(default="vinhos", max_length=16)
    scope: str = Field(default="style", max_length=16)
    title: str = Field(min_length=1, max_length=160)
    synthesis: str = Field(min_length=1, max_length=2000)
    editorial_note: str = Field(default="", max_length=2000)
    characteristics: dict[str, Any] = Field(default_factory=dict)
    culinary_contexts: dict[str, Any] = Field(default_factory=dict)
    match_hints: list[Any] = Field(default_factory=list)
    identity: dict[str, Any] = Field(default_factory=dict)
    source_url: str = Field(min_length=1, max_length=500)
    source_title: str = Field(min_length=1, max_length=240)
    source_author: str = Field(default="", max_length=160)
    source_date: str = Field(default="", max_length=32)
    consulted_at: str = Field(default="", max_length=32)
    source_kind: str = Field(default="commercial_editorial", max_length=32)
    commercial_relation: str = Field(default="unknown", max_length=40)
    evidence_type: str = Field(default="", max_length=32)
    retrieval_role: str = Field(default="", max_length=16)
    verification_status: str = Field(default="", max_length=16)
    support_locator: str = Field(default="", max_length=800)
    claim_layers: dict[str, Any] = Field(default_factory=dict)
    editorial_status: str = Field(default="draft", max_length=16)
    reviewed_by: str = Field(default="", max_length=80)
    reviewed_at: str = Field(default="", max_length=32)
    loja_choice: bool = False


@router.get("/notes")
def admin_gigio_notes(db: DbSession, principal: AdminUser) -> dict:
    del principal
    return {"items": [note_view(row) for row in list_notes(db)]}


@router.put("/notes/{note_id}")
def admin_save_gigio_note(
    note_id: UUID, payload: GigioNoteIn, db: DbSession, principal: AdminUser
) -> dict:
    del principal
    row = save_note(db, note_id, payload.title, payload.body, payload.editorial_status)
    return note_view(row)


@router.get("/pairings")
def admin_gigio_pairings(db: DbSession, principal: AdminUser) -> dict:
    del principal
    return {
        "items": [reference_admin_view(row) for row in list_references(db)],
        "owners": {
            "referencias": "Loja — /admin/produtos/gigio/harmonizacoes",
            "ofertas": "Hub — perfil, preço, link comercial",
            "paes": "Loja — vitrine e receitas",
        },
    }


@router.post("/pairings")
def admin_create_gigio_pairing(payload: GigioPairingIn, db: DbSession, principal: AdminUser) -> dict:
    del principal
    row = create_reference(db, payload.model_dump())
    return reference_admin_view(row)


@router.put("/pairings/{ref_id}")
def admin_save_gigio_pairing(
    ref_id: UUID, payload: GigioPairingIn, db: DbSession, principal: AdminUser
) -> dict:
    del principal
    row = save_reference(db, ref_id, payload.model_dump())
    return reference_admin_view(row)
