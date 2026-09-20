from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin


class Article(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "articles"
    __table_args__ = (
        CheckConstraint(
            "editorial_status IN ('draft','published','archived')",
            name="ck_articles_editorial_status",
        ),
        CheckConstraint(
            "estimated_reading_minutes IS NULL OR estimated_reading_minutes > 0",
            name="ck_articles_reading_minutes",
        ),
    )

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    summary: Mapped[str] = mapped_column(String(400), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    cover_image_ref: Mapped[str | None] = mapped_column(String(500))
    editorial_status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_reading_minutes: Mapped[int | None] = mapped_column(Integer)


class InspirationPost(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "inspiration_posts"
    __table_args__ = (
        CheckConstraint(
            "editorial_status IN ('draft','published','archived')",
            name="ck_inspiration_editorial_status",
        ),
        CheckConstraint(
            "source_kind IN ('editorial','community')",
            name="ck_inspiration_source_kind",
        ),
    )

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    image_ref: Mapped[str | None] = mapped_column(String(500))
    credit: Mapped[str | None] = mapped_column(String(160))
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="editorial")
    editorial_status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
