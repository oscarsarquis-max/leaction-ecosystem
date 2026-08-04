-- inove4us School — tabela de assentos/licenças comerciais (Hub → School).
-- Numeração: 018.

BEGIN;

CREATE TABLE IF NOT EXISTS public.school_licencas (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id    UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    total_assentos    INTEGER NOT NULL DEFAULT 0
        CHECK (total_assentos >= 0),
    assentos_em_uso   INTEGER NOT NULL DEFAULT 0
        CHECK (assentos_em_uso >= 0),
    sku_ultimo        TEXT,
    contrato_hub_id   TEXT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_licencas_instituicao UNIQUE (instituicao_id)
);

CREATE INDEX IF NOT EXISTS idx_school_licencas_instituicao
    ON public.school_licencas (instituicao_id);

COMMENT ON TABLE public.school_licencas IS
  'Assentos comerciais concedidos pelo Action Hub (LICENSES_GRANTED / CONTRACT_ACTIVATED).';
COMMENT ON COLUMN public.school_licencas.total_assentos IS
  'Soma acumulada de licenses_granted recebidas do Hub.';
COMMENT ON COLUMN public.school_licencas.assentos_em_uso IS
  'Snapshot de professores com vínculo ativo (atualizado no grant e nas leituras da Equipe).';

-- Backfill a partir de school_instituicoes.licencas_contratadas (legado)
INSERT INTO public.school_licencas (instituicao_id, total_assentos, assentos_em_uso)
SELECT
    i.id,
    COALESCE(i.licencas_contratadas, 0),
    COALESCE((
        SELECT count(*)::int
        FROM public.school_professores_vinculo v
        WHERE v.instituicao_id = i.id AND v.status_vinculo = 'ativo'
    ), 0)
FROM public.school_instituicoes i
WHERE i.licencas_contratadas IS NOT NULL
ON CONFLICT (instituicao_id) DO NOTHING;

COMMIT;
