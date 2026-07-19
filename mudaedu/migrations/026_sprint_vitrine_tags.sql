-- Tags da vitrine contextual (ActionHub) — persistidas na criação da Sprint (IA).
-- Match em runtime é SQL puro (overlap), sem chamadas de IA.

BEGIN;

ALTER TABLE public.ctdi_sprn
    ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}';

COMMENT ON COLUMN public.ctdi_sprn.tags IS
    'Tags/categorias da vitrine ActionHub (ex: formacao, equipamentos, software). Gravadas na criação pela IA; match relacional sem IA em tempo real.';

CREATE INDEX IF NOT EXISTS idx_ctdi_sprn_tags_gin
    ON public.ctdi_sprn USING GIN (tags);

COMMIT;
