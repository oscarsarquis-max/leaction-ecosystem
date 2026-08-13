-- Auditoria 0.1 (cnpj nullable):
-- Referências a school_instituicoes.cnpj no School:
--   001 schema UNIQUE NOT NULL
--   005 seed ON CONFLICT (cnpj) — já aplicada, não reexecuta
--   005.down DELETE por cnpj
--   infra/scripts/upsert-sysadmin.py ON CONFLICT (cnpj)
-- Nenhuma query de API/UI usa cnpj como chave de busca.
-- upsert-sysadmin.py passa a ON CONFLICT (cnpj) WHERE cnpj IS NOT NULL
-- (índice único parcial).

BEGIN;

ALTER TABLE public.school_instituicoes
    DROP CONSTRAINT IF EXISTS uq_school_instituicoes_cnpj;
ALTER TABLE public.school_instituicoes
    DROP CONSTRAINT IF EXISTS school_instituicoes_cnpj_key;

ALTER TABLE public.school_instituicoes
    ALTER COLUMN cnpj DROP NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_school_instituicoes_cnpj_not_null
    ON public.school_instituicoes (cnpj)
    WHERE cnpj IS NOT NULL;

ALTER TABLE public.school_instituicoes
    ADD COLUMN IF NOT EXISTS documento_responsavel_pagamento VARCHAR(32);

ALTER TABLE public.school_instituicoes
    ADD COLUMN IF NOT EXISTS documento_responsavel_tipo VARCHAR(4);

ALTER TABLE public.school_instituicoes
    DROP CONSTRAINT IF EXISTS chk_school_instituicoes_doc_tipo;

ALTER TABLE public.school_instituicoes
    ADD CONSTRAINT chk_school_instituicoes_doc_tipo
        CHECK (
            documento_responsavel_tipo IS NULL
            OR documento_responsavel_tipo IN ('cnpj', 'cpf')
        );

COMMENT ON COLUMN public.school_instituicoes.cnpj IS
  'CNPJ oficial da instituição. Nullable até a escola completar o cadastro.';
COMMENT ON COLUMN public.school_instituicoes.documento_responsavel_pagamento IS
  'Documento de quem pagou no checkout do Hub (dígitos).';
COMMENT ON COLUMN public.school_instituicoes.documento_responsavel_tipo IS
  'cnpj | cpf — tipo do documento do pagador, não necessariamente o CNPJ da escola.';

CREATE TABLE IF NOT EXISTS public.school_hub_eventos_processados (
    order_id        TEXT PRIMARY KEY,
    instituicao_id  UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_school_hub_eventos_instituicao
    ON public.school_hub_eventos_processados (instituicao_id);

COMMENT ON TABLE public.school_hub_eventos_processados IS
  'Idempotência do webhook Hub: o mesmo order_id não credita licença nem provisiona duas vezes.';

CREATE TABLE IF NOT EXISTS public.school_provisionamento_email (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id  UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    order_id        TEXT,
    gestor_email    TEXT,
    status          VARCHAR(16) NOT NULL,
    erro            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_school_provisionamento_email_status
        CHECK (status IN ('enviado', 'falhou', 'pendente'))
);

CREATE INDEX IF NOT EXISTS idx_school_provisionamento_email_inst
    ON public.school_provisionamento_email (instituicao_id, created_at DESC);

COMMENT ON TABLE public.school_provisionamento_email IS
  'Fail-soft do e-mail de credencial self-serve. Sem senha em claro. Reenvio manual via log/registro.';

COMMIT;
