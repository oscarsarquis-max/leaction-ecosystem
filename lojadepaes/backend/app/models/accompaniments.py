from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin


class AccompanimentItem(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "accompaniment_items"
    __table_args__ = (
        UniqueConstraint("hub_offer_id", name="uq_accompaniment_hub_offer"),
        CheckConstraint("char_length(hub_offer_id) BETWEEN 1 AND 80", name="ck_accompaniment_hub_id"),
        CheckConstraint("sort_order >= 0", name="ck_accompaniment_sort"),
        Index("ix_accompaniment_published_sort", "published", "sort_order"),
    )

    hub_offer_id: Mapped[str] = mapped_column(String(80), nullable=False)
    hub_source: Mapped[str] = mapped_column(String(40), nullable=False, default="mercadolivre")
    snapshot_title: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    snapshot_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    snapshot_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    snapshot_price_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    snapshot_price_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="BRL")
    snapshot_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    occasion: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    story_title: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    story_lead: Mapped[str] = mapped_column(Text, nullable=False, default="")
    why_pairs: Mapped[str] = mapped_column(Text, nullable=False, default="")
    serving_tip: Mapped[str] = mapped_column(Text, nullable=False, default="")
    related_product_slugs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    related_recipe_slugs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
