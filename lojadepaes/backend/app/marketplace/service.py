"""Operações do marketplace. Não conhece pedido, pagamento, agenda nem aviso."""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastapi.responses import FileResponse, Response

from app.core.config import Settings
from app.domain.email_outbox import enqueue_partner_lead_notice
from app.domain.errors import ProductError
from app.domain.media import open_media, store_image

_log = logging.getLogger("lojadepaes.marketplace")
from app.marketplace.auth import drop_sessions, hash_password, hash_token, start_session, verify_password
from app.marketplace.house_catalog import house_order_cancelled, published_product_name, published_slug_exists
from app.marketplace.models import (
    Partner,
    PartnerLead,
    PartnerLink,
    PartnerMedia,
    PartnerOrder,
    PartnerProduct,
    PartnerUser,
    ProductCombo,
    ProductPairing,
    ProductReview,
)
from app.marketplace.rules import (
    MarketplaceError,
    clean_category,
    clean_ceps,
    clean_fee,
    clean_days,
    clean_decision,
    clean_hex,
    clean_money,
    clean_names,
    clean_optional_text,
    clean_photos,
    clean_required,
    clean_scores,
    clean_slug,
    clean_url,
    delivery_complete,
    fold_text,
    media_id_of,
    periods_overlap,
    refuse_bakery_text,
)

PARTNER_TYPES = frozenset({"producer", "distributor", "restaurant"})
LINK_TYPES = frozenset({"exclusive", "partial", "none"})
INVITE_DAYS = 7
LEAD_CATEGORIES = frozenset(
    {
        "queijos",
        "frios",
        "vinhos",
        "cervejas",
        "azeites",
        "manteigas",
        "geleias",
        "cafe_cha",
        "pratos",
        "outro",
    }
)
LEAD_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
LEAD_RATE_LIMIT = 5
LEAD_RATE_WINDOW = timedelta(hours=1)
LEAD_STATUSES = frozenset({"new", "contacting", "invited", "discarded"})


def _now() -> datetime:
    return datetime.now(UTC)


def _flush(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise MarketplaceError(409, "já existe um registro com estes dados") from None


def _partner_or_404(db: Session, partner_id: UUID) -> Partner:
    partner = db.get(Partner, partner_id)
    if partner is None:
        raise MarketplaceError(404, "não encontrado")
    return partner


def _active(partner: Partner) -> None:
    if partner.status != "active":
        raise MarketplaceError(403, "parceiro sem permissão para alterar")


def partner_out(partner: Partner, email: str | None = None) -> dict:
    body = {
        "id": str(partner.id),
        "partner_type": partner.partner_type,
        "brand_name": partner.brand_name,
        "brand_slug": partner.brand_slug,
        "logo_url": partner.logo_url,
        "photo_url": partner.photo_url,
        "story": partner.story,
        "city": partner.city,
        "region": partner.region,
        "highlight_hex": partner.highlight_hex,
        "document": partner.document,
        "contact": partner.contact,
        "status": partner.status,
        "pay_recipient_id": partner.pay_recipient_id,
        "fee_cents": partner.fee_cents,
    }
    if email is not None:
        body["email"] = email
    return body


def _email_of(db: Session, partner_id: UUID) -> str | None:
    return db.scalar(select(PartnerUser.email).where(PartnerUser.partner_id == partner_id))


def _apply_brand(partner: Partner, payload: dict, *, required: bool) -> None:
    if required or "brand_name" in payload:
        partner.brand_name = clean_required(str(payload.get("brand_name") or ""), "o nome da marca", 120)
    if required or "brand_slug" in payload:
        partner.brand_slug = clean_slug(str(payload.get("brand_slug") or ""))
    if required or "logo_url" in payload:
        partner.logo_url = clean_url(str(payload.get("logo_url") or ""), "o logo")
    if required or "photo_url" in payload:
        partner.photo_url = clean_url(str(payload.get("photo_url") or ""), "a foto da marca")
    if required or "story" in payload:
        partner.story = clean_optional_text(str(payload.get("story") or ""), "a história", 4000)
    if required or "city" in payload:
        partner.city = clean_required(str(payload.get("city") or ""), "a cidade", 80)
    if required or "region" in payload:
        partner.region = clean_required(str(payload.get("region") or ""), "a região", 80)
    if required or "highlight_hex" in payload:
        partner.highlight_hex = clean_hex(str(payload.get("highlight_hex") or ""))


def _claim_slug(db: Session, slug: str, current: UUID | None) -> None:
    query = select(Partner.id).where(Partner.brand_slug == slug)
    if current is not None:
        query = query.where(Partner.id != current)
    if db.scalar(query) is not None:
        raise MarketplaceError(409, "já existe parceiro com este slug")


def create_partner(db: Session, payload: dict) -> dict:
    partner_type = str(payload.get("partner_type") or "").strip().casefold()
    if partner_type not in PARTNER_TYPES:
        raise MarketplaceError(400, "tipo de parceiro inválido")
    email = str(payload.get("email") or "").strip().casefold()
    if "@" not in email or email.startswith("@") or len(email) > 160:
        raise MarketplaceError(400, "e-mail inválido")
    if db.scalar(select(PartnerUser.id).where(PartnerUser.email == email)) is not None:
        raise MarketplaceError(409, "já existe usuário com este e-mail")
    fee = clean_fee(payload.get("fee_cents", 250))
    document = clean_required(str(payload.get("document") or ""), "o documento", 40)
    contact = clean_required(str(payload.get("contact") or ""), "o contato", 160)
    slug = clean_slug(str(payload.get("brand_slug") or ""))
    _claim_slug(db, slug, None)
    partner = Partner(
        partner_type=partner_type,
        brand_name="marca",
        brand_slug=slug,
        city="cidade",
        region="região",
        highlight_hex="#000000",
        document=document,
        contact=contact,
        status="invited",
        pay_recipient_id=None,
        fee_cents=fee,
    )
    _apply_brand(partner, payload, required=True)
    partner.brand_slug = slug
    db.add(partner)
    _flush(db)
    raw = secrets.token_urlsafe(32)
    expires = _now() + timedelta(days=INVITE_DAYS)
    db.add(
        PartnerUser(
            email=email,
            password_hash=None,
            partner_id=partner.id,
            invite_token_hash=hash_token(raw),
            invite_expires_at=expires,
        )
    )
    _flush(db)
    body = partner_out(partner, email)
    body["invite_link"] = f"/parceiro/convite?token={raw}"
    body["invite_expires_at"] = expires.isoformat()
    return body


def _links_out(db: Session, partner_id: UUID) -> list[dict]:
    rows = db.scalars(
        select(PartnerLink).where(PartnerLink.partner_id == partner_id).order_by(PartnerLink.created_at)
    ).all()
    return [_link_out(row) for row in rows]


def list_partners(db: Session) -> list[dict]:
    rows = db.scalars(select(Partner).order_by(Partner.created_at)).all()
    body = []
    for row in rows:
        item = partner_out(row, _email_of(db, row.id))
        item["links"] = _links_out(db, row.id)
        body.append(item)
    return body


def get_partner(db: Session, partner_id: UUID) -> dict:
    partner = _partner_or_404(db, partner_id)
    body = partner_out(partner, _email_of(db, partner.id))
    body["links"] = _links_out(db, partner.id)
    return body


def update_partner(db: Session, partner_id: UUID, payload: dict) -> dict:
    partner = _partner_or_404(db, partner_id)
    if not payload:
        return partner_out(partner, _email_of(db, partner.id))
    if "brand_slug" in payload:
        slug = clean_slug(str(payload.get("brand_slug") or ""))
        _claim_slug(db, slug, partner.id)
        payload = {**payload, "brand_slug": slug}
    _apply_brand(partner, payload, required=False)
    if "document" in payload:
        partner.document = clean_required(str(payload.get("document") or ""), "o documento", 40)
    if "contact" in payload:
        partner.contact = clean_required(str(payload.get("contact") or ""), "o contato", 160)
    if "fee_cents" in payload:
        partner.fee_cents = clean_fee(payload.get("fee_cents"))
    partner.updated_at = _now()
    _flush(db)
    return partner_out(partner, _email_of(db, partner.id))


def pause_partner(db: Session, partner_id: UUID) -> dict:
    partner = _partner_or_404(db, partner_id)
    partner.status = "paused"
    partner.updated_at = _now()
    _flush(db)
    return partner_out(partner, _email_of(db, partner.id))


def issue_access_link(db: Session, partner_id: UUID) -> dict:
    partner = _partner_or_404(db, partner_id)
    if partner.status == "paused":
        raise MarketplaceError(409, "parceiro pausado não recebe link de acesso")
    user = db.scalar(select(PartnerUser).where(PartnerUser.partner_id == partner.id))
    if user is None:
        raise MarketplaceError(404, "não encontrado")
    raw = secrets.token_urlsafe(32)
    expires = _now() + timedelta(days=INVITE_DAYS)
    user.invite_token_hash = hash_token(raw)
    user.invite_expires_at = expires
    user.updated_at = _now()
    _flush(db)
    return {
        "invite_link": f"/parceiro/convite?token={raw}",
        "invite_expires_at": expires.isoformat(),
        "email": user.email,
    }


def activate_partner(db: Session, partner_id: UUID) -> dict:
    partner = _partner_or_404(db, partner_id)
    if partner.status != "paused":
        raise MarketplaceError(409, "só um parceiro pausado pode ser reativado")
    user = db.scalar(select(PartnerUser).where(PartnerUser.partner_id == partner.id))
    if user is None:
        raise MarketplaceError(404, "não encontrado")
    partner.status = "active" if user.password_hash else "invited"
    partner.updated_at = _now()
    _flush(db)
    return partner_out(partner, user.email)


def _link_out(row: PartnerLink) -> dict:
    return {
        "id": str(row.id),
        "partner_id": str(row.partner_id),
        "category": row.category,
        "link_type": row.link_type,
        "starts_on": row.starts_on.isoformat(),
        "ends_on": row.ends_on.isoformat() if row.ends_on else None,
    }


def _exclusive_clash(
    db: Session,
    *,
    category: str,
    link_type: str,
    starts_on,
    ends_on,
    partner_id: UUID,
) -> None:
    if link_type != "exclusive":
        return
    rows = db.scalars(
        select(PartnerLink).where(
            PartnerLink.category == category,
            PartnerLink.link_type == "exclusive",
        )
    ).all()
    for row in rows:
        if row.partner_id == partner_id:
            continue
        owner = db.get(Partner, row.partner_id)
        if owner is None or owner.status == "paused":
            continue
        if periods_overlap(starts_on, ends_on, row.starts_on, row.ends_on):
            raise MarketplaceError(409, "já há um parceiro exclusivo nesta categoria neste período")


def create_link(db: Session, partner_id: UUID, payload: dict) -> dict:
    partner = _partner_or_404(db, partner_id)
    category = clean_category(str(payload.get("category") or ""))
    link_type = str(payload.get("link_type") or "").strip().casefold()
    if link_type not in LINK_TYPES:
        raise MarketplaceError(400, "tipo de vínculo inválido")
    starts_on = payload.get("starts_on")
    ends_on = payload.get("ends_on")
    if ends_on is not None and ends_on < starts_on:
        raise MarketplaceError(400, "o fim do vínculo não pode ser anterior ao início")
    _exclusive_clash(
        db,
        category=category,
        link_type=link_type,
        starts_on=starts_on,
        ends_on=ends_on,
        partner_id=partner.id,
    )
    row = PartnerLink(
        partner_id=partner.id,
        category=category,
        link_type=link_type,
        starts_on=starts_on,
        ends_on=ends_on,
    )
    db.add(row)
    _flush(db)
    return _link_out(row)


def end_link(db: Session, partner_id: UUID, link_id: UUID, payload: dict) -> dict:
    _partner_or_404(db, partner_id)
    row = db.get(PartnerLink, link_id)
    if row is None or row.partner_id != partner_id:
        raise MarketplaceError(404, "não encontrado")
    ends_on = payload.get("ends_on") or datetime.now(UTC).date()
    if ends_on < row.starts_on:
        raise MarketplaceError(400, "o fim do vínculo não pode ser anterior ao início")
    row.ends_on = ends_on
    row.updated_at = _now()
    _flush(db)
    return _link_out(row)


def _pairings_of(db: Session, product_id: UUID) -> list[ProductPairing]:
    return list(
        db.scalars(
            select(ProductPairing).where(ProductPairing.product_id == product_id).order_by(ProductPairing.created_at)
        ).all()
    )


def product_out(db: Session, product: PartnerProduct) -> dict:
    updated = product.updated_at
    if updated is None:
        db.refresh(product)
        updated = product.updated_at or _now()
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=UTC)
    return {
        "id": str(product.id),
        "partner_id": str(product.partner_id),
        "category": product.category,
        "name": product.name,
        "description": product.description,
        "photos": list(product.photos or []),
        "price_cents": product.price_cents,
        "is_available": product.is_available,
        "delivery_cities": list(product.delivery_cities or []),
        "delivery_districts": list(product.delivery_districts or []),
        "delivery_cep_prefixes": list(product.delivery_cep_prefixes or []),
        "delivery_days": product.delivery_days,
        "freight_cents": product.freight_cents,
        "perishable": product.perishable,
        "status": product.status,
        "updated_at": updated.isoformat(),
        "pairings": [
            {
                "id": str(row.id),
                "house_product_slug": row.house_product_slug,
                "house_product_name": published_product_name(db, row.house_product_slug),
                "reason": row.reason,
            }
            for row in _pairings_of(db, product.id)
        ],
    }


def _own_product(db: Session, partner_id: UUID, product_id: UUID) -> PartnerProduct:
    product = db.get(PartnerProduct, product_id)
    if product is None or product.partner_id != partner_id:
        raise MarketplaceError(404, "não encontrado")
    return product


def _clean_pairings(raw: object) -> list[tuple[str, str]]:
    if not isinstance(raw, list):
        raise MarketplaceError(400, "as harmonizações precisam ser uma lista")
    cleaned: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise MarketplaceError(400, "harmonização inválida")
        slug = " ".join(str(item.get("house_product_slug") or "").split()).casefold()
        reason = " ".join(str(item.get("reason") or "").split())
        if not slug or len(slug) > 80:
            raise MarketplaceError(400, "a harmonização precisa do pão da casa")
        if not reason or len(reason) > 400:
            raise MarketplaceError(400, "a harmonização precisa do motivo")
        cleaned.append((slug, reason))
    return cleaned


def _replace_pairings(db: Session, product: PartnerProduct, pairings: list[tuple[str, str]]) -> None:
    for row in _pairings_of(db, product.id):
        db.delete(row)
    _flush(db)
    for slug, reason in pairings:
        db.add(ProductPairing(product_id=product.id, house_product_slug=slug, reason=reason))
    _flush(db)


def _owned_photos(db: Session, partner_id: UUID, raw: object) -> list[str]:
    photos = clean_photos(raw if raw is not None else [])
    for url in photos:
        media_id = media_id_of(url)
        if media_id is None:
            continue
        row = db.get(PartnerMedia, media_id)
        if row is None or row.partner_id != partner_id:
            raise MarketplaceError(400, "a foto não pertence a este parceiro")
    return photos


def _assign_product(db: Session, partner_id: UUID, product: PartnerProduct, payload: dict) -> None:
    if "category" in payload:
        product.category = clean_category(str(payload.get("category") or ""))
    if "name" in payload or "description" in payload:
        name = product.name if "name" not in payload else clean_required(str(payload.get("name") or ""), "o nome", 120)
        description = (
            product.description
            if "description" not in payload
            else clean_optional_text(str(payload.get("description") or ""), "a descrição", 4000)
        )
        refuse_bakery_text(name, description)
        product.name = name
        product.description = description
    if "photos" in payload:
        product.photos = _owned_photos(db, partner_id, payload.get("photos"))
    if "price_cents" in payload:
        product.price_cents = clean_money(payload.get("price_cents"), "o preço")
    if "is_available" in payload:
        if not isinstance(payload.get("is_available"), bool):
            raise MarketplaceError(400, "a disponibilidade precisa ser sim ou não")
        product.is_available = payload["is_available"]
    if "delivery_cities" in payload:
        product.delivery_cities = clean_names(payload.get("delivery_cities"), "a cidade de entrega")
    if "delivery_districts" in payload:
        product.delivery_districts = clean_names(payload.get("delivery_districts"), "o bairro de entrega")
    if "delivery_cep_prefixes" in payload:
        product.delivery_cep_prefixes = clean_ceps(payload.get("delivery_cep_prefixes"))
    if "delivery_days" in payload and payload.get("delivery_days") is not None:
        product.delivery_days = clean_days(payload.get("delivery_days"))
    if "freight_cents" in payload and payload.get("freight_cents") is not None:
        product.freight_cents = clean_money(payload.get("freight_cents"), "o frete")
    if "perishable" in payload:
        if not isinstance(payload.get("perishable"), bool):
            raise MarketplaceError(400, "perecível precisa ser sim ou não")
        product.perishable = payload["perishable"]


def _require_ready(db: Session, product: PartnerProduct) -> None:
    refuse_bakery_text(product.name, product.description)
    clean_category(product.category)
    if not list(product.photos or []):
        raise MarketplaceError(400, "falta pelo menos uma foto para enviar à avaliação")
    if not delivery_complete(
        list(product.delivery_cities or []),
        list(product.delivery_districts or []),
        list(product.delivery_cep_prefixes or []),
        product.delivery_days,
        product.freight_cents,
    ):
        raise MarketplaceError(400, "a entrega precisa de área, prazo e frete")
    pairings = _pairings_of(db, product.id)
    if not pairings:
        raise MarketplaceError(400, "falta a harmonização com um pão da casa")
    for pairing in pairings:
        if not published_slug_exists(db, pairing.house_product_slug):
            raise MarketplaceError(400, "a harmonização precisa de um pão da casa publicado")


def create_product(db: Session, partner: Partner, payload: dict) -> dict:
    _active(partner)
    name = clean_required(str(payload.get("name") or ""), "o nome", 120)
    description = clean_optional_text(str(payload.get("description") or ""), "a descrição", 4000)
    refuse_bakery_text(name, description)
    product = PartnerProduct(
        partner_id=partner.id,
        category=clean_category(str(payload.get("category") or "")),
        name=name,
        description=description,
        photos=_owned_photos(db, partner.id, payload.get("photos") or []),
        price_cents=clean_money(payload.get("price_cents"), "o preço"),
        is_available=True,
        delivery_cities=clean_names(payload.get("delivery_cities") or [], "a cidade de entrega"),
        delivery_districts=clean_names(payload.get("delivery_districts") or [], "o bairro de entrega"),
        delivery_cep_prefixes=clean_ceps(payload.get("delivery_cep_prefixes") or []),
        perishable=bool(payload.get("perishable")),
        status="draft",
    )
    if payload.get("delivery_days") is not None:
        product.delivery_days = clean_days(payload.get("delivery_days"))
    if payload.get("freight_cents") is not None:
        product.freight_cents = clean_money(payload.get("freight_cents"), "o frete")
    if "is_available" in payload:
        if not isinstance(payload.get("is_available"), bool):
            raise MarketplaceError(400, "a disponibilidade precisa ser sim ou não")
        product.is_available = payload["is_available"]
    db.add(product)
    _flush(db)
    _replace_pairings(db, product, _clean_pairings(payload.get("pairings") or []))
    return product_out(db, product)


def update_product(db: Session, partner: Partner, product_id: UUID, payload: dict) -> dict:
    _active(partner)
    product = _own_product(db, partner.id, product_id)
    if product.status == "paused":
        raise MarketplaceError(409, "produto pausado não é editado pelo parceiro")
    if not payload:
        return product_out(db, product)
    previous = product.status
    _assign_product(db, partner.id, product, payload)
    if "pairings" in payload:
        _replace_pairings(db, product, _clean_pairings(payload.get("pairings")))
    if previous in {"approved", "pending"}:
        _require_ready(db, product)
    if previous == "approved":
        product.status = "pending"
    product.updated_at = _now()
    _flush(db)
    return product_out(db, product)


def submit_product(db: Session, partner: Partner, product_id: UUID) -> dict:
    _active(partner)
    product = _own_product(db, partner.id, product_id)
    if product.status not in {"draft", "returned", "rejected"}:
        raise MarketplaceError(409, "este produto não pode ser enviado agora")
    _require_ready(db, product)
    product.status = "pending"
    product.updated_at = _now()
    _flush(db)
    return product_out(db, product)


def list_my_products(db: Session, partner: Partner) -> list[dict]:
    rows = db.scalars(
        select(PartnerProduct)
        .where(PartnerProduct.partner_id == partner.id)
        .order_by(PartnerProduct.created_at)
    ).all()
    return [product_out(db, row) for row in rows]


def list_reviews(db: Session, partner: Partner, product_id: UUID) -> list[dict]:
    product = _own_product(db, partner.id, product_id)
    rows = db.scalars(
        select(ProductReview).where(ProductReview.product_id == product.id).order_by(ProductReview.reviewed_at)
    ).all()
    return [_review_out(row) for row in rows]


def list_product_reviews(db: Session, product_id: UUID) -> list[dict]:
    product = db.get(PartnerProduct, product_id)
    if product is None:
        raise MarketplaceError(404, "não encontrado")
    rows = db.scalars(
        select(ProductReview)
        .where(ProductReview.product_id == product.id)
        .order_by(ProductReview.reviewed_at.desc(), ProductReview.created_at.desc())
    ).all()
    return [_review_out(row) for row in rows]


def list_products_admin(db: Session, status: str | None) -> list[dict]:
    query = select(PartnerProduct).order_by(PartnerProduct.created_at)
    if status:
        query = query.where(PartnerProduct.status == status.strip().casefold())
    return [product_out(db, row) for row in db.scalars(query).all()]


def review_product(db: Session, product_id: UUID, payload: dict, reviewer: str) -> dict:
    product = db.get(PartnerProduct, product_id)
    if product is None:
        raise MarketplaceError(404, "não encontrado")
    if product.status != "pending":
        raise MarketplaceError(409, "só um produto pendente entra na avaliação")
    quality, visual, complementarity = clean_scores(
        payload.get("quality"), payload.get("visual"), payload.get("complementarity")
    )
    decision, note = clean_decision(str(payload.get("decision") or ""), str(payload.get("note") or ""))
    status = {"approve": "approved", "return": "returned", "reject": "rejected"}[decision]
    review = ProductReview(
        product_id=product.id,
        quality=quality,
        visual=visual,
        complementarity=complementarity,
        note=note,
        decision=decision,
        reviewer_ref=reviewer[:120],
        reviewed_at=_now(),
    )
    db.add(review)
    product.status = status
    product.updated_at = _now()
    _flush(db)
    body = product_out(db, product)
    body["review"] = _review_out(review)
    return body


_OPEN_COMBO = frozenset({"pending", "approved", "returned"})
_COMBO_STATUS = {"approve": "approved", "return": "returned", "reject": "rejected"}


def _combo_out(db: Session, row: ProductCombo, product_name: str | None = None) -> dict:
    if product_name is None:
        product = db.get(PartnerProduct, row.partner_product_id)
        product_name = product.name if product is not None else None
    reviewed = row.reviewed_at.isoformat() if row.reviewed_at is not None else None
    return {
        "id": str(row.id),
        "partner_id": str(row.partner_id),
        "partner_product_id": str(row.partner_product_id),
        "partner_product_name": product_name,
        "house_product_slug": row.house_product_slug,
        "house_product_name": published_product_name(db, row.house_product_slug),
        "reason": row.reason,
        "status": row.status,
        "review_note": row.review_note,
        "reviewed_at": reviewed,
        "house_unit_price_cents": row.house_unit_price_cents,
        "updated_at": row.updated_at.isoformat(),
    }


def _approved_product(db: Session, partner: Partner, product_id: UUID) -> PartnerProduct:
    product = db.get(PartnerProduct, product_id)
    if product is None or product.partner_id != partner.id:
        raise MarketplaceError(404, "não encontrado")
    if product.status != "approved":
        raise MarketplaceError(400, "só um produto aprovado entra na combinação")
    return product


def _published_bread(db: Session, slug: object) -> str:
    token = str(slug or "").strip()
    if not published_slug_exists(db, token):
        raise MarketplaceError(400, "a combinação precisa de um pão da casa publicado")
    return token


def _combo_reason(value: object) -> str:
    return clean_required(str(value or ""), "o motivo", 400)


def _refuse_open_pair(db: Session, product_id: UUID, slug: str, current: UUID | None = None) -> None:
    query = select(ProductCombo.id).where(
        ProductCombo.partner_product_id == product_id,
        ProductCombo.house_product_slug == slug,
        ProductCombo.status.in_(_OPEN_COMBO),
    )
    if current is not None:
        query = query.where(ProductCombo.id != current)
    if db.scalar(query) is not None:
        raise MarketplaceError(409, "já existe uma combinação deste produto com este pão")


def list_my_combos(db: Session, partner: Partner) -> list[dict]:
    rows = db.scalars(
        select(ProductCombo)
        .where(ProductCombo.partner_id == partner.id)
        .order_by(ProductCombo.created_at.desc(), ProductCombo.id.desc())
    ).all()
    return [_combo_out(db, row) for row in rows]


def create_combo(db: Session, partner: Partner, payload: dict) -> dict:
    _active(partner)
    product = _approved_product(db, partner, payload["partner_product_id"])
    slug = _published_bread(db, payload.get("house_product_slug"))
    reason = _combo_reason(payload.get("reason"))
    _refuse_open_pair(db, product.id, slug)
    row = ProductCombo(
        partner_id=partner.id,
        partner_product_id=product.id,
        house_product_slug=slug,
        reason=reason,
        status="pending",
    )
    db.add(row)
    _flush(db)
    return _combo_out(db, row, product.name)


def update_combo(db: Session, partner: Partner, combo_id: UUID, payload: dict) -> dict:
    _active(partner)
    row = db.get(ProductCombo, combo_id)
    if row is None or row.partner_id != partner.id:
        raise MarketplaceError(404, "não encontrado")
    if row.status != "returned":
        raise MarketplaceError(409, "só uma combinação devolvida pode ser reenviada")
    product = _approved_product(db, partner, row.partner_product_id)
    slug = _published_bread(db, payload.get("house_product_slug"))
    reason = _combo_reason(payload.get("reason"))
    _refuse_open_pair(db, product.id, slug, row.id)
    row.house_product_slug = slug
    row.reason = reason
    row.status = "pending"
    row.review_note = None
    row.reviewer_ref = None
    row.reviewed_at = None
    row.updated_at = _now()
    _flush(db)
    return _combo_out(db, row, product.name)


def list_combos_admin(db: Session) -> list[dict]:
    rows = db.scalars(
        select(ProductCombo).order_by(ProductCombo.created_at.desc(), ProductCombo.id.desc())
    ).all()
    return [_combo_out(db, row) for row in rows]


def review_combo(db: Session, combo_id: UUID, payload: dict, reviewer: str) -> dict:
    row = db.get(ProductCombo, combo_id)
    if row is None:
        raise MarketplaceError(404, "não encontrado")
    if row.status != "pending":
        raise MarketplaceError(409, "só uma combinação pendente entra na avaliação")
    decision, note = clean_decision(str(payload.get("decision") or ""), str(payload.get("note") or ""))
    row.status = _COMBO_STATUS[decision]
    row.review_note = note
    row.reviewer_ref = reviewer[:120]
    row.reviewed_at = _now()
    row.updated_at = _now()
    _flush(db)
    return _combo_out(db, row)


def pause_product(db: Session, product_id: UUID) -> dict:
    product = db.get(PartnerProduct, product_id)
    if product is None:
        raise MarketplaceError(404, "não encontrado")
    product.status = "paused"
    product.updated_at = _now()
    _flush(db)
    return product_out(db, product)


def _review_out(row: ProductReview) -> dict:
    return {
        "id": str(row.id),
        "quality": row.quality,
        "visual": row.visual,
        "complementarity": row.complementarity,
        "note": row.note,
        "decision": row.decision,
        "reviewer_ref": row.reviewer_ref,
        "reviewed_at": row.reviewed_at.isoformat(),
    }


def accept_invite(db: Session, token: str, password: str) -> tuple[dict, str, str]:
    if len(password or "") < 8:
        raise MarketplaceError(400, "a senha precisa de pelo menos 8 caracteres")
    user = db.scalar(select(PartnerUser).where(PartnerUser.invite_token_hash == hash_token(token.strip())))
    if user is None or user.invite_expires_at is None:
        raise MarketplaceError(400, "convite inválido ou vencido")
    expires = user.invite_expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < _now():
        raise MarketplaceError(400, "convite inválido ou vencido")
    partner = db.get(Partner, user.partner_id)
    if partner is None:
        raise MarketplaceError(400, "convite inválido ou vencido")
    user.password_hash = hash_password(password)
    user.invite_token_hash = None
    user.invite_expires_at = None
    user.updated_at = _now()
    if partner.status == "invited":
        partner.status = "active"
        partner.updated_at = _now()
    drop_sessions(db, user)
    raw, csrf = start_session(db, user)
    _flush(db)
    return {"csrf_token": csrf, "email": user.email, "partner": partner_out(partner, user.email)}, raw, csrf


def login(db: Session, email: str, password: str) -> tuple[dict, str, str]:
    user = db.scalar(select(PartnerUser).where(PartnerUser.email == email.strip().casefold()))
    if user is None or not user.password_hash or not verify_password(user.password_hash, password or ""):
        raise MarketplaceError(401, "e-mail ou senha não conferem")
    partner = db.get(Partner, user.partner_id)
    if partner is None:
        raise MarketplaceError(401, "e-mail ou senha não conferem")
    raw, csrf = start_session(db, user)
    return {"csrf_token": csrf, "email": user.email, "partner": partner_out(partner, user.email)}, raw, csrf


def me(partner: Partner, user: PartnerUser, csrf: str) -> dict:
    return {"csrf_token": csrf, "email": user.email, "partner": partner_out(partner, user.email)}


def store_partner_media(db: Session, settings, partner: Partner, payload: bytes) -> dict:
    _active(partner)
    try:
        stored_name, backend, content_type, size, width, height = store_image(settings, payload)
    except ProductError as exc:
        raise MarketplaceError(400, str(exc)) from None
    row = PartnerMedia(
        partner_id=partner.id,
        stored_name=stored_name,
        storage_backend=backend,
        content_type=content_type,
        size_bytes=size,
        width=width,
        height=height,
    )
    db.add(row)
    _flush(db)
    return {"id": str(row.id), "url": f"/api/v1/marketplace/media/{row.id}"}


def partner_media_response(db: Session, settings, media_id: UUID) -> Response:
    row = db.get(PartnerMedia, media_id)
    if row is None:
        raise MarketplaceError(404, "não encontrado")
    try:
        opened = open_media(settings, row.stored_name, row.storage_backend)
    except ProductError:
        raise MarketplaceError(404, "não encontrado") from None
    headers = {
        "Cache-Control": "public, max-age=31536000, immutable",
        "X-Content-Type-Options": "nosniff",
    }
    if hasattr(opened, "read_bytes"):
        return FileResponse(opened, media_type=row.content_type, headers=headers)
    return Response(content=opened, media_type=row.content_type, headers=headers)


_LINK_RANK = {"exclusive": 0, "partial": 1, "none": 2}
_STORE_TZ = ZoneInfo("America/Sao_Paulo")


def _store_today() -> date:
    return datetime.now(_STORE_TZ).date()


def _public_brand(partner: Partner) -> dict:
    return {
        "brand_name": partner.brand_name,
        "brand_slug": partner.brand_slug,
        "highlight_hex": partner.highlight_hex,
        "logo_url": partner.logo_url or "",
    }


def _public_delivery(product: PartnerProduct) -> dict:
    return {
        "cities": list(product.delivery_cities or []),
        "districts": list(product.delivery_districts or []),
        "days": product.delivery_days,
        "freight_cents": product.freight_cents,
        "perishable": bool(product.perishable),
    }


def _link_open(link: PartnerLink, today: date) -> bool:
    if link.starts_on > today:
        return False
    return link.ends_on is None or link.ends_on >= today


def _best_open_link(links: list[PartnerLink], partner_id: UUID, category: str, today: date) -> PartnerLink | None:
    found = [
        link
        for link in links
        if link.partner_id == partner_id and link.category == category and _link_open(link, today)
    ]
    if not found:
        return None
    found.sort(key=lambda link: _LINK_RANK.get(link.link_type, 9))
    return found[0]


def _public_product(product: PartnerProduct, *, why: str | None = None, partner: Partner | None = None, pairings: list | None = None) -> dict:
    body = {
        "id": str(product.id),
        "name": product.name,
        "description": product.description or "",
        "photos": [str(item) for item in (product.photos or [])],
        "price_cents": product.price_cents,
        "category": product.category,
        "delivery": _public_delivery(product),
    }
    if why is not None:
        body["why_pairs"] = why
    if partner is not None:
        body["partner"] = _public_brand(partner)
    if pairings is not None:
        body["pairings"] = pairings
    return body


def _public_combo(combo: ProductCombo, product: PartnerProduct, partner: Partner, *, house_name: str | None = None, on_partner_page: bool = False) -> dict:
    body = {
        "id": str(combo.id),
        "product_id": str(product.id),
        "product_name": product.name,
        "reason": combo.reason,
        "price_cents": product.price_cents,
        "freight_cents": product.freight_cents,
        "house_unit_price_cents": combo.house_unit_price_cents,
        "partner": _public_brand(partner),
    }
    if on_partner_page:
        body["house_product_slug"] = combo.house_product_slug
        body["house_product_name"] = house_name
    return body


def _catalog(db: Session) -> tuple[dict[UUID, Partner], list[PartnerLink], set[str], date]:
    today = _store_today()
    partners = {row.id: row for row in db.scalars(select(Partner)).all()}
    links = list(db.scalars(select(PartnerLink)).all())
    exclusive: set[str] = set()
    for link in links:
        owner = partners.get(link.partner_id)
        if (
            link.link_type == "exclusive"
            and _link_open(link, today)
            and owner is not None
            and owner.status == "active"
        ):
            exclusive.add(link.category)
    return partners, links, exclusive, today


def _visible(
    product: PartnerProduct,
    partner: Partner | None,
    links: list[PartnerLink],
    exclusive: set[str],
    today: date,
) -> PartnerLink | None:
    """Parceiro ativo, produto aprovado e disponível, vínculo vigente e exclusividade."""
    if partner is None or partner.status != "active" or product.partner_id != partner.id:
        return None
    if product.status != "approved" or not product.is_available:
        return None
    link = _best_open_link(links, partner.id, product.category, today)
    if link is None:
        return None
    if product.category in exclusive and link.link_type != "exclusive":
        return None
    return link


def public_bread(db: Session, slug: str) -> dict:
    token = (slug or "").strip()
    if not published_slug_exists(db, token):
        raise MarketplaceError(404, "não encontrado")
    partners, links, exclusive, today = _catalog(db)
    ranked: list[tuple[int, str, str, dict]] = []
    products = db.scalars(
        select(PartnerProduct).where(
            PartnerProduct.status == "approved",
            PartnerProduct.is_available.is_(True),
        )
    ).all()
    for product in products:
        partner = partners.get(product.partner_id)
        link = _visible(product, partner, links, exclusive, today)
        if link is None or partner is None:
            continue
        pairing = next((row for row in _pairings_of(db, product.id) if row.house_product_slug == token), None)
        if pairing is None:
            continue
        ranked.append(
            (
                _LINK_RANK.get(link.link_type, 9),
                partner.brand_name.casefold(),
                product.name.casefold(),
                _public_product(product, why=pairing.reason, partner=partner),
            )
        )
    ranked.sort(key=lambda item: item[:3])
    listed = [item[3] for item in ranked]
    combos: list[tuple[str, dict]] = []
    rows = db.scalars(
        select(ProductCombo).where(
            ProductCombo.house_product_slug == token,
            ProductCombo.status == "approved",
        )
    ).all()
    for combo in rows:
        product = db.get(PartnerProduct, combo.partner_product_id)
        partner = partners.get(combo.partner_id)
        if product is None or _visible(product, partner, links, exclusive, today) is None or partner is None:
            continue
        combos.append((product.name.casefold(), _public_combo(combo, product, partner)))
    combos.sort(key=lambda item: item[0])
    return {
        "products": listed,
        "combos": [item[1] for item in combos],
        "covered_categories": list(dict.fromkeys(item["category"] for item in listed)),
    }


def public_partner(db: Session, slug: str) -> dict:
    token = (slug or "").strip()
    partner = db.scalar(select(Partner).where(Partner.brand_slug == token))
    if partner is None or partner.status != "active":
        raise MarketplaceError(404, "não encontrado")
    partners, links, exclusive, today = _catalog(db)
    products = db.scalars(
        select(PartnerProduct)
        .where(
            PartnerProduct.partner_id == partner.id,
            PartnerProduct.status == "approved",
            PartnerProduct.is_available.is_(True),
        )
        .order_by(PartnerProduct.name, PartnerProduct.id)
    ).all()
    listed = []
    for product in products:
        if _visible(product, partner, links, exclusive, today) is None:
            continue
        pairings = []
        for row in _pairings_of(db, product.id):
            house_name = published_product_name(db, row.house_product_slug)
            if house_name is None:
                continue
            pairings.append(
                {
                    "house_product_slug": row.house_product_slug,
                    "house_product_name": house_name,
                    "reason": row.reason,
                }
            )
        listed.append(_public_product(product, pairings=pairings))
    combos: list[tuple[str, dict]] = []
    rows = db.scalars(
        select(ProductCombo).where(
            ProductCombo.partner_id == partner.id,
            ProductCombo.status == "approved",
        )
    ).all()
    for combo in rows:
        house_name = published_product_name(db, combo.house_product_slug)
        if house_name is None:
            continue
        product = db.get(PartnerProduct, combo.partner_product_id)
        if product is None or _visible(product, partner, links, exclusive, today) is None:
            continue
        combos.append(
            (
                product.name.casefold(),
                _public_combo(combo, product, partner, house_name=house_name, on_partner_page=True),
            )
        )
    combos.sort(key=lambda item: item[0])
    return {
        "partner": {
            **_public_brand(partner),
            "photo_url": partner.photo_url or "",
            "story": partner.story or "",
            "city": partner.city,
            "region": partner.region,
        },
        "products": listed,
        "combos": [item[1] for item in combos],
    }


def update_profile(db: Session, partner: Partner, user: PartnerUser, payload: dict) -> dict:
    _active(partner)
    if "brand_slug" in payload:
        slug = clean_slug(str(payload.get("brand_slug") or ""))
        _claim_slug(db, slug, partner.id)
        payload = {**payload, "brand_slug": slug}
    _apply_brand(partner, payload, required=False)
    partner.updated_at = _now()
    _flush(db)
    return partner_out(partner, user.email)


def hash_lead_ip(ip: str, secret: str) -> str:
    return hmac.new(
        (secret or "").encode("utf-8"),
        (ip or "unknown").encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _lead_whatsapp_ok(raw: str) -> bool:
    digits = re.sub(r"\D", "", raw)
    digits = re.sub(r"^55(?=\d{10,11}$)", "", digits)
    return len(digits) in {10, 11}


def _clean_lead_field(value: object, label: str, max_len: int, *, required: bool = True) -> str:
    text = str(value or "").strip()
    if not text:
        if required:
            raise MarketplaceError(422, f"{label} é obrigatório")
        return ""
    if len(text) > max_len:
        raise MarketplaceError(422, f"{label} excede {max_len} caracteres")
    return text


# Alinhado a features/b2b/partnerTerms.ts — mudar nos dois lugares juntos.
TERMS_VERSION = "2026-11-25"


def _lead_out(row: PartnerLead) -> dict:
    return {
        "id": str(row.id),
        "created_at": row.created_at.isoformat(),
        "name": row.name,
        "brand": row.brand,
        "category": row.category,
        "city": row.city,
        "whatsapp": row.whatsapp,
        "email": row.email,
        "link": row.link or "",
        "message": row.message,
        "consent_at": row.consent_at.isoformat(),
        "status": row.status,
        "terms_version": row.terms_version,
        "terms_accepted_at": row.terms_accepted_at.isoformat() if row.terms_accepted_at else None,
    }


def create_partner_lead(db: Session, settings: Settings, payload: dict, ip: str) -> dict:
    """Grava interesse /b2b. website preenchido = robô: descarta e responde ok."""
    if str(payload.get("website") or "").strip():
        return {"ok": True}

    name = _clean_lead_field(payload.get("name"), "nome", 120)
    brand = _clean_lead_field(payload.get("brand"), "marca", 120)
    category = str(payload.get("category") or "").strip()
    if category not in LEAD_CATEGORIES:
        raise MarketplaceError(422, "categoria inválida")
    city = _clean_lead_field(payload.get("city"), "cidade", 80)
    whatsapp = _clean_lead_field(payload.get("whatsapp"), "WhatsApp", 40)
    if not _lead_whatsapp_ok(whatsapp):
        raise MarketplaceError(422, "WhatsApp com DDD inválido")
    email = _clean_lead_field(payload.get("email"), "e-mail", 160)
    if not LEAD_EMAIL_RE.match(email):
        raise MarketplaceError(422, "e-mail inválido")
    link = _clean_lead_field(payload.get("link"), "link", 200, required=False)
    message = _clean_lead_field(payload.get("message"), "mensagem", 1500)
    if payload.get("consent") is not True:
        raise MarketplaceError(422, "consentimento obrigatório")

    terms_version = payload.get("terms_version")
    if terms_version is None or (isinstance(terms_version, str) and not terms_version.strip()):
        raise MarketplaceError(422, "Para enviar, aceite os termos de parceria.")
    terms_version = str(terms_version).strip()
    if terms_version != TERMS_VERSION:
        raise MarketplaceError(409, "Os termos mudaram. Recarregue a página.")

    ip_hash = hash_lead_ip(ip or "unknown", settings.admin_session_secret)
    since = _now() - LEAD_RATE_WINDOW
    recent = db.scalar(
        select(func.count())
        .select_from(PartnerLead)
        .where(PartnerLead.ip_hash == ip_hash, PartnerLead.created_at >= since)
    )
    if (recent or 0) >= LEAD_RATE_LIMIT:
        raise MarketplaceError(429, "limite de envios atingido; tente mais tarde")

    accepted_at = _now()
    row = PartnerLead(
        name=name,
        brand=brand,
        category=category,
        city=city,
        whatsapp=whatsapp,
        email=email,
        link=link,
        message=message,
        consent_at=accepted_at,
        ip_hash=ip_hash,
        status="new",
        terms_version=terms_version,
        terms_accepted_at=accepted_at,
    )
    db.add(row)
    _flush(db)
    try:
        with db.begin_nested():
            enqueue_partner_lead_notice(
                db,
                settings,
                {
                    "name": name,
                    "brand": brand,
                    "category": category,
                    "city": city,
                    "whatsapp": whatsapp,
                    "email": email,
                    "link": link,
                },
                lead_id=str(row.id),
            )
    except Exception as exc:
        # Interessado já gravado; savepoint evita deixar a transação quebrada.
        _log.warning("aviso de interessado falhou: %s", type(exc).__name__)
    return {"ok": True}


def list_partner_leads(db: Session) -> list[dict]:
    rows = db.scalars(select(PartnerLead).order_by(PartnerLead.created_at.desc())).all()
    return [_lead_out(row) for row in rows]


def update_partner_lead_status(db: Session, lead_id: UUID, status: str) -> dict:
    value = str(status or "").strip()
    if value not in LEAD_STATUSES:
        raise MarketplaceError(422, "status inválido")
    row = db.get(PartnerLead, lead_id)
    if row is None:
        raise MarketplaceError(404, "não encontrado")
    row.status = value
    _flush(db)
    return _lead_out(row)


# --- Pedido da combo (M8) ---------------------------------------------------------------------------

PARTNER_ORDER_OPEN = frozenset({"submitted", "accepted"})
REFUSE_REASON_MAX = 200


@dataclass(frozen=True)
class ComboSale:
    combo: ProductCombo
    partner: Partner
    product: PartnerProduct


def set_combo_house_price(db: Session, combo_id: UUID, value: object) -> dict:
    """Preço do pão nesta combo (acordo da Loja). Nulo volta ao preço da vitrine."""
    row = db.get(ProductCombo, combo_id)
    if row is None:
        raise MarketplaceError(404, "não encontrado")
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value <= 0):
        raise MarketplaceError(400, "o preço do pão precisa ser maior que zero, ou vazio para usar o da vitrine")
    row.house_unit_price_cents = value
    row.updated_at = _now()
    _flush(db)
    return _combo_out(db, row)


def combo_for_sale(db: Session, combo_id: UUID) -> ComboSale:
    """Combinação aprovada, com pão publicado e parceiro/produto visíveis. Qualquer falha é 404."""
    row = db.get(ProductCombo, combo_id)
    if row is None or row.status != "approved":
        raise MarketplaceError(404, "não encontrado")
    if not published_slug_exists(db, row.house_product_slug):
        raise MarketplaceError(404, "não encontrado")
    partners, links, exclusive, today = _catalog(db)
    product = db.get(PartnerProduct, row.partner_product_id)
    partner = partners.get(row.partner_id)
    if product is None or partner is None or _visible(product, partner, links, exclusive, today) is None:
        raise MarketplaceError(404, "não encontrado")
    return ComboSale(combo=row, partner=partner, product=product)


def combo_summary(db: Session, sale: ComboSale) -> dict:
    """Resumo público da combo. As variações do pão são acrescentadas pela ponte com a Loja."""
    combo, partner, product = sale.combo, sale.partner, sale.product
    return {
        "id": str(combo.id),
        "reason": combo.reason,
        "bread": {
            "slug": combo.house_product_slug,
            "name": published_product_name(db, combo.house_product_slug) or combo.house_product_slug,
        },
        "product": {
            "id": str(product.id),
            "name": product.name,
            "description": product.description or "",
            "photos": [str(item) for item in (product.photos or [])],
            "price_cents": product.price_cents,
        },
        "partner": _public_brand(partner),
        "delivery": _public_delivery(product),
        "house_unit_price_cents": combo.house_unit_price_cents,
    }


def partner_delivers(product: PartnerProduct, city: str | None, district: str | None) -> bool:
    """Áreas vazias = sem restrição. Senão a cidade ou o bairro precisa coincidir (sem acento)."""
    cities = {fold_text(item) for item in (product.delivery_cities or [])}
    districts = {fold_text(item) for item in (product.delivery_districts or [])}
    if not cities and not districts:
        return True
    if city and fold_text(city) in cities:
        return True
    return bool(district) and fold_text(district) in districts


def assert_partner_delivery(
    product: PartnerProduct, *, city: str | None, district: str | None, requested_date: date
) -> None:
    if not partner_delivers(product, city, district):
        raise MarketplaceError(422, "este parceiro não entrega na cidade ou no bairro informado")
    days = product.delivery_days or 0
    if requested_date < _store_today() + timedelta(days=days):
        raise MarketplaceError(
            422,
            f"este parceiro precisa de pelo menos {days} {'dia' if days == 1 else 'dias'} para entregar; escolha uma data mais adiante",
        )


def partner_email(db: Session, partner_id: UUID) -> str | None:
    return _email_of(db, partner_id)


def _new_partner_order_reference(db: Session) -> str:
    for _ in range(10):
        reference = "PO-" + secrets.token_hex(4).upper()
        if db.scalar(select(PartnerOrder.id).where(PartnerOrder.public_reference == reference)) is None:
            return reference
    raise MarketplaceError(409, "não foi possível gerar a referência do pedido")


def create_partner_order(
    db: Session,
    sale: ComboSale,
    *,
    combo_ref: UUID,
    house_order_id: UUID,
    requested_date: date,
    customer_name: str,
    address_line: str,
    item_quantity: int,
    accept_deadline: datetime | None,
    idempotency_key: str | None = None,
) -> PartnerOrder:
    """Parte do parceiro, com os valores congelados no momento do pedido. Não confirma a transação."""
    if isinstance(item_quantity, bool) or not isinstance(item_quantity, int) or not 1 <= item_quantity <= 10:
        raise MarketplaceError(422, "a quantidade do item precisa ser de 1 a 10")
    combo, partner, product = sale.combo, sale.partner, sale.product
    row = PartnerOrder(
        public_reference=_new_partner_order_reference(db),
        combo_ref=combo_ref,
        partner_id=partner.id,
        partner_product_id=product.id,
        product_name=product.name,
        house_product_name=published_product_name(db, combo.house_product_slug) or combo.house_product_slug,
        house_order_id=house_order_id,
        requested_date=requested_date,
        customer_name=customer_name[:160],
        address_line=address_line[:400],
        item_quantity=item_quantity,
        item_cents=item_quantity * product.price_cents,
        freight_cents=product.freight_cents,
        fee_cents=partner.fee_cents,
        status="submitted",
        accept_deadline=accept_deadline,
        submit_idempotency_key=(idempotency_key or None),
    )
    db.add(row)
    _flush(db)
    return row


def _accept_window_closed(row: PartnerOrder, now: datetime, today: date) -> bool:
    if row.accept_deadline is not None:
        deadline = row.accept_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        return now > deadline
    # Sem prazo da Loja para a data: o pedido deixa de poder ser aceito quando a data passa.
    return row.requested_date < today


def sync_partner_orders(db: Session, rows: list[PartnerOrder]) -> None:
    """Preguiçoso: pedido da casa cancelado cancela a parte; prazo vencido expira a parte (o pão segue)."""
    now = _now()
    today = _store_today()
    changed = False
    for row in rows:
        if row.status not in PARTNER_ORDER_OPEN:
            continue
        if house_order_cancelled(db, row.house_order_id):
            row.status = "cancelled"
        elif row.status == "submitted" and _accept_window_closed(row, now, today):
            row.status = "expired"
        else:
            continue
        row.updated_at = now
        changed = True
    if changed:
        db.flush()


def _amount_to_partner(row: PartnerOrder) -> int:
    return row.item_cents + (row.freight_cents or 0) - row.fee_cents


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def partner_order_out(row: PartnerOrder) -> dict:
    return {
        "id": str(row.id),
        "public_reference": row.public_reference,
        "combo_ref": str(row.combo_ref),
        "product_name": row.product_name,
        "house_product_name": row.house_product_name,
        "requested_date": row.requested_date.isoformat(),
        "customer_name": row.customer_name,
        "address_line": row.address_line,
        "item_quantity": row.item_quantity,
        "item_cents": row.item_cents,
        "freight_cents": row.freight_cents,
        "fee_cents": row.fee_cents,
        "status": row.status,
        "accept_deadline": _iso(row.accept_deadline),
        "refuse_reason": row.refuse_reason,
    }


def list_partner_orders(db: Session, partner: Partner) -> list[dict]:
    rows = list(
        db.scalars(
            select(PartnerOrder)
            .where(PartnerOrder.partner_id == partner.id)
            .order_by(PartnerOrder.created_at.desc(), PartnerOrder.id.desc())
        ).all()
    )
    sync_partner_orders(db, rows)
    return [partner_order_out(row) for row in rows]


def _own_partner_order(db: Session, partner: Partner, order_id: UUID) -> PartnerOrder:
    row = db.scalar(
        select(PartnerOrder)
        .where(PartnerOrder.id == order_id, PartnerOrder.partner_id == partner.id)
        .with_for_update()
    )
    if row is None:
        raise MarketplaceError(404, "não encontrado")
    sync_partner_orders(db, [row])
    return row


def _require_open_for_decision(row: PartnerOrder) -> None:
    if row.status == "expired":
        raise MarketplaceError(409, "o prazo para decidir este pedido venceu")
    if row.status == "cancelled":
        raise MarketplaceError(409, "este pedido foi cancelado pela Loja")
    if row.status != "submitted":
        raise MarketplaceError(409, "este pedido não está aguardando a sua decisão")


def accept_partner_order(db: Session, partner: Partner, order_id: UUID) -> dict:
    _active(partner)
    row = _own_partner_order(db, partner, order_id)
    _require_open_for_decision(row)
    row.status = "accepted"
    row.updated_at = _now()
    _flush(db)
    return partner_order_out(row)


def refuse_partner_order(db: Session, partner: Partner, order_id: UUID, reason: object) -> dict:
    _active(partner)
    text = clean_required(str(reason or ""), "o motivo da recusa", REFUSE_REASON_MAX)
    row = _own_partner_order(db, partner, order_id)
    _require_open_for_decision(row)
    row.status = "refused"
    row.refuse_reason = text
    row.updated_at = _now()
    _flush(db)
    return partner_order_out(row)


def deliver_partner_order(db: Session, partner: Partner, order_id: UUID) -> dict:
    _active(partner)
    row = _own_partner_order(db, partner, order_id)
    if row.status == "cancelled":
        raise MarketplaceError(409, "este pedido foi cancelado pela Loja")
    if row.status != "accepted":
        raise MarketplaceError(409, "só um pedido confirmado pode ser marcado como entregue")
    row.status = "delivered"
    row.updated_at = _now()
    _flush(db)
    return partner_order_out(row)


def combo_partner_parts(db: Session, combo_ref: UUID) -> list[dict]:
    """Partes dos parceiros de um pedido de combo, como o cliente as vê. Sem a taxa."""
    rows = list(
        db.scalars(
            select(PartnerOrder)
            .where(PartnerOrder.combo_ref == combo_ref)
            .order_by(PartnerOrder.created_at, PartnerOrder.id)
        ).all()
    )
    sync_partner_orders(db, rows)
    parts = []
    for row in rows:
        partner = db.get(Partner, row.partner_id)
        if partner is None:
            continue
        parts.append(
            {
                "id": str(row.id),
                "public_reference": row.public_reference,
                "brand": _public_brand(partner),
                "product_name": row.product_name,
                "status": row.status,
                "amount_cents": _amount_to_partner(row),
                "refuse_reason": row.refuse_reason,
                "accept_deadline": _iso(row.accept_deadline),
            }
        )
    return parts
