-- Define webhook_url padrão do inove4us (dev).
-- Em produção: sobrescrever via APP_WEBHOOK_URL_INOVE4US (gateway) ou painel admin —
-- não depender deste valor localhost.

UPDATE app_registry
SET webhook_url = 'http://localhost:5000/api/webhooks/actionhub'
WHERE app_id = 'inove4us'
  AND (
    webhook_url IS NULL
    OR btrim(webhook_url) = ''
    OR webhook_url LIKE 'http://localhost:%'
  );
