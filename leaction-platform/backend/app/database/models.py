"""Modelos SQLAlchemy do plugin Marketplace."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.database import DB_AVAILABLE, db

if not DB_AVAILABLE or db is None:
    MarketplaceCuration = None  # type: ignore[misc, assignment]
    MarketplaceProduct = None  # type: ignore[misc, assignment]
else:
    from sqlalchemy.dialects.postgresql import ARRAY, JSONB
    from sqlalchemy.orm import Mapped, mapped_column

    class MarketplaceCuration(db.Model):
        """Regras de curadoria B2B por categoria (ou global)."""

        __tablename__ = "marketplace_curation"

        id: Mapped[str] = mapped_column(db.String(64), primary_key=True)
        search_terms: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
        positive_keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
        negative_keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
        updated_at: Mapped[datetime] = mapped_column(
            db.DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=False,
        )

        def to_dict(self) -> dict:
            return {
                "id": self.id,
                "search_terms": _as_string_list(self.search_terms),
                "positive_keywords": _as_string_list(self.positive_keywords),
                "negative_keywords": _as_string_list(self.negative_keywords),
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }

    class MarketplaceProduct(db.Model):
        """Catálogo persistido da vitrine — match SQL por overlap de tags com sprints."""

        __tablename__ = "marketplace_products"

        id: Mapped[str] = mapped_column(db.String(128), primary_key=True)
        title: Mapped[str] = mapped_column(db.Text, nullable=False)
        price: Mapped[Decimal | None] = mapped_column(db.Numeric(12, 2), nullable=True)
        currency: Mapped[str] = mapped_column(db.String(8), nullable=False, default="BRL")
        price_label: Mapped[str | None] = mapped_column(db.Text, nullable=True)
        image: Mapped[str | None] = mapped_column(db.Text, nullable=True)
        link: Mapped[str] = mapped_column(db.Text, nullable=False)
        vendor: Mapped[str] = mapped_column(db.String(64), nullable=False, default="catalog")
        category: Mapped[str | None] = mapped_column(db.String(64), nullable=True)
        tags: Mapped[list] = mapped_column(ARRAY(db.Text), nullable=False, default=list)
        active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)
        created_at: Mapped[datetime] = mapped_column(
            db.DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False,
        )
        updated_at: Mapped[datetime] = mapped_column(
            db.DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=False,
        )

        def to_offer_dict(self) -> dict:
            price_val = float(self.price) if self.price is not None else None
            if self.price_label:
                label = self.price_label
            elif price_val is not None:
                label = (
                    f"R$ {price_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
            else:
                label = "Consulte"
            return {
                "id": self.id,
                "title": self.title,
                "price": price_val,
                "currency": self.currency or "BRL",
                "price_label": label,
                "image": self.image,
                "link": self.link,
                "vendor": self.vendor or "catalog",
                "category": self.category,
                "tags": _as_string_list(self.tags),
                "fallback": False,
                "match_reason": "tag_overlap",
            }


def _as_string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
