-- Aviso da Mesa pode mirar um professor (id_clie B2C).
-- Retorno da curadoria grava o texto enviado ao docente.

BEGIN;

ALTER TABLE public.school_avisos_mesa
    ADD COLUMN IF NOT EXISTS professor_b2c_id INTEGER;

ALTER TABLE public.school_avisos_mesa
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(64) NOT NULL DEFAULT 'geral';

ALTER TABLE public.school_avisos_mesa
    DROP CONSTRAINT IF EXISTS chk_school_avisos_mesa_texto;

ALTER TABLE public.school_avisos_mesa
    ADD CONSTRAINT chk_school_avisos_mesa_texto
    CHECK (char_length(trim(texto)) BETWEEN 1 AND 4000);

CREATE INDEX IF NOT EXISTS idx_school_avisos_mesa_professor
    ON public.school_avisos_mesa (instituicao_id, professor_b2c_id)
    WHERE ativo = TRUE AND professor_b2c_id IS NOT NULL;

COMMENT ON COLUMN public.school_avisos_mesa.professor_b2c_id IS
  'id_clie do Inove. Preenchido = aviso individual (turma/disciplina NULL).';
COMMENT ON COLUMN public.school_avisos_mesa.tipo IS
  'geral | resposta_proposta_metodologica';

ALTER TABLE public.school_curadoria_metodologias
    ADD COLUMN IF NOT EXISTS retorno_docente TEXT;

ALTER TABLE public.school_curadoria_metodologias
    ADD COLUMN IF NOT EXISTS resultado_analise VARCHAR(32);

COMMENT ON COLUMN public.school_curadoria_metodologias.retorno_docente IS
  'Texto obrigatório do coordenador ao fechar a sugestão (aviso na Mesa).';
COMMENT ON COLUMN public.school_curadoria_metodologias.resultado_analise IS
  'aprovada | adaptada | nao_incorporada';

COMMIT;
