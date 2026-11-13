"""Tabelas do schema marketplace. Nenhuma chave aponta para fora deste schema."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.models.mixins import TimestampMixin, UuidPkMixin


class MarketplaceBase(DeclarativeBase):
    pass


class Partner(UuidPkMixin, TimestampMixin, MarketplaceBase):
    __tablename__ = "partners"
    __table_args__ = (
        CheckConstraint(
            "partner_type IN ('producer','distributor','restaurant')",
            name="ck_mp_partners_type",
        ),
        CheckConstraint(
            "status IN ('invited','active','paused')",
            name="ck_mp_partners_status",
        ),
        CheckConstraint(
            "fee_cents BETWEEN 0 AND 100000",
            name="ck_mp_partners_fee",
        ),
        UniqueConstraint("brand_slug", name="uq_mp_partners_slug"),
        {"schema": "marketplace"},
    )

    partner_type: Mapped[str] = mapped_column(String(20), nullable=False)
    brand_name: Mapped[str] = mapped_column(String(120), nullable=False)
    brand_slug: Mapped[str] = mapped_column(String(80), nullable=False)
    logo_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    photo_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    story: Mapped[str] = mapped_column(Text, nullable=False, default="")
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    highlight_hex: Mapped[str] = mapped_column(String(7), nullable=False)
    document: Mapped[str] = mapped_column(String(40), nullable=False)
    contact: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="invited")
    pay_recipient_id: Mapped[str | None] = mapped_column(String(80))
    fee_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=250, server_default="250")


class PartnerUser(UuidPkMixin, TimestampMixin, MarketplaceBase):
    __tablename__ = "partner_users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_mp_partner_users_email"),
        {"schema": "marketplace"},
    )

    email: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    partner_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("marketplace.partners.id", ondelete="CASCADE"),
        nullable=False,
    )
    invite_token_hash: Mapped[str | None] = mapped_column(String(64))
    invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PartnerSession(UuidPkMixin, TimestampMixin, MarketplaceBase):
    __tablename__ = "partner_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_mp_partner_sessions_token"),
        {"schema": "marketplace"},
    )

    partner_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("marketplace.partner_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    csrf_token: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PartnerLink(UuidPkMixin, TimestampMixin, MarketplaceBase):
    __tablename__ = "partner_links"
    __table_args__ = (
        CheckConstraint(
            "link_type IN ('exclusive','partial','none')",
            name="ck_mp_partner_links_type",
        ),
        CheckConstraint(
            "ends_on IS NULL OR ends_on >= starts_on",
            name="ck_mp_partner_links_range",
        ),
        {"schema": "marketplace"},
    )

    partner_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("marketplace.partners.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    link_type: Mapped[str] = mapped_column(String(20), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date)


class PartnerProduct(UuidPkMixin, TimestampMixin, MarketplaceBase):
    __tablename__ = "partner_products"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','pending','returned','approved','rejected','paused')",
            name="ck_mp_products_status",
        ),
        CheckConstraint("price_cents >= 0", name="ck_mp_products_price"),
        CheckConstraint(
            "delivery_days IS NULL OR delivery_days >= 0",
            name="ck_mp_products_days",
        ),
        CheckConstraint(
            "freight_cents IS NULL OR freight_cents >= 0",
            name="ck_mp_products_freight",
        ),
        {"schema": "marketplace"},
    )

    partner_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("marketplace.partners.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    photos: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    delivery_cities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    delivery_districts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    delivery_cep_prefixes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    delivery_days: Mapped[int | None] = mapped_column(Integer)
    freight_cents: Mapped[int | None] = mapped_column(Integer)
    perishable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")


class ProductPairing(UuidPkMixin, TimestampMixin, MarketplaceBase):
    __tablename__ = "product_pairings"
    __table_args__ = (
        CheckConstraint("char_length(reason) >= 1", name="ck_mp_pairings_reason"),
        {"schema": "marketplace"},
    )

    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("marketplace.partner_products.id", ondelete="CASCADE"),
        nullable=False,
    )
    house_product_slug: Mapped[str] = mapped_column(String(80), nullable=False)
    reason: Mapped[str] = mapped_column(String(400), nullable=False)


class ProductReview(UuidPkMixin, TimestampMixin, MarketplaceBase):
    __tablename__ = "product_reviews"
    __table_args__ = (
        CheckConstraint("quality BETWEEN 1 AND 5", name="ck_mp_reviews_quality"),
        CheckConstraint("visual BETWEEN 1 AND 5", name="ck_mp_reviews_visual"),
        CheckConstraint(
            "complementarity BETWEEN 1 AND 5",
            name="ck_mp_reviews_complementarity",
        ),
        CheckConstraint(
            "decision IN ('approve','return','reject')",
            name="ck_mp_reviews_decision",
        ),
        {"schema": "marketplace"},
    )

    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("marketplace.partner_products.id", ondelete="CASCADE"),
        nullable=False,
    )
    quality: Mapped[int] = mapped_column(Integer, nullable=False)
    visual: Mapped[int] = mapped_column(Integer, nullable=False)
    complementarity: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reviewer_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PartnerMedia(UuidPkMixin, MarketplaceBase):
    __tablename__ = "partner_media"
    __table_args__ = {"schema": "marketplace"}

    partner_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("marketplace.partners.id", ondelete="CASCADE"),
        nullable=False,
    )
    stored_name: Mapped[str] = mapped_column(String(80), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(32), nullable=False)
    content_type: Mapped[str] = mapped_column(String(40), nullable=False)
    size_bytes: Mapped[int] = mapped_column("bytes", Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
