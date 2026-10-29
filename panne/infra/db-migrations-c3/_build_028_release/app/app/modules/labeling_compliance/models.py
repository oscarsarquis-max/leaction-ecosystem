"""Persistência de rotulagem. Avaliações e decisões append-only."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid_pk():
    return mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))


def _created_at():
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LabelingDossier(Base):
    __tablename__ = "labeling_dossier"
    __table_args__ = (
        Index("uq_labeling_dossier_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    establishment_id: Mapped[UUID | None] = mapped_column(Uuid)
    technical_product_id: Mapped[UUID | None] = mapped_column(Uuid)
    formulation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    formulation_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    nutrition_calculation_id: Mapped[UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class LabelingApplicabilityProfile(Base):
    __tablename__ = "labeling_applicability_profile"
    __table_args__ = (
        Index("uq_labeling_profile_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["labeling_dossier_id", "organization_id"],
            ["labeling_dossier.id", "labeling_dossier.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    labeling_dossier_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(Text)
    evaluation_date: Mapped[date | None] = mapped_column(Date)
    packed_food: Mapped[bool | None] = mapped_column(Boolean)
    packed_away_from_consumer: Mapped[bool | None] = mapped_column(Boolean)
    packed_at_point_of_sale: Mapped[bool | None] = mapped_column(Boolean)
    packed_on_request: Mapped[bool | None] = mapped_column(Boolean)
    same_establishment: Mapped[bool | None] = mapped_column(Boolean)
    sales_channel: Mapped[str | None] = mapped_column(Text)
    food_service: Mapped[bool | None] = mapped_column(Boolean)
    physical_state: Mapped[str | None] = mapped_column(Text)
    ready_to_eat: Mapped[bool | None] = mapped_column(Boolean)
    regulatory_category_code: Mapped[str | None] = mapped_column(Text)
    category_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    package_area_cm2: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    net_content_g: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    servings_per_package: Mapped[int | None] = mapped_column(Integer)
    purpose: Mapped[str | None] = mapped_column(Text)
    destination_market: Mapped[str | None] = mapped_column(Text)
    completeness: Mapped[str] = mapped_column(Text, nullable=False, server_default="incomplete")
    created_at: Mapped[datetime] = _created_at()


class LabelingDossierVersion(Base):
    __tablename__ = "labeling_dossier_version"
    __table_args__ = (
        Index(
            "uq_labeling_dossier_version_number",
            "labeling_dossier_id",
            "version_number",
            unique=True,
        ),
        Index("uq_labeling_dossier_version_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["labeling_dossier_id", "organization_id"],
            ["labeling_dossier.id", "labeling_dossier.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    labeling_dossier_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="evaluated")
    algorithm_name: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class LabelingAssessment(Base):
    __tablename__ = "labeling_assessment"
    __table_args__ = (
        Index("uq_labeling_assessment_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    labeling_dossier_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="evaluated")
    proposal_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class LabelingFinding(Base):
    __tablename__ = "labeling_finding"
    __table_args__ = (
        Index("uq_labeling_finding_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["labeling_assessment_id", "organization_id"],
            ["labeling_assessment.id", "labeling_assessment.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    labeling_assessment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    rule_code: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    expected_value: Mapped[str | None] = mapped_column(Text)
    found_value: Mapped[str | None] = mapped_column(Text)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    source_version: Mapped[str] = mapped_column(Text, nullable=False)
    accessed_at: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    action_needed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = _created_at()


class LabelingEvidence(Base):
    __tablename__ = "labeling_evidence"
    __table_args__ = (
        Index("uq_labeling_evidence_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["labeling_finding_id", "organization_id"],
            ["labeling_finding.id", "labeling_finding.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    labeling_finding_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    evidence_key: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = _created_at()


class LabelingReview(Base):
    __tablename__ = "labeling_review"
    __table_args__ = (
        Index("uq_labeling_review_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    labeling_dossier_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()


class LabelingNutritionCandidate(Base):
    __tablename__ = "labeling_nutrition_candidate"
    __table_args__ = (
        Index("uq_labeling_nutrition_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    labeling_dossier_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    portion_g: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    household_measure: Mapped[str | None] = mapped_column(Text)
    servings_per_package: Mapped[int | None] = mapped_column(Integer)
    table_format: Mapped[str] = mapped_column(Text, nullable=False, server_default="vertical")
    footnotes: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[datetime] = _created_at()


class LabelingNutritionLine(Base):
    __tablename__ = "labeling_nutrition_line"
    __table_args__ = (
        Index(
            "uq_labeling_nutrition_line_code",
            "labeling_nutrition_candidate_id",
            "nutrient_code",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["labeling_nutrition_candidate_id", "organization_id"],
            ["labeling_nutrition_candidate.id", "labeling_nutrition_candidate.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    labeling_nutrition_candidate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    nutrient_code: Mapped[str] = mapped_column(Text, nullable=False)
    technical_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    regulatory_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    declared_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    declared_per_serving: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    daily_value_percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    completeness: Mapped[str] = mapped_column(Text, nullable=False)
    presented: Mapped[str | None] = mapped_column(Text)


class LabelingFrontOfPack(Base):
    __tablename__ = "labeling_front_of_pack"
    __table_args__ = (
        Index("uq_labeling_fop_version", "labeling_dossier_version_id", unique=True),
        ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    labeling_dossier_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    added_sugars_result: Mapped[str] = mapped_column(Text, nullable=False)
    saturated_fat_result: Mapped[str] = mapped_column(Text, nullable=False)
    sodium_result: Mapped[str] = mapped_column(Text, nullable=False)
    magnifier_required: Mapped[bool | None] = mapped_column(Boolean)
    nutrients_high: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    compared: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )


class LabelingIngredientCandidate(Base):
    __tablename__ = "labeling_ingredient_candidate"
    __table_args__ = (
        Index("uq_labeling_ingredient_seq", "labeling_dossier_version_id", "sequence", unique=True),
        ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    labeling_dossier_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    ingredient_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    net_quantity_g: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    compound: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    components: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    gap: Mapped[str | None] = mapped_column(Text)


class LabelingWarningCandidate(Base):
    __tablename__ = "labeling_warning_candidate"
    __table_args__ = (
        Index("uq_labeling_warning_code", "labeling_dossier_version_id", "code", unique=True),
        ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    labeling_dossier_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )


class LabelingMandatoryItem(Base):
    __tablename__ = "labeling_mandatory_item"
    __table_args__ = (
        Index("uq_labeling_mandatory_code", "labeling_dossier_version_id", "code", unique=True),
        ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    labeling_dossier_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    claim: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class LabelingLabelCandidate(Base):
    __tablename__ = "labeling_label_candidate"
    __table_args__ = (
        Index("uq_labeling_label_version", "labeling_dossier_version_id", unique=True),
        ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    labeling_dossier_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    watermark: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class LabelingInvalidation(Base):
    __tablename__ = "labeling_invalidation"
    __table_args__ = (
        Index("uq_labeling_invalidation_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    labeling_dossier_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class LabelingCommand(Base):
    __tablename__ = "labeling_command"
    __table_args__ = (
        Index(
            "uq_labeling_command_idempotency",
            "organization_id",
            "idempotency_key",
            unique=True,
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    payload_digest: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()
