-- Opportunity governance: lifecycle statuses, append-only submission/decision/events.
-- V1–V4 unchanged. No CASCADE. No business triggers.
-- Conceptual rollback: drop events, decisions, submissions, drop new columns, restore DRAFT-only status check.

ALTER TABLE segsense.contextual_opportunity
    DROP CONSTRAINT opportunity_status_chk;

ALTER TABLE segsense.contextual_opportunity
    ADD CONSTRAINT opportunity_status_chk CHECK (
        status IN (
            'DRAFT',
            'UNDER_REVIEW',
            'APPROVED',
            'PUBLISHED',
            'PAUSED',
            'REVOKED',
            'EXPIRED'
        )
    );

ALTER TABLE segsense.contextual_opportunity
    ADD COLUMN submitted_revision INTEGER,
    ADD COLUMN approved_revision INTEGER,
    ADD COLUMN open_submission_id UUID,
    ADD COLUMN submitted_by VARCHAR(128),
    ADD COLUMN approved_by VARCHAR(128);

ALTER TABLE segsense.contextual_opportunity
    ADD CONSTRAINT opportunity_submitted_revision_chk
        CHECK (submitted_revision IS NULL OR submitted_revision >= 1);

ALTER TABLE segsense.contextual_opportunity
    ADD CONSTRAINT opportunity_approved_revision_chk
        CHECK (approved_revision IS NULL OR approved_revision >= 1);

ALTER TABLE segsense.contextual_opportunity
    ADD CONSTRAINT opportunity_submitted_revision_fk
        FOREIGN KEY (id, submitted_revision)
        REFERENCES segsense.contextual_opportunity_revision (opportunity_id, revision_number)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION;

ALTER TABLE segsense.contextual_opportunity
    ADD CONSTRAINT opportunity_approved_revision_fk
        FOREIGN KEY (id, approved_revision)
        REFERENCES segsense.contextual_opportunity_revision (opportunity_id, revision_number)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION;

CREATE TABLE segsense.opportunity_submission (
    id UUID PRIMARY KEY,
    opportunity_id UUID NOT NULL,
    revision_number INTEGER NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    submitted_by VARCHAR(128) NOT NULL,
    correlation_id UUID NOT NULL,
    status VARCHAR(16) NOT NULL,
    CONSTRAINT opportunity_submission_opportunity_fk
        FOREIGN KEY (opportunity_id)
        REFERENCES segsense.contextual_opportunity (id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT opportunity_submission_revision_fk
        FOREIGN KEY (opportunity_id, revision_number)
        REFERENCES segsense.contextual_opportunity_revision (opportunity_id, revision_number)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT opportunity_submission_status_chk CHECK (status IN ('OPEN', 'DECIDED')),
    CONSTRAINT opportunity_submission_revision_chk CHECK (revision_number >= 1)
);

CREATE UNIQUE INDEX opportunity_open_submission_unique
    ON segsense.opportunity_submission (opportunity_id)
    WHERE status = 'OPEN';

CREATE INDEX opportunity_submission_history_idx
    ON segsense.opportunity_submission (opportunity_id, submitted_at, id);

ALTER TABLE segsense.contextual_opportunity
    ADD CONSTRAINT opportunity_open_submission_fk
        FOREIGN KEY (open_submission_id)
        REFERENCES segsense.opportunity_submission (id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION;

CREATE TABLE segsense.opportunity_decision (
    id UUID PRIMARY KEY,
    submission_id UUID NOT NULL,
    opportunity_id UUID NOT NULL,
    revision_number INTEGER NOT NULL,
    outcome VARCHAR(16) NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL,
    decided_by VARCHAR(128) NOT NULL,
    justification VARCHAR(500),
    correlation_id UUID NOT NULL,
    CONSTRAINT opportunity_decision_submission_unique UNIQUE (submission_id),
    CONSTRAINT opportunity_decision_submission_fk
        FOREIGN KEY (submission_id)
        REFERENCES segsense.opportunity_submission (id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT opportunity_decision_revision_fk
        FOREIGN KEY (opportunity_id, revision_number)
        REFERENCES segsense.contextual_opportunity_revision (opportunity_id, revision_number)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT opportunity_decision_outcome_chk
        CHECK (outcome IN ('APPROVED', 'RETURNED', 'REJECTED')),
    CONSTRAINT opportunity_decision_justification_chk CHECK (
        (outcome = 'APPROVED' AND justification IS NULL)
        OR (
            outcome IN ('RETURNED', 'REJECTED')
            AND justification IS NOT NULL
            AND char_length(justification) BETWEEN 10 AND 500
        )
    )
);

CREATE TABLE segsense.opportunity_lifecycle_event (
    id UUID PRIMARY KEY,
    opportunity_id UUID NOT NULL,
    revision_number INTEGER NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    previous_status VARCHAR(16) NOT NULL,
    new_status VARCHAR(16) NOT NULL,
    actor_subject_id VARCHAR(128) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    justification VARCHAR(500),
    correlation_id UUID NOT NULL,
    CONSTRAINT opportunity_event_opportunity_fk
        FOREIGN KEY (opportunity_id)
        REFERENCES segsense.contextual_opportunity (id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT opportunity_event_revision_fk
        FOREIGN KEY (opportunity_id, revision_number)
        REFERENCES segsense.contextual_opportunity_revision (opportunity_id, revision_number)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT opportunity_event_type_chk CHECK (
        event_type IN (
            'SUBMITTED',
            'RETURNED',
            'APPROVED',
            'REJECTED',
            'ACTIVATED',
            'PAUSED',
            'RESUMED',
            'EXPIRED',
            'REVOKED'
        )
    )
);

CREATE INDEX opportunity_event_cursor_idx
    ON segsense.opportunity_lifecycle_event (opportunity_id, occurred_at, id);
CREATE INDEX opportunity_event_revision_idx
    ON segsense.opportunity_lifecycle_event (opportunity_id, revision_number);
