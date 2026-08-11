-- Dia a Dia: tópico da ementa selecionado no plano da aula
--
-- Aplicar:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/030_aula_simples_ementa_topico.sql

BEGIN;

ALTER TABLE public.inove_aulas_simples
    ADD COLUMN IF NOT EXISTS ementa_topico VARCHAR(255);

COMMENT ON COLUMN public.inove_aulas_simples.ementa_topico IS
  'Item/linha da ementa da disciplina escolhido para esta aula (texto).';

COMMIT;
