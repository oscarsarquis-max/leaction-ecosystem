-- 154 — cancelar aula libera o slot (104) e registra o cancelamento no planejamento.

DO $$
DECLARE r record;
BEGIN
    FOR r IN
        SELECT conname
          FROM pg_constraint
         WHERE conrelid = 'public.school_planejamento_escolar'::regclass
           AND contype = 'c'
           AND pg_get_constraintdef(oid) ILIKE '%status_push%'
    LOOP
        EXECUTE format(
            'ALTER TABLE public.school_planejamento_escolar DROP CONSTRAINT IF EXISTS %I',
            r.conname
        );
    END LOOP;
END $$;

ALTER TABLE public.school_planejamento_escolar
    ADD CONSTRAINT school_planejamento_escolar_status_push_check
    CHECK (status_push IN ('rascunho', 'enviado', 'erro', 'cancelado'));

COMMENT ON COLUMN public.school_planejamento_escolar.status_push IS
  'rascunho | enviado | erro | cancelado — cancelado não compete por horário.';
