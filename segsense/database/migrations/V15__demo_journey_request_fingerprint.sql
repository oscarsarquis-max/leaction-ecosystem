-- PRM_016_COR_001: canonical idempotency fingerprint. V1–V14 unchanged.
-- Nullable so existing rows remain readable. Replay of those keys is fail-closed (409).

ALTER TABLE segsense.demo_protection_journey
    ADD COLUMN request_fingerprint CHAR(64);
