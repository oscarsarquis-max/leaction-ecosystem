-- Enforce that a contextual_environment publisher_id matches its channel's publisher.
-- Does not change or delete existing rows. Fails explicitly if any row is inconsistent.
-- V1 and V2 remain unchanged. No CASCADE. No triggers.

DO $$
DECLARE
    inconsistent_count INTEGER;
BEGIN
    SELECT COUNT(*)
      INTO inconsistent_count
      FROM segsense.contextual_environment environment
      JOIN segsense.channel channel ON channel.id = environment.channel_id
     WHERE environment.publisher_id <> channel.publisher_id;

    IF inconsistent_count > 0 THEN
        RAISE EXCEPTION
            'V3 aborted: % contextual_environment row(s) have publisher_id different from channel.publisher_id',
            inconsistent_count;
    END IF;
END
$$;

ALTER TABLE segsense.channel
    ADD CONSTRAINT channel_id_publisher_unique UNIQUE (id, publisher_id);

CREATE INDEX IF NOT EXISTS environment_channel_publisher_idx
    ON segsense.contextual_environment (channel_id, publisher_id);

ALTER TABLE segsense.contextual_environment
    ADD CONSTRAINT environment_channel_scope_fk
        FOREIGN KEY (channel_id, publisher_id)
        REFERENCES segsense.channel (id, publisher_id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION;

ALTER TABLE segsense.contextual_environment
    DROP CONSTRAINT environment_channel_fk;
