-- Reverte 030: INTEGER → UUID (coluna vazia; não há cast válido de id_clie).
-- Uso só em dev. Perde o vínculo lógico com id_clie.

DELETE FROM public.school_professores_vinculo;

ALTER TABLE public.school_professores_vinculo
    DROP CONSTRAINT IF EXISTS uq_school_prof_vinculo_inst_prof;

DROP INDEX IF EXISTS public.idx_school_prof_vinculo_professor;

ALTER TABLE public.school_professores_vinculo
    DROP COLUMN IF EXISTS professor_b2c_id;

ALTER TABLE public.school_professores_vinculo
    ADD COLUMN professor_b2c_id UUID NOT NULL;

ALTER TABLE public.school_professores_vinculo
    ADD CONSTRAINT uq_school_prof_vinculo_inst_prof
        UNIQUE (instituicao_id, professor_b2c_id);

CREATE INDEX IF NOT EXISTS idx_school_prof_vinculo_professor
    ON public.school_professores_vinculo (professor_b2c_id);

COMMENT ON COLUMN public.school_professores_vinculo.professor_b2c_id IS
  'UUID de referência ao professor no ecossistema B2C. Sem FK — comunicação via API/contratos.';
