-- PanelDX — Gamificação OKR + catálogo fixo de direcionadores estratégicos
-- Idempotente.

ALTER TABLE public.ctdi_okr_direcionadores
    ADD COLUMN IF NOT EXISTS slug_catalogo VARCHAR(80);

ALTER TABLE public.ctdi_okr_direcionadores
    ADD COLUMN IF NOT EXISTS meta_financeira VARCHAR(32);

ALTER TABLE public.ctdi_okr_direcionadores
    ADD COLUMN IF NOT EXISTS icone VARCHAR(16);

CREATE TABLE IF NOT EXISTS public.ctdi_okr_comentarios (
    id_comentario SERIAL PRIMARY KEY,
    id_clie       INTEGER NOT NULL,
    entidade_tipo VARCHAR(32) NOT NULL,
    entidade_id   INTEGER NOT NULL,
    autor_nome    VARCHAR(120),
    texto         TEXT NOT NULL,
    criado_em     TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_okr_comentarios_entidade
    ON public.ctdi_okr_comentarios (id_clie, entidade_tipo, entidade_id);

COMMENT ON TABLE public.ctdi_okr_comentarios IS
    'Comentários do gestor na árvore estratégica OKR (direcionador, objetivo, kr).';
