-- Funil de Vendas — oportunidades/leads (órfãos, distribuição e prospecção)
-- Estende o CRM Admin e o Portal do Consultor.

BEGIN;

-- ---------------------------------------------------------------------------
-- A) Código de convite único por consultor (tracking ?ref=)
-- ---------------------------------------------------------------------------
ALTER TABLE public.dx_consultores
    ADD COLUMN IF NOT EXISTS ref_code VARCHAR(32);

COMMENT ON COLUMN public.dx_consultores.ref_code IS
    'Hash público do consultor para links de convite (?ref=). Único quando preenchido.';

CREATE UNIQUE INDEX IF NOT EXISTS idx_dx_consultores_ref_code
    ON public.dx_consultores (ref_code)
    WHERE ref_code IS NOT NULL AND BTRIM(ref_code) <> '';

-- Backfill idempotente para consultores sem código
UPDATE public.dx_consultores
SET ref_code = LOWER(SUBSTRING(MD5(RANDOM()::TEXT || id::TEXT || CLOCK_TIMESTAMP()::TEXT) FROM 1 FOR 12))
WHERE ref_code IS NULL OR BTRIM(ref_code) = '';

-- ---------------------------------------------------------------------------
-- B) Tabela de oportunidades / leads do funil
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.dx_oportunidades (
    id                      SERIAL PRIMARY KEY,
    id_clie                 INTEGER REFERENCES public.ctdi_clie(id_clie) ON DELETE SET NULL,
    id_matu                 INTEGER REFERENCES public.ctdi_matu(id_matu) ON DELETE SET NULL,
    id_consultor_origem     INTEGER REFERENCES public.dx_consultores(id) ON DELETE SET NULL,
    status_funil            VARCHAR(32) NOT NULL DEFAULT 'novo_lead',
    origem                  VARCHAR(32) NOT NULL DEFAULT 'organico',
    nome                    VARCHAR(255),
    email                   VARCHAR(255),
    telefone                VARCHAR(64),
    empresa                 VARCHAR(255),
    invite_token            VARCHAR(64),
    motivo_perda            TEXT,
    criado_em               TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    atualizado_em           TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT dx_oportunidades_status_funil_chk
        CHECK (status_funil IN (
            'novo_lead',
            'distribuido',
            'em_negociacao',
            'convite_enviado',
            'ganho',
            'perdido'
        )),
    CONSTRAINT dx_oportunidades_origem_chk
        CHECK (origem IN (
            'organico',
            'admin_distribuicao',
            'consultor_reativo',
            'consultor_ativo',
            'convite'
        ))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dx_oportunidades_id_matu
    ON public.dx_oportunidades (id_matu)
    WHERE id_matu IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_dx_oportunidades_invite_token
    ON public.dx_oportunidades (invite_token)
    WHERE invite_token IS NOT NULL AND BTRIM(invite_token) <> '';

CREATE INDEX IF NOT EXISTS idx_dx_oportunidades_status
    ON public.dx_oportunidades (status_funil);

CREATE INDEX IF NOT EXISTS idx_dx_oportunidades_consultor
    ON public.dx_oportunidades (id_consultor_origem)
    WHERE id_consultor_origem IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dx_oportunidades_email
    ON public.dx_oportunidades (LOWER(TRIM(email)))
    WHERE email IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dx_oportunidades_id_clie
    ON public.dx_oportunidades (id_clie)
    WHERE id_clie IS NOT NULL;

COMMENT ON TABLE public.dx_oportunidades IS
    'Funil de vendas PanelDX — leads órfãos, distribuição admin e prospecção do consultor';

COMMENT ON COLUMN public.dx_oportunidades.status_funil IS
    'novo_lead | distribuido | em_negociacao | convite_enviado | ganho | perdido';

COMMENT ON COLUMN public.dx_oportunidades.id_consultor_origem IS
    'Consultor/agência responsável; NULL = lead órfão';

COMMENT ON COLUMN public.dx_oportunidades.invite_token IS
    'Token único do link de convite outbound do consultor';

-- ---------------------------------------------------------------------------
-- C) Backfill: clientes GENERAL com id_matu e sem consultor → novo_lead
-- ---------------------------------------------------------------------------
INSERT INTO public.dx_oportunidades (
    id_clie, id_matu, id_consultor_origem, status_funil, origem,
    nome, email, telefone, empresa
)
SELECT
    c.id_clie,
    m.id_matu,
    NULL,
    'novo_lead',
    'organico',
    c.nome_clie,
    c.mail_clie,
    c.fone_clie,
    c.empresa_clie
FROM public.ctdi_matu m
INNER JOIN public.ctdi_clie c ON c.id_clie = m.id_clie
WHERE COALESCE(UPPER(TRIM(c.init_role)), 'GENERAL') <> 'SOLO'
  AND NOT EXISTS (
      SELECT 1 FROM public.dx_oportunidades o WHERE o.id_matu = m.id_matu
  )
  AND NOT EXISTS (
      SELECT 1
      FROM public.dx_contratos ct
      WHERE ct.id_clie = c.id_clie
        AND ct.id_consultor_origem IS NOT NULL
        AND ct.status IN ('ativo', 'trial', 'inadimplente')
  )
ON CONFLICT DO NOTHING;

COMMIT;
