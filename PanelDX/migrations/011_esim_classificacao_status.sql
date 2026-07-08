-- Status de classificação do evento eSIM (catálogo LeAction)
ALTER TABLE public.esim_eventos
    ADD COLUMN IF NOT EXISTS classificacao_status VARCHAR(32) NOT NULL DEFAULT 'classificado';

CREATE INDEX IF NOT EXISTS idx_esim_eventos_classificacao
    ON public.esim_eventos (classificacao_status, recebido_em DESC);

COMMENT ON COLUMN public.esim_eventos.classificacao_status IS
    'classificado | nao_classificado — eventos sem match em esim_eventos_catalog';
