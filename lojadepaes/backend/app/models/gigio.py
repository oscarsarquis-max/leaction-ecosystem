from sqlalchemy import Boolean, CheckConstraint, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin


class GigioEditorialNote(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "gigio_editorial_notes"
    __table_args__ = (
        UniqueConstraint("topic_key", name="uq_gigio_editorial_topic"),
        CheckConstraint(
            "editorial_status IN ('draft','published')",
            name="ck_gigio_editorial_status",
        ),
        CheckConstraint("char_length(topic_key) BETWEEN 1 AND 80", name="ck_gigio_editorial_topic"),
        CheckConstraint("char_length(title) BETWEEN 1 AND 160", name="ck_gigio_editorial_title"),
    )

    topic_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    editorial_status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class GigioPairingReference(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "gigio_pairing_references"
    __table_args__ = (
        UniqueConstraint("profile_key", name="uq_gigio_pairing_profile"),
        CheckConstraint(
            "category IN ('vinhos','queijos','azeites','frios')",
            name="ck_gigio_pairing_category",
        ),
        CheckConstraint(
            "scope IN ('general','style','product')",
            name="ck_gigio_pairing_scope",
        ),
        CheckConstraint(
            "editorial_status IN ('draft','reviewed','published','archived')",
            name="ck_gigio_pairing_status",
        ),
        CheckConstraint(
            "source_kind IN ('commercial','independent','producer',"
            "'commercial_editorial','official_register','research_institution')",
            name="ck_gigio_pairing_source_kind",
        ),
        CheckConstraint(
            "evidence_type IN ('pairing_recommendation','official_register',"
            "'research_project','method_help','style_unverified','guide_evaluation')",
            name="ck_gigio_pairing_evidence",
        ),
        CheckConstraint(
            "retrieval_role IN ('pairing','informational','excluded','evaluation')",
            name="ck_gigio_pairing_retrieval",
        ),
        CheckConstraint(
            "verification_status IN ('verified','pending','inaccessible')",
            name="ck_gigio_pairing_verification",
        ),
        CheckConstraint("char_length(profile_key) BETWEEN 1 AND 80", name="ck_gigio_pairing_profile"),
        CheckConstraint("char_length(title) BETWEEN 1 AND 160", name="ck_gigio_pairing_title"),
    )

    profile_key: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    synthesis: Mapped[str] = mapped_column(Text, nullable=False)
    editorial_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    characteristics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    culinary_contexts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    match_hints: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    identity: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_title: Mapped[str] = mapped_column(String(240), nullable=False)
    source_author: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    source_date: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    consulted_at: Mapped[str] = mapped_column(String(32), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    commercial_relation: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown")
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False, default="style_unverified")
    retrieval_role: Mapped[str] = mapped_column(String(16), nullable=False, default="excluded")
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    support_locator: Mapped[str] = mapped_column(Text, nullable=False, default="")
    claim_layers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    editorial_status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    reviewed_by: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    reviewed_at: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    loja_choice: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
