"""Foto/PDF só anexam nota existente. Sem extração, sem nota sintética."""

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
from app.modules.production_planning.errors import InvalidStateError, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests import helpers

FIXTURE_XML = Path(__file__).parent / "fixtures" / "fiscal" / "demo_nfe.xml"
JPEG = b"\xff\xd8\xff\xe0" + b"foto-real" + b"\x00" * 32
PDF = b"%PDF-1.4\n%referencia\n%%EOF"
REAL_KEY = "35260812345678000190550010005066121034567890"


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


def _manual(ctx, *, number: str, access_key: str | None = None):
    return commands.create_manual(
        ctx["session"],
        ctx["principal"],
        {
            "establishment_id": str(ctx["place"].id),
            "supplier_name": "Moinho Real",
            "document_number": number,
            "access_key": access_key,
            "items": [{"description": "Farinha tipo 1", "quantity": "25", "unit_code": "KG", "unit_price": "4.10"}],
        },
        idempotency_key=uuid4(),
    )


def _scan(ctx, *, document_id=None, content: bytes, content_type: str, filename: str, key=None, store=None, ocr=None):
    body = {
        "establishment_id": str(ctx["place"].id),
        "content": content,
        "content_type": content_type,
        "filename": filename,
    }
    if document_id is not None:
        body["document_id"] = str(document_id)
    return commands.attach_scan(
        ctx["session"],
        ctx["principal"],
        body,
        idempotency_key=key or uuid4(),
        store=store,
        ocr=ocr,
    )


def test_scan_without_document_does_not_persist(db_session: Session) -> None:
    ctx = _world(db_session, f"foto{uuid4().hex[:6]}")
    before = _counts(db_session, ctx["organization"].id)
    with pytest.raises(ValidationError, match="anexo_nao_cria_nota"):
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


def test_photo_attaches_existing_note_without_extraction(db_session: Session) -> None:
    ctx = _world(db_session, f"ref{uuid4().hex[:6]}")
    note = _manual(ctx, number="50661", access_key=REAL_KEY)
    before_header = (note.emitter_name, note.number, note.access_key, note.status)
    attached = _scan(
        ctx,
        document_id=note.id,
        content=JPEG,
        content_type="image/jpeg",
        filename="nota.jpeg",
        ocr=_ForbiddenOcr(),
    )
    db_session.flush()
    assert attached.id == note.id
    assert (attached.emitter_name, attached.number, attached.access_key, attached.status) == before_header
    atts = list(
        db_session.scalars(
            select(FiscalInboundAttachment).where(
                FiscalInboundAttachment.fiscal_inbound_document_id == note.id
            )
        )
    )
    assert len(atts) == 1
    assert atts[0].kind == "image"
    assert _counts(db_session, ctx["organization"].id)["extractions"] == 0
    assert _counts(db_session, ctx["organization"].id)["movements"] == 0
    assert _counts(db_session, ctx["organization"].id)["documents"] == 1


def test_pdf_attaches_existing_note_without_extraction(db_session: Session) -> None:
    ctx = _world(db_session, f"pdf{uuid4().hex[:6]}")
    note = _manual(ctx, number="4102")
    _scan(
        ctx,
        document_id=note.id,
        content=PDF,
        content_type="application/pdf",
        filename="nota.pdf",
        ocr=_ForbiddenOcr(),
    )
    db_session.flush()
    atts = list(
        db_session.scalars(
            select(FiscalInboundAttachment).where(
                FiscalInboundAttachment.fiscal_inbound_document_id == note.id
            )
        )
    )
    assert len(atts) == 1
    assert atts[0].kind == "pdf"
    assert note.number == "4102"
    assert note.access_key is None
    assert _counts(db_session, ctx["organization"].id)["extractions"] == 0


def test_repeat_upload_does_not_duplicate(db_session: Session) -> None:
    ctx = _world(db_session, f"dup{uuid4().hex[:6]}")
    note = _manual(ctx, number="4103")
    first = _scan(ctx, document_id=note.id, content=JPEG, content_type="image/jpeg", filename="a.jpeg")
    second = _scan(ctx, document_id=note.id, content=JPEG, content_type="image/jpeg", filename="a.jpeg")
    db_session.flush()
    assert first.id == second.id == note.id
    assert _counts(db_session, ctx["organization"].id)["attachments"] == 1


def test_failed_upload_keeps_saved_note(db_session: Session) -> None:
    ctx = _world(db_session, f"falha{uuid4().hex[:6]}")
    note = _manual(ctx, number="4104")
    with pytest.raises(AssertionError, match="store.put"):
        _scan(
            ctx,
            document_id=note.id,
            content=JPEG,
            content_type="image/jpeg",
            filename="nota.jpeg",
            store=_ForbiddenStore(),
        )
    kept = db_session.get(FiscalInboundDocument, note.id)
    assert kept is not None
    assert kept.number == "4104"
    assert _counts(db_session, ctx["organization"].id)["documents"] == 1
    assert _counts(db_session, ctx["organization"].id)["attachments"] == 0
    assert _counts(db_session, ctx["organization"].id)["movements"] == 0


def test_default_ocr_provider_cannot_serve_synthetic() -> None:
    with pytest.raises(InvalidStateError, match="ocr_proibido_em_dados_de_cliente"):
        default_ocr_provider()


def test_simulate_ingest_and_lookup_do_not_create_document(db_session: Session) -> None:
    ctx = _world(db_session, f"sim{uuid4().hex[:6]}")
    before = _counts(db_session, ctx["organization"].id)
    with pytest.raises(InvalidStateError, match="simulacao_nao_grava_documento"):
        commands.simulate_distribution_poll(
            db_session,
            ctx["principal"],
            {"establishment_id": str(ctx["place"].id), "ingest": True},
            idempotency_key=uuid4(),
        )
    with pytest.raises(InvalidStateError, match="consulta_fiscal_nao_ativada"):
        commands.lookup_access_key(
            db_session,
            ctx["principal"],
            {"access_key": REAL_KEY, "establishment_id": str(ctx["place"].id)},
            idempotency_key=uuid4(),
        )
    db_session.flush()
    assert _counts(db_session, ctx["organization"].id) == before


def test_xml_and_manual_with_or_without_key(db_session: Session) -> None:
    ctx = _world(db_session, f"ok{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    with pytest.raises(ValidationError, match="documento_sintetico_proibido"):
        commands.create_manual(
            session,
            principal,
            {
                "establishment_id": str(ctx["place"].id),
                "supplier_name": "X",
                "document_number": "1",
                "synthetic": True,
                "items": [{"description": "x", "quantity": "1", "unit_code": "KG"}],
            },
            idempotency_key=uuid4(),
        )
    without_key = _manual(ctx, number="4101")
    assert without_key.access_key is None
    assert without_key.status == "awaiting_match"
    with_key = _manual(ctx, number="4105", access_key=REAL_KEY)
    assert with_key.access_key == REAL_KEY
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
    assert imported.capture_origin == "xml"
    assert imported.number == "99001"
    assert _counts(session, ctx["organization"].id)["movements"] == 0
