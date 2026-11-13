"""Operações do marketplace. Não conhece pedido, pagamento, agenda nem aviso."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastapi.responses import FileResponse, Response

from app.domain.errors import ProductError
from app.domain.media import open_media, store_image
from app.marketplace.auth import drop_sessions, hash_password, hash_token, start_session, verify_password
from app.marketplace.house_catalog import published_product_name, published_slug_exists
from app.marketplace.models import (
    Partner,
    PartnerLink,
    PartnerMedia,
    PartnerProduct,
    PartnerUser,
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
    media_id_of,
    periods_overlap,
    refuse_bakery_text,
)

PARTNER_TYPES = frozenset({"producer", "distributor", "restaurant"})
LINK_TYPES = frozenset({"exclusive", "partial", "none"})
INVITE_DAYS = 7


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
