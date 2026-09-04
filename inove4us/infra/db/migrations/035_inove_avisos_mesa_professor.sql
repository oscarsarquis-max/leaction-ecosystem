-- Aviso individual do School (professor_b2c_id = id_clie) + tipo da tag.

BEGIN;

ALTER TABLE public.inove_avisos_mesa
    ADD COLUMN IF NOT EXISTS professor_b2c_id INTEGER;

ALTER TABLE public.inove_avisos_mesa
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(64) NOT NULL DEFAULT 'geral';

ALTER TABLE public.inove_avisos_mesa
    ADD COLUMN IF NOT EXISTS meta_json JSONB;

CREATE INDEX IF NOT EXISTS idx_inove_avisos_mesa_professor
    ON public.inove_avisos_mesa (instituicao_b2b_id, professor_b2c_id)
    WHERE ativo = TRUE AND professor_b2c_id IS NOT NULL;

COMMENT ON COLUMN public.inove_avisos_mesa.professor_b2c_id IS
  'id_clie alvo. NULL = aviso da instituição (comportamento antigo).';
COMMENT ON COLUMN public.inove_avisos_mesa.tipo IS
  'geral | resposta_proposta_metodologica';

COMMIT;
