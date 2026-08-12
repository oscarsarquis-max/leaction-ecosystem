-- inove4us School — Unidade hub: dados institucionais + equipe gestora
-- Não altera shape do GET /api/secretaria/unidades (lista).
-- Não toca sync B2C.

BEGIN;

ALTER TABLE public.school_unidades
    ADD COLUMN IF NOT EXISTS logradouro           TEXT,
    ADD COLUMN IF NOT EXISTS numero               TEXT,
    ADD COLUMN IF NOT EXISTS bairro               TEXT,
    ADD COLUMN IF NOT EXISTS cep                  TEXT,
    ADD COLUMN IF NOT EXISTS telefone             TEXT,
    ADD COLUMN IF NOT EXISTS email_institucional  TEXT;

COMMENT ON COLUMN public.school_unidades.endereco IS
  'Legado (texto livre). Preferir logradouro/numero/bairro/cep; manter por compatibilidade.';
COMMENT ON COLUMN public.school_unidades.logradouro IS
  'Logradouro estruturado do campus.';
COMMENT ON COLUMN public.school_unidades.email_institucional IS
  'E-mail institucional da unidade (não confundir com login de gestor).';

-- Backfill suave: só preenche logradouro se estruturado ainda vazio
UPDATE public.school_unidades
SET logradouro = NULLIF(trim(endereco), '')
WHERE (logradouro IS NULL OR trim(logradouro) = '')
  AND endereco IS NOT NULL
  AND trim(endereco) <> '';

CREATE TABLE IF NOT EXISTS public.school_unidade_equipe (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unidade_id      UUID NOT NULL
        REFERENCES public.school_unidades (id) ON DELETE CASCADE,
    papel           TEXT NOT NULL,
    gestor_id       UUID
        REFERENCES public.school_gestores (id) ON DELETE SET NULL,
    -- Contato: obrigatório na prática quando gestor_id IS NULL (avulso)
    nome            TEXT,
    email           TEXT,
    telefone        TEXT,
    -- Só faz sentido para coordenador (área/curso de coordenação)
    area_coordenacao TEXT,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_school_unidade_equipe_papel CHECK (
        papel = ANY (ARRAY[
            'gestor_principal',
            'gestor_academico',
            'coordenador'
        ])
    ),
    CONSTRAINT chk_school_unidade_equipe_identidade CHECK (
        gestor_id IS NOT NULL
        OR (nome IS NOT NULL AND length(trim(nome)) > 0)
    )
);

COMMENT ON TABLE public.school_unidade_equipe IS
  'Equipe gestora por unidade. Gestor com login → gestor_id; coordenador avulso → nome/email/telefone.';

-- No máx. 1 principal e 1 acadêmico ativos por unidade
CREATE UNIQUE INDEX IF NOT EXISTS uq_school_unidade_equipe_um_principal
    ON public.school_unidade_equipe (unidade_id)
    WHERE ativo = TRUE AND papel = 'gestor_principal';

CREATE UNIQUE INDEX IF NOT EXISTS uq_school_unidade_equipe_um_academico
    ON public.school_unidade_equipe (unidade_id)
    WHERE ativo = TRUE AND papel = 'gestor_academico';

-- Coordenadores N; evita duplicar o mesmo gestor_id ativo no mesmo papel
CREATE UNIQUE INDEX IF NOT EXISTS uq_school_unidade_equipe_gestor_papel
    ON public.school_unidade_equipe (unidade_id, papel, gestor_id)
    WHERE ativo = TRUE AND gestor_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_school_unidade_equipe_unidade
    ON public.school_unidade_equipe (unidade_id)
    WHERE ativo = TRUE;

COMMIT;
