-- 149: cache do roteiro também por habilidade ENEM.
BEGIN;

ALTER TABLE public.inove_roteiro_conteudo_cache
  DROP CONSTRAINT IF EXISTS ck_inove_roteiro_conteudo_fonte;

ALTER TABLE public.inove_roteiro_conteudo_cache
  ADD CONSTRAINT ck_inove_roteiro_conteudo_fonte
  CHECK (fonte IN ('bncc', 'ementa', 'enem'));

COMMENT ON TABLE public.inove_roteiro_conteudo_cache IS
  'Conteúdo sugerido da disciplina, gerado 1× por tema oficial×nível (BNCC ou ENEM).';

COMMIT;
