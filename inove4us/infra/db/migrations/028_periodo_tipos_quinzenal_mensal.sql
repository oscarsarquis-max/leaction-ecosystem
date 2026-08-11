-- Amplia tipos_periodo: quinzenal e mensal
--
-- Aplicar:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/028_periodo_tipos_quinzenal_mensal.sql

BEGIN;

ALTER TABLE public.inove_periodos_letivos
  DROP CONSTRAINT IF EXISTS inove_periodos_letivos_tipo_periodo_check;

ALTER TABLE public.inove_periodos_letivos
  ADD CONSTRAINT inove_periodos_letivos_tipo_periodo_check
  CHECK (tipo_periodo IN (
    'anual', 'semestral', 'trimestral', 'modular', 'quinzenal', 'mensal'
  ));

COMMIT;
