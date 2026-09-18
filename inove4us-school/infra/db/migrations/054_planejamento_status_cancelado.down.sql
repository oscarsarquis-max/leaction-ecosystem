UPDATE public.school_planejamento_escolar
   SET status_push = 'enviado'
 WHERE status_push = 'cancelado';

ALTER TABLE public.school_planejamento_escolar
    DROP CONSTRAINT IF EXISTS school_planejamento_escolar_status_push_check;

ALTER TABLE public.school_planejamento_escolar
    ADD CONSTRAINT school_planejamento_escolar_status_push_check
    CHECK (status_push IN ('rascunho', 'enviado', 'erro'));
