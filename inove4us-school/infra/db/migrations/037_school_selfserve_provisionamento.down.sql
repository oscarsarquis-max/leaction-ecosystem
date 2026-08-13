-- Rollback 037. Só restaura NOT NULL em cnpj se não houver nulos.

BEGIN;

DROP TABLE IF EXISTS public.school_provisionamento_email;
DROP TABLE IF EXISTS public.school_hub_eventos_processados;

ALTER TABLE public.school_instituicoes
    DROP CONSTRAINT IF EXISTS chk_school_instituicoes_doc_tipo;

ALTER TABLE public.school_instituicoes
    DROP COLUMN IF EXISTS documento_responsavel_pagamento;

ALTER TABLE public.school_instituicoes
    DROP COLUMN IF EXISTS documento_responsavel_tipo;

DROP INDEX IF EXISTS public.uq_school_instituicoes_cnpj_not_null;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.school_instituicoes WHERE cnpj IS NULL
    ) THEN
        ALTER TABLE public.school_instituicoes
            ALTER COLUMN cnpj SET NOT NULL;
        ALTER TABLE public.school_instituicoes
            ADD CONSTRAINT uq_school_instituicoes_cnpj UNIQUE (cnpj);
    END IF;
END $$;

COMMIT;
