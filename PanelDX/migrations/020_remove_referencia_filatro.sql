-- Remove referência nominal; alinha com padrões de mercado
BEGIN;

COMMENT ON COLUMN public.leaf_dime.long_description IS
    'Conceituação detalhada baseada no LeAction F e em padrões de mercado';

COMMIT;
