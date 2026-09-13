-- Bind published_context_link to the currently approved revision and
-- bind publisher bindings to the immutable field definition of that revision.
-- V1–V7 unchanged. No CASCADE. No data repair. No business triggers.
-- Conceptual rollback: drop binding FKs and new binding columns, drop link
-- approved-revision/identity FKs and opportunity_revision_id, drop the new
-- candidate keys on opportunity, revision and field.

DO $guard$
DECLARE
  missing_opportunity bigint;
  not_approved bigint;
  missing_revision bigint;
  scope_mismatch bigint;
  unknown_binding bigint;
  user_binding bigint;
BEGIN
  SELECT COUNT(*) INTO missing_opportunity
  FROM segsense.published_context_link l
  WHERE NOT EXISTS (
    SELECT 1 FROM segsense.contextual_opportunity o WHERE o.id = l.opportunity_id
  );

  SELECT COUNT(*) INTO not_approved
  FROM segsense.published_context_link l
  JOIN segsense.contextual_opportunity o ON o.id = l.opportunity_id
  WHERE o.approved_revision IS DISTINCT FROM l.revision_number;

  SELECT COUNT(*) INTO missing_revision
  FROM segsense.published_context_link l
  WHERE NOT EXISTS (
    SELECT 1
    FROM segsense.contextual_opportunity_revision r
    WHERE r.opportunity_id = l.opportunity_id
      AND r.revision_number = l.revision_number
  );

  SELECT COUNT(*) INTO scope_mismatch
  FROM segsense.published_context_link l
  JOIN segsense.contextual_opportunity o ON o.id = l.opportunity_id
  WHERE o.publisher_id <> l.publisher_id
     OR o.channel_id <> l.channel_id
     OR o.environment_id <> l.environment_id;

  SELECT COUNT(*) INTO unknown_binding
  FROM segsense.published_context_link_binding b
  JOIN segsense.published_context_link l ON l.id = b.link_id
  WHERE NOT EXISTS (
    SELECT 1
    FROM segsense.contextual_opportunity_revision r
    JOIN segsense.contextual_opportunity_revision_field f
      ON f.opportunity_revision_id = r.id
    WHERE r.opportunity_id = l.opportunity_id
      AND r.revision_number = l.revision_number
      AND f.field_key = b.field_key
      AND f.type = b.field_type
  );

  SELECT COUNT(*) INTO user_binding
  FROM segsense.published_context_link_binding b
  JOIN segsense.published_context_link l ON l.id = b.link_id
  JOIN segsense.contextual_opportunity_revision r
    ON r.opportunity_id = l.opportunity_id
   AND r.revision_number = l.revision_number
  JOIN segsense.contextual_opportunity_revision_field f
    ON f.opportunity_revision_id = r.id
   AND f.field_key = b.field_key
  WHERE f.source = 'USER';

  IF missing_opportunity > 0
     OR not_approved > 0
     OR missing_revision > 0
     OR scope_mismatch > 0
     OR unknown_binding > 0
     OR user_binding > 0 THEN
    RAISE EXCEPTION
      'V8 aborted without mutation: missing_opportunity=%, not_approved=%, missing_revision=%, scope_mismatch=%, unknown_binding=%, user_binding=%',
      missing_opportunity, not_approved, missing_revision, scope_mismatch, unknown_binding, user_binding;
  END IF;
END $guard$;

ALTER TABLE segsense.contextual_opportunity
    ADD CONSTRAINT opportunity_id_approved_revision_unique
        UNIQUE (id, approved_revision);

ALTER TABLE segsense.published_context_link
    ADD CONSTRAINT published_context_link_approved_revision_fk
        FOREIGN KEY (opportunity_id, revision_number)
        REFERENCES segsense.contextual_opportunity (id, approved_revision)
        ON DELETE NO ACTION ON UPDATE NO ACTION;

ALTER TABLE segsense.contextual_opportunity_revision
    ADD CONSTRAINT opportunity_revision_id_natural_unique
        UNIQUE (id, opportunity_id, revision_number);

ALTER TABLE segsense.published_context_link
    ADD COLUMN opportunity_revision_id UUID;

UPDATE segsense.published_context_link l
SET opportunity_revision_id = r.id
FROM segsense.contextual_opportunity_revision r
WHERE r.opportunity_id = l.opportunity_id
  AND r.revision_number = l.revision_number;

DO $fill_link$
DECLARE missing bigint;
BEGIN
  SELECT COUNT(*) INTO missing
  FROM segsense.published_context_link
  WHERE opportunity_revision_id IS NULL;
  IF missing > 0 THEN
    RAISE EXCEPTION
      'V8 aborted: % links lack an unambiguous revision identity', missing;
  END IF;
END $fill_link$;

ALTER TABLE segsense.published_context_link
    ALTER COLUMN opportunity_revision_id SET NOT NULL;

ALTER TABLE segsense.published_context_link
    ADD CONSTRAINT published_context_link_revision_identity_fk
        FOREIGN KEY (opportunity_revision_id, opportunity_id, revision_number)
        REFERENCES segsense.contextual_opportunity_revision (id, opportunity_id, revision_number)
        ON DELETE NO ACTION ON UPDATE NO ACTION;

ALTER TABLE segsense.published_context_link
    ADD CONSTRAINT published_context_link_id_revision_unique
        UNIQUE (id, opportunity_revision_id);

ALTER TABLE segsense.contextual_opportunity_revision_field
    ADD CONSTRAINT opportunity_revision_field_definition_unique
        UNIQUE (opportunity_revision_id, field_key, type, source);

ALTER TABLE segsense.published_context_link_binding
    ADD COLUMN opportunity_revision_id UUID,
    ADD COLUMN field_source VARCHAR(16);

UPDATE segsense.published_context_link_binding b
SET opportunity_revision_id = src.opportunity_revision_id,
    field_source = src.source
FROM (
    SELECT l.id AS link_id,
           l.opportunity_revision_id,
           f.field_key,
           f.type,
           f.source
    FROM segsense.published_context_link l
    JOIN segsense.contextual_opportunity_revision_field f
      ON f.opportunity_revision_id = l.opportunity_revision_id
     AND f.source IN ('PUBLISHER', 'EITHER')
) src
WHERE b.link_id = src.link_id
  AND b.field_key = src.field_key
  AND b.field_type = src.type;

DO $fill_binding$
DECLARE missing bigint;
BEGIN
  SELECT COUNT(*) INTO missing
  FROM segsense.published_context_link_binding
  WHERE opportunity_revision_id IS NULL OR field_source IS NULL;
  IF missing > 0 THEN
    RAISE EXCEPTION
      'V8 aborted: % bindings lack an unambiguous field definition', missing;
  END IF;
END $fill_binding$;

ALTER TABLE segsense.published_context_link_binding
    ALTER COLUMN opportunity_revision_id SET NOT NULL,
    ALTER COLUMN field_source SET NOT NULL;

ALTER TABLE segsense.published_context_link_binding
    ADD CONSTRAINT published_context_link_binding_source_chk
        CHECK (field_source IN ('PUBLISHER', 'EITHER'));

ALTER TABLE segsense.published_context_link_binding
    ADD CONSTRAINT published_context_link_binding_revision_fk
        FOREIGN KEY (link_id, opportunity_revision_id)
        REFERENCES segsense.published_context_link (id, opportunity_revision_id)
        ON DELETE NO ACTION ON UPDATE NO ACTION;

ALTER TABLE segsense.published_context_link_binding
    ADD CONSTRAINT published_context_link_binding_field_fk
        FOREIGN KEY (opportunity_revision_id, field_key, field_type, field_source)
        REFERENCES segsense.contextual_opportunity_revision_field
            (opportunity_revision_id, field_key, type, source)
        ON DELETE NO ACTION ON UPDATE NO ACTION;
