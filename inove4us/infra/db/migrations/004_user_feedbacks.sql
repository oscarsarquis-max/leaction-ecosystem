-- Programa de Co-criação — ideias, bugs e melhorias dos professores.
CREATE TABLE IF NOT EXISTS public.inove_user_feedbacks (
    id           SERIAL PRIMARY KEY,
    user_email   VARCHAR(254) NOT NULL,
    id_clie      INTEGER REFERENCES public.ctdi_clie (id_clie) ON DELETE SET NULL,
    tipo         VARCHAR(32) NOT NULL,
    mensagem     TEXT NOT NULL,
    status       VARCHAR(32) NOT NULL DEFAULT 'pendente',
    created_at   TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_inove_user_feedbacks_tipo
        CHECK (tipo IN ('ideia', 'bug', 'melhoria')),
    CONSTRAINT chk_inove_user_feedbacks_status
        CHECK (status IN ('pendente', 'lido', 'recompensado', 'arquivado'))
);

CREATE INDEX IF NOT EXISTS idx_inove_user_feedbacks_email_created
    ON public.inove_user_feedbacks (lower(user_email), created_at DESC);

CREATE INDEX IF NOT EXISTS idx_inove_user_feedbacks_status
    ON public.inove_user_feedbacks (status, created_at DESC);
