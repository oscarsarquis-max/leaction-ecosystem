-- Atividades de sprint obrigatoriamente amarradas ao KR canônico (dx_krs)
-- Progresso bottom-up: atividades → KR → objetivo

BEGIN;

ALTER TABLE public.ctdi_okr_atividades
    ADD COLUMN IF NOT EXISTS dx_kr_id INTEGER;

UPDATE public.ctdi_okr_atividades a
SET dx_kr_id = k.dx_kr_id
FROM public.ctdi_okr_krs k
WHERE k.id_kr = a.id_kr
  AND a.dx_kr_id IS NULL
  AND k.dx_kr_id IS NOT NULL;

-- Atividades órfãs: tenta inferir único KR do objetivo da sprint
UPDATE public.ctdi_okr_atividades a
SET dx_kr_id = sub.dx_kr_id
FROM (
    SELECT a2.id_ativ,
           (ARRAY_AGG(k.dx_kr_id ORDER BY k.dx_kr_id))[1] AS dx_kr_id
    FROM public.ctdi_okr_atividades a2
    JOIN public.ctdi_sprn s ON s.id_sprn = a2.id_sprn
    JOIN public.ctdi_okr_objetivos_dt o ON o.dx_objetivo_id = s.objetivo_id
    JOIN public.ctdi_okr_krs k ON k.id_obj_dt = o.id_obj_dt AND k.dx_kr_id IS NOT NULL
    WHERE a2.dx_kr_id IS NULL
      AND s.objetivo_id IS NOT NULL
    GROUP BY a2.id_ativ
    HAVING COUNT(DISTINCT k.dx_kr_id) = 1
) sub
WHERE a.id_ativ = sub.id_ativ
  AND a.dx_kr_id IS NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM public.ctdi_okr_atividades WHERE dx_kr_id IS NULL
    ) THEN
        RAISE NOTICE 'Aviso: existem atividades sem dx_kr_id — revise antes de tornar NOT NULL.';
    ELSE
        ALTER TABLE public.ctdi_okr_atividades
            ALTER COLUMN dx_kr_id SET NOT NULL;
    END IF;
END $$;

ALTER TABLE public.ctdi_okr_atividades
    DROP CONSTRAINT IF EXISTS fk_atividade_dx_kr;

ALTER TABLE public.ctdi_okr_atividades
    ADD CONSTRAINT fk_atividade_dx_kr
        FOREIGN KEY (dx_kr_id) REFERENCES public.dx_krs(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_ctdi_okr_atividades_dx_kr
    ON public.ctdi_okr_atividades (dx_kr_id);

COMMENT ON COLUMN public.ctdi_okr_atividades.dx_kr_id IS
    'KR canônico (matriz dx_krs) — obrigatório para rollup bottom-up de progresso.';

-- Mantém dx_kr_id sincronizado quando id_kr (instância cliente) mudar
CREATE OR REPLACE FUNCTION public.fn_sync_atividade_dx_kr_id()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_dx_kr_id integer;
BEGIN
    IF NEW.id_kr IS NULL THEN
        RAISE EXCEPTION 'id_kr é obrigatório em ctdi_okr_atividades';
    END IF;

    SELECT dx_kr_id INTO v_dx_kr_id
    FROM public.ctdi_okr_krs
    WHERE id_kr = NEW.id_kr;

    IF v_dx_kr_id IS NULL THEN
        RAISE EXCEPTION 'KR cliente % sem vínculo dx_kr_id na matriz canônica', NEW.id_kr;
    END IF;

    NEW.dx_kr_id := v_dx_kr_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tg_sync_atividade_dx_kr ON public.ctdi_okr_atividades;
CREATE TRIGGER tg_sync_atividade_dx_kr
    BEFORE INSERT OR UPDATE OF id_kr ON public.ctdi_okr_atividades
    FOR EACH ROW
    EXECUTE FUNCTION public.fn_sync_atividade_dx_kr_id();

COMMIT;
