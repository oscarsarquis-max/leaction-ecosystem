BEGIN;
DROP VIEW IF EXISTS public.school_enem_habilidades_canonico;
DROP TABLE IF EXISTS public.enem_disciplina_alias;
DROP TABLE IF EXISTS public.enem_disciplina_mapeamento;
DROP FUNCTION IF EXISTS public.enem_norm_disciplina(text);
COMMIT;
