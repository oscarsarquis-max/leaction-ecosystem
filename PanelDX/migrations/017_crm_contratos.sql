-- CRM PanelDX — planos dinâmicos e contratos por cliente (MRR / vigência)
-- Executar após migrations anteriores (012+).

BEGIN;

-- ---------------------------------------------------------------------------
-- A) Planos comerciais
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.dx_planos (
    id              SERIAL PRIMARY KEY,
    nome            VARCHAR(120) NOT NULL,
    valor_mensal    NUMERIC(12, 2) NOT NULL DEFAULT 0,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    atualizado_em   TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dx_planos_nome_lower
    ON public.dx_planos (LOWER(TRIM(nome)));

COMMENT ON TABLE public.dx_planos IS
    'Catálogo de planos comerciais PanelDX — preço base para novos contratos';

COMMENT ON COLUMN public.dx_planos.valor_mensal IS
    'Valor de referência mensal; contratos gravam valor_negociado na assinatura';

-- ---------------------------------------------------------------------------
-- B) Contratos por cliente
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.dx_contratos (
    id                  SERIAL PRIMARY KEY,
    id_clie             INTEGER NOT NULL REFERENCES public.ctdi_clie(id_clie) ON DELETE CASCADE,
    id_plano            INTEGER NOT NULL REFERENCES public.dx_planos(id) ON DELETE RESTRICT,
    valor_negociado     NUMERIC(12, 2) NOT NULL,
    status              VARCHAR(32) NOT NULL DEFAULT 'trial',
    data_inicio         DATE NOT NULL,
    data_vencimento     DATE NOT NULL,
    criado_em           TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    atualizado_em       TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT dx_contratos_status_chk
        CHECK (status IN ('ativo', 'inadimplente', 'cancelado', 'trial')),
    CONSTRAINT dx_contratos_datas_chk
        CHECK (data_vencimento >= data_inicio)
);

CREATE INDEX IF NOT EXISTS idx_dx_contratos_id_clie
    ON public.dx_contratos (id_clie);

CREATE INDEX IF NOT EXISTS idx_dx_contratos_status
    ON public.dx_contratos (status);

CREATE INDEX IF NOT EXISTS idx_dx_contratos_plano_status
    ON public.dx_contratos (id_plano, status);

-- Um contrato "aberto" por cliente (ativo, trial ou inadimplente)
CREATE UNIQUE INDEX IF NOT EXISTS idx_dx_contratos_um_aberto_por_clie
    ON public.dx_contratos (id_clie)
    WHERE status IN ('ativo', 'trial', 'inadimplente');

COMMENT ON TABLE public.dx_contratos IS
    'Contrato comercial do cliente — valor_negociado congela preço na assinatura';

COMMENT ON COLUMN public.dx_contratos.valor_negociado IS
    'Valor mensal acordado no momento da assinatura (imutável para MRR histórico)';

-- ---------------------------------------------------------------------------
-- C) Seed canônico — 3 planos default
-- ---------------------------------------------------------------------------
INSERT INTO public.dx_planos (nome, valor_mensal, ativo)
SELECT v.nome, v.valor_mensal, TRUE
FROM (VALUES
    ('Conta Básica', 999.00::NUMERIC),
    ('Conta Avançada', 1999.00::NUMERIC),
    ('Conta Premium', 2999.00::NUMERIC)
) AS v(nome, valor_mensal)
WHERE NOT EXISTS (
    SELECT 1 FROM public.dx_planos p
    WHERE LOWER(TRIM(p.nome)) = LOWER(TRIM(v.nome))
);

COMMIT;
