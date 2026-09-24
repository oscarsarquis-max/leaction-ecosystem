BEGIN;

DROP TABLE IF EXISTS public.school_onboarding_mail_log;

ALTER TABLE public.school_gestores
    DROP COLUMN IF EXISTS recebe_resumo_diario;

COMMIT;
