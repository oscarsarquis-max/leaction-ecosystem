-- SegSense local catalog: publishers, channels and contextual environments.
-- Conceptual rollback (manual, never automatic): drop environment, then channel, then publisher.
-- V1 is unchanged. No CASCADE delete. No personal or contractual data.

CREATE TABLE segsense.publisher (
    id UUID PRIMARY KEY,
    key VARCHAR(50) NOT NULL,
    name VARCHAR(120) NOT NULL,
    status VARCHAR(16) NOT NULL,
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by VARCHAR(128) NOT NULL,
    updated_by VARCHAR(128) NOT NULL,
    CONSTRAINT publisher_key_unique UNIQUE (key),
    CONSTRAINT publisher_key_format_chk CHECK (key ~ '^[a-z][a-z0-9-]{2,49}$'),
    CONSTRAINT publisher_name_len_chk CHECK (char_length(name) BETWEEN 3 AND 120),
    CONSTRAINT publisher_status_chk CHECK (status IN ('DRAFT', 'ACTIVE', 'SUSPENDED')),
    CONSTRAINT publisher_version_chk CHECK (version >= 0)
);

CREATE INDEX publisher_status_idx ON segsense.publisher (status);
CREATE INDEX publisher_created_cursor_idx ON segsense.publisher (created_at, id);

CREATE TABLE segsense.channel (
    id UUID PRIMARY KEY,
    publisher_id UUID NOT NULL,
    key VARCHAR(50) NOT NULL,
    name VARCHAR(120) NOT NULL,
    type VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL,
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by VARCHAR(128) NOT NULL,
    updated_by VARCHAR(128) NOT NULL,
    CONSTRAINT channel_publisher_fk FOREIGN KEY (publisher_id)
        REFERENCES segsense.publisher (id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT channel_key_unique UNIQUE (publisher_id, key),
    CONSTRAINT channel_key_format_chk CHECK (key ~ '^[a-z][a-z0-9-]{2,49}$'),
    CONSTRAINT channel_name_len_chk CHECK (char_length(name) BETWEEN 3 AND 120),
    CONSTRAINT channel_type_chk CHECK (
        type IN ('WEBSITE', 'WEB_APPLICATION', 'MOBILE_APPLICATION', 'PARTNER_PORTAL')
    ),
    CONSTRAINT channel_status_chk CHECK (status IN ('DRAFT', 'ACTIVE', 'SUSPENDED')),
    CONSTRAINT channel_version_chk CHECK (version >= 0)
);

CREATE INDEX channel_publisher_status_idx ON segsense.channel (publisher_id, status);
CREATE INDEX channel_publisher_created_cursor_idx ON segsense.channel (publisher_id, created_at, id);

CREATE TABLE segsense.contextual_environment (
    id UUID PRIMARY KEY,
    publisher_id UUID NOT NULL,
    channel_id UUID NOT NULL,
    key VARCHAR(50) NOT NULL,
    name VARCHAR(120) NOT NULL,
    type VARCHAR(32) NOT NULL,
    canonical_url VARCHAR(2048),
    status VARCHAR(16) NOT NULL,
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by VARCHAR(128) NOT NULL,
    updated_by VARCHAR(128) NOT NULL,
    CONSTRAINT environment_publisher_fk FOREIGN KEY (publisher_id)
        REFERENCES segsense.publisher (id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT environment_channel_fk FOREIGN KEY (channel_id)
        REFERENCES segsense.channel (id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT environment_key_unique UNIQUE (channel_id, key),
    CONSTRAINT environment_key_format_chk CHECK (key ~ '^[a-z][a-z0-9-]{2,49}$'),
    CONSTRAINT environment_name_len_chk CHECK (char_length(name) BETWEEN 3 AND 120),
    CONSTRAINT environment_type_chk CHECK (
        type IN ('ARTICLE', 'PAGE', 'APPLICATION_SCREEN', 'EMBEDDED_COMPONENT')
    ),
    CONSTRAINT environment_status_chk CHECK (status IN ('DRAFT', 'ACTIVE', 'SUSPENDED')),
    CONSTRAINT environment_version_chk CHECK (version >= 0),
    CONSTRAINT environment_canonical_url_chk CHECK (
        canonical_url IS NULL
        OR (
            canonical_url LIKE 'https://%'
            AND position('?' IN canonical_url) = 0
            AND position('#' IN canonical_url) = 0
        )
    )
);

CREATE INDEX environment_scope_idx
    ON segsense.contextual_environment (publisher_id, channel_id);
CREATE INDEX environment_channel_status_idx
    ON segsense.contextual_environment (channel_id, status);
CREATE INDEX environment_channel_created_cursor_idx
    ON segsense.contextual_environment (channel_id, created_at, id);
