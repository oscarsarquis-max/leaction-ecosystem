BEGIN;

ALTER TABLE public.school_curadoria_metodologias
    DROP COLUMN IF EXISTS retorno_docente;
ALTER TABLE public.school_curadoria_metodologias
    DROP COLUMN IF EXISTS resultado_analise;

DROP INDEX IF EXISTS public.idx_school_avisos_mesa_professor;

ALTER TABLE public.school_avisos_mesa
    DROP COLUMN IF EXISTS professor_b2c_id;
ALTER TABLE public.school_avisos_mesa
    DROP COLUMN IF EXISTS tipo;

ALTER TABLE public.school_avisos_mesa
    DROP CONSTRAINT IF EXISTS chk_school_avisos_mesa_texto;
ALTER TABLE public.school_avisos_mesa
    ADD CONSTRAINT chk_school_avisos_mesa_texto
    CHECK (char_length(trim(texto)) BETWEEN 1 AND 500);

COMMIT;
