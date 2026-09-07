-- Retorno ao docente também na curadoria PEI (mesma trava do loop 53).

BEGIN;

ALTER TABLE public.school_curadoria_pei
    ADD COLUMN IF NOT EXISTS retorno_docente TEXT;

ALTER TABLE public.school_curadoria_pei
    ADD COLUMN IF NOT EXISTS resultado_analise VARCHAR(32);

COMMENT ON COLUMN public.school_curadoria_pei.retorno_docente IS
  'Texto obrigatório do coordenador ao incorporar a sugestão (aviso na Mesa).';
COMMENT ON COLUMN public.school_curadoria_pei.resultado_analise IS
  'aprovada | adaptada | nao_incorporada';

COMMIT;
