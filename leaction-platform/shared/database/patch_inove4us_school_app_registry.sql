-- Action Hub — registra satélite inove4us-school no app_registry.
-- Idempotente: INSERT + ON CONFLICT atualiza webhook/secret/active.
--
-- Outbox: com webhook_url + webhook_secret preenchidos, o worker despacha
-- eventos deste app_id para http://localhost:5012/api/webhooks/actionhub
-- Override opcional via env: APP_WEBHOOK_URL_INOVE4US_SCHOOL
--
-- Aplicar (ex. DB local do Hub):
--   psql -h 127.0.0.1 -p 5434 -U admin -d leaction_hub -v ON_ERROR_STOP=1 \
--     -f shared/database/patch_inove4us_school_app_registry.sql
-- (ajuste host/porta/db conforme o .env do gateway)

BEGIN;

INSERT INTO app_registry (
    app_id,
    name,
    webhook_url,
    webhook_secret,
    return_origins,
    active
)
VALUES (
    'inove4us-school',
    'Inove4us School B2B',
    'http://localhost:5012/api/webhooks/actionhub',
    'sk_test_school_webhook_secret_999',
    ARRAY[
        'http://localhost:5175',
        'http://127.0.0.1:5175'
    ]::TEXT[],
    TRUE
)
ON CONFLICT (app_id) DO UPDATE SET
    name           = EXCLUDED.name,
    webhook_url    = EXCLUDED.webhook_url,
    webhook_secret = EXCLUDED.webhook_secret,
    return_origins = EXCLUDED.return_origins,
    active         = EXCLUDED.active;

COMMIT;

-- Verificação:
-- SELECT app_id, name, webhook_url, active,
--        left(webhook_secret, 12) || '…' AS secret_prefix,
--        return_origins
-- FROM app_registry
-- WHERE app_id = 'inove4us-school';
