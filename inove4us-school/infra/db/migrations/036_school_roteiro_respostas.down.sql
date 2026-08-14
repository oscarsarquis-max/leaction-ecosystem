-- Rollback 036 — remove respostas do Roteiro Guiado.

BEGIN;

DROP TABLE IF EXISTS public.school_roteiro_respostas;

COMMIT;
