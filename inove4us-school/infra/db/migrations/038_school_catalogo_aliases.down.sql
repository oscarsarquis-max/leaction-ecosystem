-- Rollback 038 — remove aliases. Nomes já regravados no canônico permanecem.

BEGIN;

DROP INDEX IF EXISTS public.idx_school_metodologias_aliases_codigo;
DROP TABLE IF EXISTS public.school_metodologias_aliases;

COMMIT;
