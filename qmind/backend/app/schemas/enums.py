"""Domain state-machine enums — OpenAPI + runtime validation (domain-docs-v0)."""

from __future__ import annotations

from enum import Enum


class AssessmentStatus(str, Enum):
    draft = "draft"
    planned = "planned"
    in_progress = "in_progress"
    analysis = "analysis"
    actions = "actions"
    report = "report"
    closed = "closed"
    cancelled = "cancelled"


class AssessmentType(str, Enum):
    diagnosis = "diagnosis"
    internal_audit = "internal_audit"
    external_audit = "external_audit"
    certification_prep = "certification_prep"
    other = "other"


class FindingStatus(str, Enum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    withdrawn = "withdrawn"
    discarded = "discarded"


class FindingType(str, Enum):
    conformity = "conformity"
    nonconformity = "nonconformity"
    opportunity = "opportunity"
    observation = "observation"


class EvidenceStatus(str, Enum):
    upload_pending = "upload_pending"
    quarantined = "quarantined"
    rejected = "rejected"
    approved = "approved"
    superseded = "superseded"
    pending_disposal = "pending_disposal"
    disposed = "disposed"


class EvidenceClassification(str, Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


class InterviewStatus(str, Enum):
    planned = "planned"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class InterviewMode(str, Enum):
    onsite = "onsite"
    remote = "remote"
    hybrid = "hybrid"


class EvidenceLinkTargetType(str, Enum):
    requirement = "requirement"
    question = "question"
    finding = "finding"
    action_item = "action_item"
    interview = "interview"
    answer = "answer"


class MaturityStatus(str, Enum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    superseded = "superseded"
    discarded = "discarded"


class Applicability(str, Enum):
    applicable = "applicable"
    not_applicable = "not_applicable"
    insufficient_info = "insufficient_info"


class ActionPlanStatus(str, Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class ActionItemStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    implemented = "implemented"
    validated = "validated"
    done = "done"
    cancelled = "cancelled"
    ineffective = "ineffective"
    ineffective_closed = "ineffective_closed"


class ActionKind(str, Enum):
    correction = "correction"
    corrective_action = "corrective_action"
    improvement = "improvement"


class ReportStatus(str, Enum):
    draft = "draft"
    in_review = "in_review"
    published = "published"
    archived = "archived"
    superseded = "superseded"
    discarded = "discarded"


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class OrganizationStatus(str, Enum):
    active = "active"
    suspended = "suspended"
    closed = "closed"


class MembershipStatus(str, Enum):
    invited = "invited"
    active = "active"
    revoked = "revoked"
    expired = "expired"
