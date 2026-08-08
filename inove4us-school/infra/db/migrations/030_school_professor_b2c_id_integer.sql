-- 030: professor_b2c_id UUID → INTEGER (id_clie do B2C / ctdi_clie.id_clie)
--
-- Passo 0 (inove4us): information_schema + FK em inove_aulas_simples /
-- inove_comunicados_escola_destinatarios confirmam id_clie INTEGER (int4).
-- Sem cast UUID→int (não há conversão válida); linhas de teste são removidas.
--
-- Impacto: nenhuma outra tabela referencia professor_b2c_id. Dependentes usam
-- school_professores_vinculo.id (UUID PK) via professor_vinculo_id.

DO $$
DECLARE
    col_type text;
BEGIN
    SELECT data_type INTO col_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'school_professores_vinculo'
      AND column_name = 'professor_b2c_id';

    IF col_type IS NULL THEN
        ALTER TABLE public.school_professores_vinculo
            ADD COLUMN professor_b2c_id INTEGER NOT NULL;
    ELSIF col_type = 'uuid' THEN
        -- Dado de teste / provisório UUID — não é id_clie real
        DELETE FROM public.school_professores_vinculo;

        ALTER TABLE public.school_professores_vinculo
            DROP CONSTRAINT IF EXISTS uq_school_prof_vinculo_inst_prof;

        DROP INDEX IF EXISTS public.idx_school_prof_vinculo_professor;

        ALTER TABLE public.school_professores_vinculo
            DROP COLUMN professor_b2c_id;

        ALTER TABLE public.school_professores_vinculo
            ADD COLUMN professor_b2c_id INTEGER NOT NULL;
    ELSIF col_type IN ('integer', 'bigint', 'smallint') THEN
        -- Já migrado (ou tipo compatível); só garante constraints abaixo
        NULL;
    ELSE
        RAISE EXCEPTION
            '030: professor_b2c_id tem tipo inesperado: %', col_type;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_school_prof_vinculo_inst_prof'
          AND conrelid = 'public.school_professores_vinculo'::regclass
    ) THEN
        ALTER TABLE public.school_professores_vinculo
            ADD CONSTRAINT uq_school_prof_vinculo_inst_prof
                UNIQUE (instituicao_id, professor_b2c_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_school_prof_vinculo_professor
    ON public.school_professores_vinculo (professor_b2c_id);

COMMENT ON COLUMN public.school_professores_vinculo.professor_b2c_id IS
  'id_clie do professor no B2C (public.ctdi_clie.id_clie / INTEGER). Sem FK cross-database — comunicação via API.';
