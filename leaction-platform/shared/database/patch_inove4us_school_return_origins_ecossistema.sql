-- Action Hub — inclui https://inove4us.com.br em return_origins do satélite School.
-- Aditivo: NÃO altera webhook_url nem webhook_secret.

BEGIN;

UPDATE app_registry
SET return_origins = (
    SELECT ARRAY(
        SELECT DISTINCT orig
        FROM unnest(COALESCE(return_origins, ARRAY[]::TEXT[]) || ARRAY[
            'https://inove4us.com.br',
            'https://school.inove4us.com.br'
        ]) AS orig
    )
)
WHERE app_id = 'inove4us-school'
  AND (
    return_origins IS NULL
    OR NOT ('https://inove4us.com.br' = ANY (return_origins))
  );

COMMIT;
