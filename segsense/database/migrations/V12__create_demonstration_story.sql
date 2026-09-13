-- Editorial DemonstrationStory: snapshots, sources and publication ledger.
-- V1–V11 unchanged. No CASCADE. No data repair.
-- Conceptual rollback: drop V12 triggers/functions/tables.

DO $guard$
DECLARE
  personal_fields bigint;
BEGIN
  SELECT COUNT(*) INTO personal_fields
    FROM segsense.contextual_opportunity_revision_field
   WHERE classification IS DISTINCT FROM 'NON_PERSONAL';

  IF personal_fields > 0 THEN
    RAISE EXCEPTION
      'V12 aborted without mutation: personal_fields=%',
      personal_fields;
  END IF;
END $guard$;

CREATE TABLE segsense.demonstration_source (
    id UUID PRIMARY KEY,
    source_key VARCHAR(50) NOT NULL,
    url TEXT NOT NULL,
    consulted_on DATE NOT NULL,
    access_kind VARCHAR(32) NOT NULL,
    verification_status VARCHAR(32) NOT NULL,
    summary VARCHAR(500) NOT NULL,
    CONSTRAINT demonstration_source_key_unique UNIQUE (source_key),
    CONSTRAINT demonstration_source_url_unique UNIQUE (url),
    CONSTRAINT demonstration_source_access_chk CHECK (
        access_kind IN ('PUBLIC', 'RESTRICTED', 'UNVERIFIED')
    ),
    CONSTRAINT demonstration_source_status_chk CHECK (
        verification_status IN ('VERIFIED', 'VERIFIED_LIMITED', 'UNVERIFIED')
    )
);

CREATE TABLE segsense.demonstration_story (
    id UUID PRIMARY KEY,
    story_key VARCHAR(50) NOT NULL,
    workflow_status VARCHAR(16) NOT NULL,
    publication_status VARCHAR(16) NOT NULL,
    current_revision INTEGER NOT NULL,
    published_revision INTEGER,
    submitted_by VARCHAR(128),
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by VARCHAR(128) NOT NULL,
    updated_by VARCHAR(128) NOT NULL,
    CONSTRAINT demonstration_story_key_unique UNIQUE (story_key),
    CONSTRAINT demonstration_story_workflow_chk CHECK (
        workflow_status IN ('DRAFT', 'UNDER_REVIEW', 'APPROVED')
    ),
    CONSTRAINT demonstration_story_publication_chk CHECK (
        publication_status IN ('UNPUBLISHED', 'LIVE', 'PAUSED', 'RETIRED')
    ),
    CONSTRAINT demonstration_story_current_revision_chk CHECK (current_revision >= 1),
    CONSTRAINT demonstration_story_published_revision_chk CHECK (
        published_revision IS NULL OR published_revision >= 1
    ),
    CONSTRAINT demonstration_story_publication_presence_chk CHECK (
        (publication_status = 'UNPUBLISHED' AND published_revision IS NULL)
        OR (publication_status IN ('LIVE', 'PAUSED', 'RETIRED') AND published_revision IS NOT NULL)
    )
);

CREATE TABLE segsense.demonstration_revision (
    id UUID PRIMARY KEY,
    story_id UUID NOT NULL,
    revision_number INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    summary TEXT NOT NULL,
    intended_audience VARCHAR(200) NOT NULL,
    scope_note TEXT NOT NULL,
    frozen BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    created_by VARCHAR(128) NOT NULL,
    CONSTRAINT demonstration_revision_story_fk
        FOREIGN KEY (story_id)
        REFERENCES segsense.demonstration_story (id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT demonstration_revision_number_chk CHECK (revision_number >= 1),
    CONSTRAINT demonstration_revision_identity_unique UNIQUE (story_id, revision_number)
);

ALTER TABLE segsense.demonstration_story
    ADD CONSTRAINT demonstration_story_current_revision_fk
        FOREIGN KEY (id, current_revision)
        REFERENCES segsense.demonstration_revision (story_id, revision_number)
        DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE segsense.demonstration_story
    ADD CONSTRAINT demonstration_story_published_revision_fk
        FOREIGN KEY (id, published_revision)
        REFERENCES segsense.demonstration_revision (story_id, revision_number)
        DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE segsense.demonstration_block (
    id UUID PRIMARY KEY,
    story_id UUID NOT NULL,
    revision_number INTEGER NOT NULL,
    position INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    CONSTRAINT demonstration_block_revision_fk
        FOREIGN KEY (story_id, revision_number)
        REFERENCES segsense.demonstration_revision (story_id, revision_number)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT demonstration_block_position_chk CHECK (position >= 1),
    CONSTRAINT demonstration_block_position_unique UNIQUE (story_id, revision_number, position)
);

CREATE TABLE segsense.demonstration_claim (
    id UUID PRIMARY KEY,
    story_id UUID NOT NULL,
    revision_number INTEGER NOT NULL,
    position INTEGER NOT NULL,
    claim_text TEXT NOT NULL,
    source_id UUID NOT NULL,
    CONSTRAINT demonstration_claim_revision_fk
        FOREIGN KEY (story_id, revision_number)
        REFERENCES segsense.demonstration_revision (story_id, revision_number)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT demonstration_claim_source_fk
        FOREIGN KEY (source_id)
        REFERENCES segsense.demonstration_source (id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT demonstration_claim_position_chk CHECK (position >= 1),
    CONSTRAINT demonstration_claim_position_unique UNIQUE (story_id, revision_number, position)
);

CREATE TABLE segsense.demonstration_decision (
    id UUID PRIMARY KEY,
    story_id UUID NOT NULL,
    revision_number INTEGER NOT NULL,
    action VARCHAR(16) NOT NULL,
    actor VARCHAR(128) NOT NULL,
    justification TEXT NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT demonstration_decision_story_fk
        FOREIGN KEY (story_id)
        REFERENCES segsense.demonstration_story (id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT demonstration_decision_revision_fk
        FOREIGN KEY (story_id, revision_number)
        REFERENCES segsense.demonstration_revision (story_id, revision_number)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT demonstration_decision_action_chk CHECK (
        action IN ('SUBMITTED', 'RETURNED', 'APPROVED', 'PUBLISHED', 'PAUSED', 'RESUMED', 'RETIRED')
    )
);

CREATE FUNCTION segsense.reject_demonstration_revision_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'demonstration revision is append-only';
  END IF;
  IF OLD.frozen AND NEW.frozen IS DISTINCT FROM TRUE THEN
    RAISE EXCEPTION 'demonstration revision cannot be unfrozen';
  END IF;
  IF OLD.frozen AND (
       NEW.title IS DISTINCT FROM OLD.title
    OR NEW.summary IS DISTINCT FROM OLD.summary
    OR NEW.intended_audience IS DISTINCT FROM OLD.intended_audience
    OR NEW.scope_note IS DISTINCT FROM OLD.scope_note
    OR NEW.revision_number IS DISTINCT FROM OLD.revision_number
    OR NEW.story_id IS DISTINCT FROM OLD.story_id
  ) THEN
    RAISE EXCEPTION 'demonstration revision is immutable';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER demonstration_revision_protect
    BEFORE UPDATE OR DELETE ON segsense.demonstration_revision
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_demonstration_revision_mutation();

CREATE FUNCTION segsense.reject_demonstration_child_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  parent_frozen boolean;
BEGIN
  IF TG_OP = 'INSERT' THEN
    SELECT frozen INTO parent_frozen
      FROM segsense.demonstration_revision
     WHERE story_id = NEW.story_id AND revision_number = NEW.revision_number;
    IF parent_frozen IS NULL THEN
      RAISE EXCEPTION 'demonstration child requires an existing revision';
    END IF;
    IF parent_frozen THEN
      RAISE EXCEPTION 'cannot add content to a frozen demonstration revision';
    END IF;
    RETURN NEW;
  END IF;
  SELECT frozen INTO parent_frozen
    FROM segsense.demonstration_revision
   WHERE story_id = OLD.story_id AND revision_number = OLD.revision_number;
  IF parent_frozen THEN
    RAISE EXCEPTION 'demonstration revision content is immutable';
  END IF;
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER demonstration_block_protect
    BEFORE INSERT OR UPDATE OR DELETE ON segsense.demonstration_block
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_demonstration_child_mutation();

CREATE TRIGGER demonstration_claim_protect
    BEFORE INSERT OR UPDATE OR DELETE ON segsense.demonstration_claim
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_demonstration_child_mutation();

CREATE FUNCTION segsense.reject_unverified_demonstration_claim()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  source_status varchar(32);
BEGIN
  SELECT verification_status INTO source_status
    FROM segsense.demonstration_source
   WHERE id = NEW.source_id;
  IF source_status IS NULL THEN
    RAISE EXCEPTION 'demonstration claim requires a catalogued source';
  END IF;
  IF source_status NOT IN ('VERIFIED', 'VERIFIED_LIMITED') THEN
    RAISE EXCEPTION 'demonstration claim requires a verified source';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER demonstration_claim_verified_source
    BEFORE INSERT ON segsense.demonstration_claim
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_unverified_demonstration_claim();

CREATE FUNCTION segsense.reject_demonstration_decision_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'demonstration decision is append-only';
END;
$$;

CREATE TRIGGER demonstration_decision_no_update
    BEFORE UPDATE OR DELETE ON segsense.demonstration_decision
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_demonstration_decision_mutation();

CREATE FUNCTION segsense.reject_unpublished_live_story()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.publication_status = 'LIVE' THEN
    IF NEW.published_revision IS NULL THEN
      RAISE EXCEPTION 'cannot publish demonstration without a snapshot';
    END IF;
    IF NOT EXISTS (
      SELECT 1
        FROM segsense.demonstration_decision d
       WHERE d.story_id = NEW.id
         AND d.revision_number = NEW.published_revision
         AND d.action = 'APPROVED'
    ) THEN
      RAISE EXCEPTION 'cannot publish demonstration without an approval decision';
    END IF;
  END IF;
  IF OLD.publication_status = 'RETIRED' AND NEW.publication_status IS DISTINCT FROM 'RETIRED' THEN
    RAISE EXCEPTION 'retired demonstration cannot change publication status';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER demonstration_story_publication_guard
    BEFORE UPDATE ON segsense.demonstration_story
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_unpublished_live_story();

INSERT INTO segsense.demonstration_source
    (id, source_key, url, consulted_on, access_kind, verification_status, summary)
VALUES
    (
      '11111111-1111-4111-8111-000000000001',
      'icatu-hub-home',
      'https://portal-api.icatuseguros.com.br/',
      DATE '2026-09-12',
      'PUBLIC',
      'VERIFIED',
      'Pagina publica do Hub de APIs. Apresenta integracao autenticada; nao e licenca nem parceria.'
    ),
    (
      '11111111-1111-4111-8111-000000000002',
      'icatu-hub-apis',
      'https://portal-api.icatuseguros.com.br/apis',
      DATE '2026-09-12',
      'PUBLIC',
      'VERIFIED_LIMITED',
      'Catalogo publico abre como casco HTML. Especificacoes de operacao nao aparecem sem autenticacao.'
    ),
    (
      '11111111-1111-4111-8111-000000000003',
      'icatu-hub-terms',
      'https://portal-api.icatuseguros.com.br/terms-of-use',
      DATE '2026-09-12',
      'PUBLIC',
      'VERIFIED',
      'Termos publicos vinculam uso de API a cadastro aprovado e relacao contratual. Sem licenca generica.'
    );
