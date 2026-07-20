-- Contas de teste no inove4us (não entram em métricas de produto quando filtradas)
BEGIN;

ALTER TABLE public.ctdi_clie
  ADD COLUMN IF NOT EXISTS is_test BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE public.ctdi_clie
SET is_test = TRUE
WHERE LOWER(TRIM(mail_clie)) = 'inovador@inove4us.com.br';

COMMIT;
