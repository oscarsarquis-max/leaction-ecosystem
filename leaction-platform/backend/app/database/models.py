"""Modelos SQLAlchemy do plugin Marketplace."""

from __future__ import annotations

from datetime import datetime, timezone

from app.database import DB_AVAILABLE, db

if not DB_AVAILABLE or db is None:
    MarketplaceCuration = None  # type: ignore[misc, assignment]
else:
    from sqlalchemy.dialects.postgresql import JSONB
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


def _as_string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
