-- 028: Governança de qualidade da Sprint (Vetor 1)
-- Progresso = média das notas_qualidade das métricas avaliadas.
-- DoD = checkboxes binários (concluido); obrigatório 100% para encerrar.

BEGIN;

CREATE TABLE IF NOT EXISTS public.dx_entregas_metricas (
    id              SERIAL PRIMARY KEY,
    id_sprn         INTEGER NOT NULL
                    REFERENCES public.ctdi_sprn(id_sprn) ON DELETE CASCADE,
    -- Chave estável da métrica derivada de leaf_derv.derv_metr (texto canônico).
    id_metrica      INTEGER,
    metrica_chave   TEXT NOT NULL,
    metrica_rotulo  TEXT NOT NULL,
    documento_url   TEXT,
    depoimento      TEXT,
    nota_qualidade  NUMERIC(5, 2)
                    CHECK (nota_qualidade IS NULL OR (nota_qualidade >= 0 AND nota_qualidade <= 100)),
    avaliado_em     TIMESTAMP WITHOUT TIME ZONE,
    id_moderador    INTEGER
                    REFERENCES public.paneldx_usuarios(id_usuario) ON DELETE SET NULL,
    criado_em       TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT dx_entregas_metricas_sprn_chave_uq UNIQUE (id_sprn, metrica_chave)
);

COMMENT ON TABLE public.dx_entregas_metricas IS
    'Comprovações e auditoria de qualidade por métrica da sprint (Vetor 1).';
COMMENT ON COLUMN public.dx_entregas_metricas.id_metrica IS
    'Espelho do id da entrega (API id_metrica); preenchido após insert.';
COMMENT ON COLUMN public.dx_entregas_metricas.nota_qualidade IS
    'Nota 0–100 atribuída pelo moderador; progresso da sprint = média das notas preenchidas.';

CREATE INDEX IF NOT EXISTS idx_dx_entregas_metricas_sprn
    ON public.dx_entregas_metricas (id_sprn);

CREATE INDEX IF NOT EXISTS idx_dx_entregas_metricas_moderador
    ON public.dx_entregas_metricas (id_moderador)
    WHERE id_moderador IS NOT NULL;

-- Após insert, id_metrica = id (fonte de verdade para a API).
CREATE OR REPLACE FUNCTION public.fn_dx_entregas_metricas_sync_id_metrica()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    UPDATE public.dx_entregas_metricas
       SET id_metrica = NEW.id,
           atualizado_em = NOW()
     WHERE id = NEW.id
       AND (id_metrica IS NULL OR id_metrica IS DISTINCT FROM NEW.id);
    RETURN NULL;
END;
$function$;

DROP TRIGGER IF EXISTS trg_dx_entregas_metricas_sync_id_metrica
    ON public.dx_entregas_metricas;
CREATE TRIGGER trg_dx_entregas_metricas_sync_id_metrica
    AFTER INSERT ON public.dx_entregas_metricas
    FOR EACH ROW
    EXECUTE FUNCTION public.fn_dx_entregas_metricas_sync_id_metrica();

-- Critérios DoD declarativos: apenas concluido boolean (sem nota de qualidade).
CREATE TABLE IF NOT EXISTS public.dx_dod_itens (
    id              SERIAL PRIMARY KEY,
    id_sprn         INTEGER NOT NULL
                    REFERENCES public.ctdi_sprn(id_sprn) ON DELETE CASCADE,
    criterio_chave  TEXT NOT NULL,
    criterio_texto  TEXT NOT NULL,
    grupo           TEXT NOT NULL DEFAULT 'required',
    concluido       BOOLEAN NOT NULL DEFAULT FALSE,
    atualizado_em   TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT dx_dod_itens_sprn_chave_uq UNIQUE (id_sprn, criterio_chave),
    CONSTRAINT dx_dod_itens_grupo_chk CHECK (grupo IN ('required', 'context_education', 'outros'))
);

COMMENT ON TABLE public.dx_dod_itens IS
    'Definition of Done da sprint: itens binários (concluido). Não entram na média de qualidade.';
COMMENT ON COLUMN public.dx_dod_itens.concluido IS
    'true = critério atendido. Sprint só pode ser concluída com 100% true.';

CREATE INDEX IF NOT EXISTS idx_dx_dod_itens_sprn
    ON public.dx_dod_itens (id_sprn);

COMMIT;
