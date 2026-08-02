-- Adaptação Inclusiva (PEI): tabela de cards/subcards do Kanban.
-- O board runtime continua em kanban_state JSONB; esta tabela persiste
-- subcards PEI com parent_card_id + perfil_inclusao (e pode espelhar cards).
-- Aplicar: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/020_inove_kanban_pei_subcards.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.inove_kanban_cards (
    id                 BIGSERIAL PRIMARY KEY,
    id_clie            INTEGER NOT NULL
        REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
    id_evento          INTEGER
        REFERENCES public.inove_agenda_eventos (id_evento) ON DELETE CASCADE,
    desafio_id         UUID,
    card_key           VARCHAR(120) NOT NULL,
    parent_card_id     BIGINT
        REFERENCES public.inove_kanban_cards (id) ON DELETE CASCADE,
    parent_card_key    VARCHAR(120),
    titulo             TEXT NOT NULL DEFAULT '',
    descricao          TEXT NOT NULL DEFAULT '',
    coluna             VARCHAR(32) NOT NULL DEFAULT 'para_fazer',
    perfil_inclusao    VARCHAR(64),
    meta_json          JSONB,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_inove_kanban_cards_coluna
        CHECK (coluna IN ('para_fazer', 'fazendo', 'pronto')),
    CONSTRAINT chk_inove_kanban_cards_pei_parent
        CHECK (
            perfil_inclusao IS NULL
            OR parent_card_key IS NOT NULL
            OR parent_card_id IS NOT NULL
        )
);

-- Um card_key por evento (quando vinculado a uma aula).
CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_kanban_cards_evento_key
    ON public.inove_kanban_cards (id_evento, card_key)
    WHERE id_evento IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_inove_kanban_cards_clie
    ON public.inove_kanban_cards (id_clie, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_inove_kanban_cards_parent
    ON public.inove_kanban_cards (parent_card_id)
    WHERE parent_card_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_inove_kanban_cards_parent_key
    ON public.inove_kanban_cards (id_evento, parent_card_key)
    WHERE parent_card_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_inove_kanban_cards_perfil
    ON public.inove_kanban_cards (perfil_inclusao)
    WHERE perfil_inclusao IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_inove_kanban_cards_desafio
    ON public.inove_kanban_cards (desafio_id)
    WHERE desafio_id IS NOT NULL;

COMMENT ON TABLE public.inove_kanban_cards IS
  'Cards/subcards do Kanban (PEI). parent_card_id/parent_card_key ligam adaptação ao card pai; perfil_inclusao guarda TEA/TDAH/Dislexia etc.';
COMMENT ON COLUMN public.inove_kanban_cards.parent_card_id IS
  'FK para o card pai nesta tabela (nullable se o pai ainda só existe no JSONB).';
COMMENT ON COLUMN public.inove_kanban_cards.parent_card_key IS
  'card_key/id do card pai no kanban_state JSONB.';
COMMENT ON COLUMN public.inove_kanban_cards.perfil_inclusao IS
  'Perfil neurodivergente da adaptação (ex.: TEA, TDAH, Dislexia). NULL = card normal.';
COMMENT ON COLUMN public.inove_kanban_cards.card_key IS
  'Identificador estável usado em kanban_state.tarefas[].id.';

COMMIT;
