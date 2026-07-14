-- 027: ciclo de vida dos KRs do cliente (editáveis / suprimíveis / custom)
-- e atividades podem vincular KRs custom (sem dx_kr_id).

ALTER TABLE public.ctdi_okr_krs
    ADD COLUMN IF NOT EXISTS ativo boolean NOT NULL DEFAULT true;

COMMENT ON COLUMN public.ctdi_okr_krs.ativo IS
    'false = KR suprimido pelo cliente (não reaparece no seed da matriz).';

-- Atividades: dx_kr_id deixa de ser obrigatório para KRs personalizados
ALTER TABLE public.ctdi_okr_atividades
    ALTER COLUMN dx_kr_id DROP NOT NULL;

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

    -- KRs canônicos sincronizam; custom (dx_kr_id null) seguem só pelo id_kr
    NEW.dx_kr_id := v_dx_kr_id;
    RETURN NEW;
END;
$function$;
