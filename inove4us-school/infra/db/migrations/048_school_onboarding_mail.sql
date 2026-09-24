-- 146 — preferência de resumo diário + log idempotente de e-mails de onboarding.

BEGIN;

ALTER TABLE public.school_gestores
    ADD COLUMN IF NOT EXISTS recebe_resumo_diario BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN public.school_gestores.recebe_resumo_diario IS
  'Gestor recebe o resumo diário de acompanhamento (e-mail). Default ligado.';

CREATE TABLE IF NOT EXISTS public.school_onboarding_mail_log (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind             VARCHAR(32) NOT NULL,
    recipient_email  TEXT NOT NULL,
    instituicao_id   UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    ref_id           UUID,
    sent_on          DATE NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_school_onboarding_mail_kind
        CHECK (kind IN ('teacher_reminder', 'gestor_digest')),
    CONSTRAINT uq_school_onboarding_mail_day
        UNIQUE (kind, recipient_email, instituicao_id, sent_on)
);

CREATE INDEX IF NOT EXISTS idx_school_onboarding_mail_day
    ON public.school_onboarding_mail_log (sent_on, kind);

COMMENT ON TABLE public.school_onboarding_mail_log IS
  'Idempotência: no máximo 1 e-mail por pessoa/instituição/tipo/dia (America/Sao_Paulo).';

COMMIT;
