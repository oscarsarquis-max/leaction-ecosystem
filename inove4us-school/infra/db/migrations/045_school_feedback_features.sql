-- Feedback de features experimentais (piloto). Texto livre do gestor.

BEGIN;

CREATE TABLE IF NOT EXISTS public.school_feedback_features (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id  UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    gestor_id       UUID,
    gestor_email    TEXT,
    gestor_nome     TEXT,
    feature_key     TEXT NOT NULL,
    texto           TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_school_feedback_features_inst_feat
    ON public.school_feedback_features (instituicao_id, feature_key, created_at DESC);

COMMENT ON TABLE public.school_feedback_features IS
  'Opinião livre do gestor sobre telas experimentais (piloto). Sem score.';

COMMIT;
