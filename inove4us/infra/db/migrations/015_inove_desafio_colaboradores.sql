-- Fase 3: colaboração pontual por desafio (convite por e-mail).
-- Aplicar: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/015_inove_desafio_colaboradores.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.inove_desafio_colaboradores (
    id                  BIGSERIAL PRIMARY KEY,
    desafio_id          UUID NOT NULL
        REFERENCES public.inove_desafios (id) ON DELETE CASCADE,
    email_convidado     VARCHAR(320) NOT NULL,
    id_clie_convidado   INTEGER
        REFERENCES public.ctdi_clie (id_clie) ON DELETE SET NULL,
    papel_ou_parte      VARCHAR(200),
    token_convite       VARCHAR(64) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'aceito', 'recusado')),
    convidado_por       INTEGER NOT NULL
        REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
    criado_em           TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    aceito_em           TIMESTAMP WITHOUT TIME ZONE
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_desafio_colab_token
    ON public.inove_desafio_colaboradores (token_convite);

CREATE INDEX IF NOT EXISTS idx_inove_desafio_colab_desafio
    ON public.inove_desafio_colaboradores (desafio_id, status);

CREATE INDEX IF NOT EXISTS idx_inove_desafio_colab_email
    ON public.inove_desafio_colaboradores (desafio_id, lower(trim(email_convidado)));

COMMENT ON TABLE public.inove_desafio_colaboradores IS
  'Convite pontual por desafio — não cria rede persistente entre professores.';

-- Responsável explícito da execução (aula). Distinto do dono do desafio (inove_desafios.id_clie).
ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS id_clie_responsavel INTEGER
        REFERENCES public.ctdi_clie (id_clie) ON DELETE SET NULL;

UPDATE public.inove_agenda_eventos
   SET id_clie_responsavel = id_clie
 WHERE id_clie_responsavel IS NULL;

CREATE INDEX IF NOT EXISTS idx_inove_agenda_eventos_responsavel
    ON public.inove_agenda_eventos (id_clie_responsavel)
    WHERE id_clie_responsavel IS NOT NULL;

COMMENT ON COLUMN public.inove_agenda_eventos.id_clie_responsavel IS
  'Professor responsável pela execução desta aula; pode diferir do dono do desafio.';

COMMIT;
