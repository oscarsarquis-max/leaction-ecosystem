"""Contenção: foto/PDF falham antes de criar documento ou anexo."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.modules.fiscal_inbound import commands
from app.modules.fiscal_inbound.models import (
    FiscalInboundAttachment,
    FiscalInboundDocument,
    FiscalInboundExtraction,
)
from app.modules.fiscal_inbound.ocr import SyntheticOcrProvider, default_ocr_provider
from app.modules.inventory_procurement.models import InventoryCommand, InventoryMovement
from app.modules.production_http.errors import public_error
from app.modules.production_planning.errors import InvalidStateError
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests import helpers

FIXTURE_XML = Path(__file__).parent / "fixtures" / "fiscal" / "demo_nfe.xml"
JPEG = b"\xff\xd8\xff\xe0" + b"foto-real" + b"\x00" * 32
PDF = b"%PDF-1.4\n%referencia\n%%EOF"


def _ensure_head(engine) -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")


@pytest.fixture(scope="module", autouse=True)
def _schema(engine) -> None:
    _ensure_head(engine)


def _world(session: Session, slug: str):
    organization = helpers.org(session, slug)
    actor = helpers.user(session, f"{slug}@example.com")
    helpers.membership(session, organization, actor, "owner")
    place = helpers.establishment(session, organization, "MATRIZ")
    principal = helpers.principal_for(actor, organization, "owner")
    return {
        "session": session,
        "organization": organization,
        "place": place,
        "principal": principal,
    }


def _counts(session: Session, organization_id):
    org = organization_id
    return {
        "documents": session.scalar(
            select(func.count()).select_from(FiscalInboundDocument).where(
                FiscalInboundDocument.organization_id == org
            )
        )
        or 0,
        "attachments": session.scalar(
            select(func.count()).select_from(FiscalInboundAttachment).where(
                FiscalInboundAttachment.organization_id == org
            )
        )
        or 0,
        "extractions": session.scalar(
            select(func.count()).select_from(FiscalInboundExtraction).where(
                FiscalInboundExtraction.organization_id == org
            )
        )
        or 0,
        "movements": session.scalar(
            select(func.count()).select_from(InventoryMovement).where(
                InventoryMovement.organization_id == org
            )
        )
        or 0,
        "commands": session.scalar(
            select(func.count()).select_from(InventoryCommand).where(
                InventoryCommand.organization_id == org
            )
        )
        or 0,
    }


class _ForbiddenStore:
    def put(self, *args, **kwargs):
        raise AssertionError("store.put nao deveria ser chamado")


class _ForbiddenOcr(SyntheticOcrProvider):
    def extract(self, payload: bytes, *, content_type: str):
        raise AssertionError("ocr.extract nao deveria ser chamado")


def _scan(ctx, *, content: bytes, content_type: str, filename: str, key=None, store=None, ocr=None):
    return commands.attach_scan(
        ctx["session"],
        ctx["principal"],
        {
            "establishment_id": str(ctx["place"].id),
            "content": content,
            "content_type": content_type,
            "filename": filename,
        },
        idempotency_key=key or uuid4(),
        store=store,
        ocr=ocr,
    )


def test_photo_fails_before_document_or_attachment(db_session: Session) -> None:
    ctx = _world(db_session, f"foto{uuid4().hex[:6]}")
    before = _counts(db_session, ctx["organization"].id)
    with pytest.raises(InvalidStateError, match="captura_indisponivel"):
        _scan(
            ctx,
            content=JPEG,
            content_type="image/jpeg",
            filename="nota.jpeg",
            store=_ForbiddenStore(),
            ocr=_ForbiddenOcr(),
        )
    db_session.flush()
    assert _counts(db_session, ctx["organization"].id) == before


def test_pdf_fails_before_document_or_attachment(db_session: Session) -> None:
    ctx = _world(db_session, f"pdf{uuid4().hex[:6]}")
    before = _counts(db_session, ctx["organization"].id)
    with pytest.raises(InvalidStateError, match="captura_indisponivel"):
        _scan(
            ctx,
            content=PDF,
            content_type="application/pdf",
            filename="nota.pdf",
            store=_ForbiddenStore(),
            ocr=_ForbiddenOcr(),
        )
    db_session.flush()
    assert _counts(db_session, ctx["organization"].id) == before


def test_scan_replay_does_not_persist(db_session: Session) -> None:
    ctx = _world(db_session, f"rep{uuid4().hex[:6]}")
    key = uuid4()
    before = _counts(db_session, ctx["organization"].id)
    for _ in range(2):
        with pytest.raises(InvalidStateError, match="captura_indisponivel"):
            _scan(
                ctx,
                content=JPEG,
                content_type="image/jpeg",
                filename="replay.jpeg",
                key=key,
                store=_ForbiddenStore(),
                ocr=_ForbiddenOcr(),
            )
    db_session.flush()
    assert _counts(db_session, ctx["organization"].id) == before


def test_default_ocr_provider_cannot_serve_synthetic() -> None:
    with pytest.raises(InvalidStateError, match="ocr_proibido_em_dados_de_cliente"):
        default_ocr_provider()


def test_simulate_ingest_does_not_create_document(db_session: Session) -> None:
    ctx = _world(db_session, f"sim{uuid4().hex[:6]}")
    before = _counts(db_session, ctx["organization"].id)
    with pytest.raises(InvalidStateError, match="simulacao_nao_grava_documento"):
        commands.simulate_distribution_poll(
            db_session,
            ctx["principal"],
            {"establishment_id": str(ctx["place"].id), "ingest": True},
            idempotency_key=uuid4(),
        )
    db_session.flush()
    assert _counts(db_session, ctx["organization"].id) == before


def test_xml_and_manual_still_work(db_session: Session) -> None:
    ctx = _world(db_session, f"ok{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    manual = commands.create_manual(
        session,
        principal,
        {
            "establishment_id": str(ctx["place"].id),
            "supplier_name": "Moinho Real",
            "document_number": "4101",
            "items": [{"description": "Farinha tipo 1", "quantity": "25", "unit_code": "KG"}],
        },
        idempotency_key=uuid4(),
    )
    assert manual.status == "awaiting_match"
    assert manual.number == "4101"
    imported = commands.import_xml(
        session,
        principal,
        {
            "establishment_id": str(ctx["place"].id),
            "content": FIXTURE_XML.read_bytes(),
            "filename": "nota.xml",
            "synthetic": True,
        },
        idempotency_key=uuid4(),
    )
    assert imported.status == "awaiting_match"
    assert imported.capture_origin == "xml"
    assert imported.number == "99001"
    assert _counts(session, ctx["organization"].id)["movements"] == 0


def test_captura_indisponivel_is_honest_public_error() -> None:
    payload = public_error("captura_indisponivel")
    assert payload["code"] == "captura_indisponivel"
    assert "indisponível" in payload["message"]
