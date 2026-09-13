-- SegSense technical baseline. No insurance, publisher, journey or integration tables.

CREATE SCHEMA IF NOT EXISTS segsense;

CREATE TABLE segsense.runtime_marker (
    id SMALLINT PRIMARY KEY,
    initialized_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO segsense.runtime_marker (id)
VALUES (1);
