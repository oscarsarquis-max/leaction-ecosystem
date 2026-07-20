-- Define webhook_url padrão do inove4us (dev) — Flask local na porta 5010.
-- Em produção: sobrescrever via APP_WEBHOOK_URL_INOVE4US (gateway) ou painel admin —
-- não depender deste valor localhost.

UPDATE app_registry
SET webhook_url = 'http://127.0.0.1:5010/api/webhooks/actionhub'
WHERE app_id = 'inove4us'
  AND (
    webhook_url IS NULL
    OR btrim(webhook_url) = ''
    OR webhook_url LIKE 'http://localhost:%'
    OR webhook_url LIKE 'http://127.0.0.1:%'
  );
