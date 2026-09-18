-- 148: tabela por escola (Helenita). 150 substituiu por view generica (051).
-- Fica no-op para o bootstrap nao tentar indexar a view ja existente.

BEGIN;

DO $$
BEGIN
  RAISE NOTICE '050 no-op: school_enem_habilidades_canonico passou a ser view na 051.';
END $$;

COMMIT;
