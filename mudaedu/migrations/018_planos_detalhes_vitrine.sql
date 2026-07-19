-- Vitrine comercial — periodicidade e benefícios dos planos (ActionHub)
BEGIN;

ALTER TABLE public.dx_planos
    ADD COLUMN IF NOT EXISTS periodicidade VARCHAR(32) NOT NULL DEFAULT 'Mensal';

ALTER TABLE public.dx_planos
    ADD COLUMN IF NOT EXISTS descricao_beneficios JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE public.dx_planos DROP CONSTRAINT IF EXISTS dx_planos_periodicidade_chk;

ALTER TABLE public.dx_planos
    ADD CONSTRAINT dx_planos_periodicidade_chk
        CHECK (periodicidade IN ('Mensal', 'Semestral', 'Anual'));

COMMENT ON COLUMN public.dx_planos.periodicidade IS
    'Prazo de vigência exibido na vitrine (Mensal, Semestral, Anual)';

COMMENT ON COLUMN public.dx_planos.descricao_beneficios IS
    'Lista JSON de benefícios para pricing cards no ActionHub';

-- Benefícios canônicos nos planos seed (idempotente)
UPDATE public.dx_planos SET
    periodicidade = 'Mensal',
    descricao_beneficios = '["Diagnóstico de maturidade digital","Gestão de squads e OKRs","Suporte por e-mail"]'::jsonb
WHERE LOWER(TRIM(nome)) = LOWER('Conta Básica');

UPDATE public.dx_planos SET
    periodicidade = 'Mensal',
    descricao_beneficios = '["Tudo da Conta Básica","Inteligência de negócio avançada","Múltiplas squads ativas","Consultoria mensal"]'::jsonb
WHERE LOWER(TRIM(nome)) = LOWER('Conta Avançada');

UPDATE public.dx_planos SET
    periodicidade = 'Anual',
    descricao_beneficios = '["Tudo da Conta Avançada","Cockpit executivo completo","eSIM e telemetria integrada","CSM dedicado","Renovação prioritária"]'::jsonb
WHERE LOWER(TRIM(nome)) = LOWER('Conta Premium');

COMMIT;
