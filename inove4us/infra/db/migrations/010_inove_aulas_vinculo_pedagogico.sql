-- Estruturação Pedagógica — Etapa 3/4: vínculo pedagógico opcional em aula/evento
-- Freemium: todas as colunas nullable / com default que preserva comportamento atual.
-- Não altera id_evento_pai (grafo) nem o enum `tipo` da agenda.
--
-- Aplicar:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/010_inove_aulas_vinculo_pedagogico.sql

BEGIN;

-- Dia a Dia
ALTER TABLE public.inove_aulas_simples
    ADD COLUMN IF NOT EXISTS disciplina_id BIGINT
        REFERENCES public.inove_disciplinas (id) ON DELETE SET NULL;

ALTER TABLE public.inove_aulas_simples
    ADD COLUMN IF NOT EXISTS tipo_registro VARCHAR(20) NOT NULL DEFAULT 'aula';

ALTER TABLE public.inove_aulas_simples
    ADD COLUMN IF NOT EXISTS origem VARCHAR(20) NOT NULL DEFAULT 'manual';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_inove_aulas_simples_tipo_registro'
    ) THEN
        ALTER TABLE public.inove_aulas_simples
            ADD CONSTRAINT chk_inove_aulas_simples_tipo_registro
            CHECK (tipo_registro IN ('aula', 'evento'));
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_inove_aulas_simples_origem'
    ) THEN
        ALTER TABLE public.inove_aulas_simples
            ADD CONSTRAINT chk_inove_aulas_simples_origem
            CHECK (origem IN ('manual', 'wizard_ia', 'importacao'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_inove_aulas_simples_disciplina
    ON public.inove_aulas_simples (disciplina_id)
    WHERE disciplina_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_inove_aulas_simples_origem
    ON public.inove_aulas_simples (id_clie, origem);

COMMENT ON COLUMN public.inove_aulas_simples.disciplina_id IS
  'Vínculo pedagógico opcional; curso/período/instituição via join.';
COMMENT ON COLUMN public.inove_aulas_simples.origem IS
  'manual | wizard_ia | importacao — metadado para Etapa 4 / filtros.';

-- Agenda (Desafio + espelho Dia a Dia). `tipo` já distingue o registro.
ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS disciplina_id BIGINT
        REFERENCES public.inove_disciplinas (id) ON DELETE SET NULL;

ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS origem VARCHAR(20) NOT NULL DEFAULT 'manual';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_inove_agenda_eventos_origem'
    ) THEN
        ALTER TABLE public.inove_agenda_eventos
            ADD CONSTRAINT chk_inove_agenda_eventos_origem
            CHECK (origem IN ('manual', 'wizard_ia', 'importacao'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_inove_agenda_eventos_disciplina
    ON public.inove_agenda_eventos (disciplina_id)
    WHERE disciplina_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_inove_agenda_eventos_origem
    ON public.inove_agenda_eventos (id_clie, origem);

COMMENT ON COLUMN public.inove_agenda_eventos.disciplina_id IS
  'Vínculo pedagógico opcional; não substitui coluna tipo existente.';
COMMENT ON COLUMN public.inove_agenda_eventos.origem IS
  'manual | wizard_ia | importacao.';

COMMIT;
