-- Assunto/tema da sequência pedagógica (compartilhado: importação + grafo)
-- Aplicar: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/012_inove_agenda_tema.sql

BEGIN;

ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS tema VARCHAR(200);

CREATE INDEX IF NOT EXISTS idx_inove_agenda_eventos_tema
    ON public.inove_agenda_eventos (id_clie, lower(tema))
    WHERE tema IS NOT NULL AND trim(tema) <> '';

COMMENT ON COLUMN public.inove_agenda_eventos.tema IS
  'Assunto/tema da sequência; linhas importadas com o mesmo assunto são encadeadas.';

COMMIT;
