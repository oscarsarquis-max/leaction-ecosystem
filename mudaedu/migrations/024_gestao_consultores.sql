-- Portal do Parceiro / Consultor — cadastro, vínculos em contratos e demandas
-- Nota: 021 já existe (sanitize_filatro) — esta migration usa 024.

BEGIN;

-- ---------------------------------------------------------------------------
-- A) Flag de elegibilidade à comissão técnica no plano
-- ---------------------------------------------------------------------------
ALTER TABLE public.dx_planos
    ADD COLUMN IF NOT EXISTS direito_consultoria_tecnica BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN public.dx_planos.direito_consultoria_tecnica IS
    'Plano elegível à comissão técnica do consultor (ex.: Conta Premium)';

UPDATE public.dx_planos
SET direito_consultoria_tecnica = TRUE
WHERE LOWER(TRIM(nome)) LIKE '%premium%'
   OR LOWER(TRIM(nome)) = LOWER('Conta Premium');

-- ---------------------------------------------------------------------------
-- B) Cadastro de consultores (agência vs. indivíduo)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.dx_consultores (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER NOT NULL REFERENCES public.paneldx_usuarios(id_usuario) ON DELETE CASCADE,
    tipo                    VARCHAR(16) NOT NULL DEFAULT 'individual',
    id_agencia_pai          INTEGER REFERENCES public.dx_consultores(id) ON DELETE SET NULL,
    taxa_comissao_venda     NUMERIC(5, 2) NOT NULL DEFAULT 10.00,
    taxa_comissao_tecnica   NUMERIC(5, 2) NOT NULL DEFAULT 15.00,
    ativo                   BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em               TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    atualizado_em           TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT dx_consultores_tipo_chk
        CHECK (tipo IN ('agencia', 'individual')),
    CONSTRAINT dx_consultores_taxa_venda_chk
        CHECK (taxa_comissao_venda >= 0 AND taxa_comissao_venda <= 100),
    CONSTRAINT dx_consultores_taxa_tecnica_chk
        CHECK (taxa_comissao_tecnica >= 0 AND taxa_comissao_tecnica <= 100),
    CONSTRAINT dx_consultores_agencia_sem_pai_chk
        CHECK (tipo <> 'agencia' OR id_agencia_pai IS NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dx_consultores_user_id
    ON public.dx_consultores (user_id);

CREATE INDEX IF NOT EXISTS idx_dx_consultores_agencia_pai
    ON public.dx_consultores (id_agencia_pai)
    WHERE id_agencia_pai IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dx_consultores_tipo_ativo
    ON public.dx_consultores (tipo, ativo);

COMMENT ON TABLE public.dx_consultores IS
    'Parceiros consultores PanelDX — agência ou indivíduo, com taxas de comissão';

COMMENT ON COLUMN public.dx_consultores.id_agencia_pai IS
    'Preenchido quando o consultor individual pertence a uma agência';

-- ---------------------------------------------------------------------------
-- C) Vínculos de origem e atuação técnica nos contratos
-- ---------------------------------------------------------------------------
ALTER TABLE public.dx_contratos
    ADD COLUMN IF NOT EXISTS id_consultor_origem INTEGER
        REFERENCES public.dx_consultores(id) ON DELETE SET NULL;

ALTER TABLE public.dx_contratos
    ADD COLUMN IF NOT EXISTS id_consultor_tecnico INTEGER
        REFERENCES public.dx_consultores(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_dx_contratos_consultor_origem
    ON public.dx_contratos (id_consultor_origem)
    WHERE id_consultor_origem IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dx_contratos_consultor_tecnico
    ON public.dx_contratos (id_consultor_tecnico)
    WHERE id_consultor_tecnico IS NOT NULL;

COMMENT ON COLUMN public.dx_contratos.id_consultor_origem IS
    'Consultor que originou a venda do contrato';

COMMENT ON COLUMN public.dx_contratos.id_consultor_tecnico IS
    'Consultor responsável pela atuação técnica no cliente';

-- ---------------------------------------------------------------------------
-- D) Fila de demandas do cliente para o consultor
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.dx_demandas_consultor (
    id              SERIAL PRIMARY KEY,
    id_clie         INTEGER NOT NULL REFERENCES public.ctdi_clie(id_clie) ON DELETE CASCADE,
    id_consultor    INTEGER NOT NULL REFERENCES public.dx_consultores(id) ON DELETE CASCADE,
    titulo          VARCHAR(200) NOT NULL,
    descricao       TEXT,
    status          VARCHAR(32) NOT NULL DEFAULT 'aberta',
    criado_em       TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    atualizado_em   TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT dx_demandas_consultor_status_chk
        CHECK (status IN ('aberta', 'em_andamento', 'resolvida'))
);

CREATE INDEX IF NOT EXISTS idx_dx_demandas_consultor_consultor
    ON public.dx_demandas_consultor (id_consultor, status);

CREATE INDEX IF NOT EXISTS idx_dx_demandas_consultor_clie
    ON public.dx_demandas_consultor (id_clie);

COMMENT ON TABLE public.dx_demandas_consultor IS
    'Solicitações de clientes atendidas pelo consultor no Portal do Parceiro';

COMMIT;
