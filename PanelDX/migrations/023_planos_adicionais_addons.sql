-- Add-ons de licenças (pacotes extras de usuários) — vinculados ao contrato base
-- Nota: 020 já existe (remove_referencia_filatro) — esta migration usa 023.

BEGIN;

ALTER TABLE public.dx_planos
    ADD COLUMN IF NOT EXISTS tipo_plano VARCHAR(16) NOT NULL DEFAULT 'base';

ALTER TABLE public.dx_planos
    DROP CONSTRAINT IF EXISTS dx_planos_tipo_plano_chk;

ALTER TABLE public.dx_planos
    ADD CONSTRAINT dx_planos_tipo_plano_chk
        CHECK (tipo_plano IN ('base', 'addon'));

COMMENT ON COLUMN public.dx_planos.tipo_plano IS
    'base = plano comercial principal; addon = pacote adicional de licenças';

CREATE TABLE IF NOT EXISTS public.dx_contratos_addons (
    id              SERIAL PRIMARY KEY,
    id_contrato     INTEGER NOT NULL REFERENCES public.dx_contratos(id) ON DELETE CASCADE,
    id_plano_addon  INTEGER NOT NULL REFERENCES public.dx_planos(id) ON DELETE RESTRICT,
    quantidade      INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(16) NOT NULL DEFAULT 'ativo',
    hub_order_id    VARCHAR(64),
    criado_em       TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    atualizado_em   TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT dx_contratos_addons_status_chk
        CHECK (status IN ('ativo', 'cancelado')),
    CONSTRAINT dx_contratos_addons_quantidade_chk
        CHECK (quantidade >= 1)
);

CREATE INDEX IF NOT EXISTS idx_dx_contratos_addons_contrato
    ON public.dx_contratos_addons (id_contrato);

CREATE INDEX IF NOT EXISTS idx_dx_contratos_addons_status
    ON public.dx_contratos_addons (status);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dx_contratos_addons_hub_order
    ON public.dx_contratos_addons (hub_order_id)
    WHERE hub_order_id IS NOT NULL AND hub_order_id <> '';

COMMENT ON TABLE public.dx_contratos_addons IS
    'Pacotes add-on de usuários vinculados ao contrato principal do cliente';

INSERT INTO public.dx_planos (nome, valor_mensal, periodicidade, max_usuarios, tipo_plano, ativo, descricao_beneficios)
SELECT
    'Pacote Extra: 5 Usuários',
    199.00::NUMERIC,
    'Mensal',
    5,
    'addon',
    TRUE,
    '["+5 usuários ativos no seu plano","Sem troca de plano base","Ativação imediata após pagamento"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM public.dx_planos p
    WHERE LOWER(TRIM(p.nome)) = LOWER('Pacote Extra: 5 Usuários')
      AND p.tipo_plano = 'addon'
);

COMMIT;
