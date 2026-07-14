-- 027 (prod-safe): ciclo de vida dos KRs + dx_kr_id opcional em atividades
-- Idempotente para ambientes onde dx_kr_id ainda não existe.

ALTER TABLE public.ctdi_okr_krs
    ADD COLUMN IF NOT EXISTS ativo boolean NOT NULL DEFAULT true;

COMMENT ON COLUMN public.ctdi_okr_krs.ativo IS
    'false = KR suprimido pelo cliente (não reaparece no seed da matriz).';

-- Garante a coluna (nullable) quando o ambiente ainda não a tinha
ALTER TABLE public.ctdi_okr_atividades
    ADD COLUMN IF NOT EXISTS dx_kr_id integer;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'ctdi_okr_atividades'
          AND column_name = 'dx_kr_id'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE public.ctdi_okr_atividades
            ALTER COLUMN dx_kr_id DROP NOT NULL;
    END IF;
END $$;

-- FK para catálogo canônico (somente se dx_krs existir)
DO $$
BEGIN
    IF to_regclass('public.dx_krs') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1 FROM pg_constraint
           WHERE conname = 'fk_atividade_dx_kr'
       ) THEN
        ALTER TABLE public.ctdi_okr_atividades
            ADD CONSTRAINT fk_atividade_dx_kr
            FOREIGN KEY (dx_kr_id) REFERENCES public.dx_krs(id) ON DELETE RESTRICT;
    END IF;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN undefined_table THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_ctdi_okr_atividades_dx_kr
    ON public.ctdi_okr_atividades (dx_kr_id);

CREATE OR REPLACE FUNCTION public.fn_sync_atividade_dx_kr_id()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
DECLARE
    v_dx_kr_id integer;
    v_ativo boolean;
BEGIN
    IF NEW.id_kr IS NULL THEN
        RAISE EXCEPTION 'id_kr é obrigatório em ctdi_okr_atividades';
    END IF;

    SELECT dx_kr_id, COALESCE(ativo, true)
      INTO v_dx_kr_id, v_ativo
    FROM public.ctdi_okr_krs
    WHERE id_kr = NEW.id_kr;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'KR cliente % não encontrado', NEW.id_kr;
    END IF;

    IF v_ativo IS FALSE THEN
        RAISE EXCEPTION 'KR cliente % está suprimido e não pode receber atividades', NEW.id_kr;
    END IF;

    NEW.dx_kr_id := v_dx_kr_id;
    RETURN NEW;
END;
$function$;

DROP TRIGGER IF EXISTS tg_sync_atividade_dx_kr ON public.ctdi_okr_atividades;
CREATE TRIGGER tg_sync_atividade_dx_kr
    BEFORE INSERT OR UPDATE OF id_kr ON public.ctdi_okr_atividades
    FOR EACH ROW
    EXECUTE FUNCTION public.fn_sync_atividade_dx_kr_id();
