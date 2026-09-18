BEGIN;
ALTER TABLE public.inove_roteiro_conteudo_cache
  DROP CONSTRAINT IF EXISTS ck_inove_roteiro_conteudo_fonte;
ALTER TABLE public.inove_roteiro_conteudo_cache
  ADD CONSTRAINT ck_inove_roteiro_conteudo_fonte
  CHECK (fonte IN ('bncc', 'ementa'));
COMMIT;
