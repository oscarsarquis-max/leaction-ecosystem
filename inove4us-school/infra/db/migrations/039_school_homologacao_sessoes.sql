-- Homologação multi-pessoa: homologadores, sessões nomeadas, eventos e vínculo no roteiro.

BEGIN;

CREATE TABLE IF NOT EXISTS public.school_homologadores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id  UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    gestor_id       UUID NOT NULL
        REFERENCES public.school_gestores (id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,
    nome            VARCHAR(200) NOT NULL,
    funcao          VARCHAR(80) NOT NULL DEFAULT 'homologador',
    escopo_dados    VARCHAR(20) NOT NULL DEFAULT 'proprio',
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_homologadores_inst_email
        UNIQUE (instituicao_id, email),
    CONSTRAINT uq_school_homologadores_gestor
        UNIQUE (gestor_id),
    CONSTRAINT chk_school_homologadores_escopo
        CHECK (escopo_dados IN ('proprio', 'todos'))
);

CREATE INDEX IF NOT EXISTS idx_school_homologadores_instituicao
    ON public.school_homologadores (instituicao_id, ativo);

COMMENT ON TABLE public.school_homologadores IS
  'Profissionais autorizados a conduzir homologação; escopo_dados=proprio isola sessões.';

CREATE TABLE IF NOT EXISTS public.school_homologacao_sessoes (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id          UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    homologador_id          UUID NOT NULL
        REFERENCES public.school_homologadores (id) ON DELETE RESTRICT,
    gestor_id               UUID NOT NULL
        REFERENCES public.school_gestores (id) ON DELETE CASCADE,
    codigo                  VARCHAR(80) NOT NULL,
    titulo                  VARCHAR(200),
    status                  VARCHAR(20) NOT NULL DEFAULT 'preparada',
    profissionais           JSONB NOT NULL DEFAULT '[]'::jsonb,
    impressoes              TEXT,
    resultado_geral         VARCHAR(40),
    versao_school           VARCHAR(40),
    versao_inove            VARCHAR(40),
    iniciada_em             TIMESTAMPTZ,
    encerrada_em            TIMESTAMPTZ,
    tempo_ativo_segundos    INTEGER NOT NULL DEFAULT 0,
    periodo_ativo_inicio    TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_homologacao_sessoes_codigo
        UNIQUE (instituicao_id, codigo),
    CONSTRAINT chk_school_homologacao_status
        CHECK (status IN (
            'preparada', 'em_andamento', 'pausada', 'concluida', 'cancelada'
        )),
    CONSTRAINT chk_school_homologacao_resultado
        CHECK (
            resultado_geral IS NULL
            OR resultado_geral IN ('passou', 'travou', 'nao_concluido')
        )
);

CREATE INDEX IF NOT EXISTS idx_school_homologacao_sessoes_inst_status
    ON public.school_homologacao_sessoes (instituicao_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_school_homologacao_sessoes_homologador
    ON public.school_homologacao_sessoes (homologador_id, updated_at DESC);

COMMENT ON TABLE public.school_homologacao_sessoes IS
  'Sessão nomeada de homologação (uma por homologador/data/código).';
COMMENT ON COLUMN public.school_homologacao_sessoes.profissionais IS
  'JSON array: [{nome, papel, email?}].';
COMMENT ON COLUMN public.school_homologacao_sessoes.tempo_ativo_segundos IS
  'Segundos acumulados em em_andamento (pausas não contam).';

CREATE TABLE IF NOT EXISTS public.school_homologacao_eventos (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sessao_id               UUID NOT NULL
        REFERENCES public.school_homologacao_sessoes (id) ON DELETE CASCADE,
    tipo                    VARCHAR(30) NOT NULL,
    texto                   TEXT,
    meta                    JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_por_gestor_id    UUID
        REFERENCES public.school_gestores (id) ON DELETE SET NULL,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_school_homologacao_evento_tipo
        CHECK (tipo IN (
            'inicio', 'pausa', 'retomada', 'interrupcao',
            'impressao', 'nota', 'fim', 'status'
        ))
);

CREATE INDEX IF NOT EXISTS idx_school_homologacao_eventos_sessao
    ON public.school_homologacao_eventos (sessao_id, criado_em);

COMMENT ON TABLE public.school_homologacao_eventos IS
  'Linha do tempo da sessão: início/pausa/interrupções/impressões/notas.';

ALTER TABLE public.school_roteiro_respostas
    ADD COLUMN IF NOT EXISTS sessao_id UUID
        REFERENCES public.school_homologacao_sessoes (id) ON DELETE CASCADE;

ALTER TABLE public.school_roteiro_respostas
    DROP CONSTRAINT IF EXISTS uq_school_roteiro_respostas_escopo;

CREATE UNIQUE INDEX IF NOT EXISTS uq_school_roteiro_respostas_com_sessao
    ON public.school_roteiro_respostas (sessao_id, passo_id)
    WHERE sessao_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_school_roteiro_respostas_sem_sessao
    ON public.school_roteiro_respostas (instituicao_id, gestor_id, tipo, passo_id)
    WHERE sessao_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_school_roteiro_respostas_sessao
    ON public.school_roteiro_respostas (sessao_id)
    WHERE sessao_id IS NOT NULL;

COMMENT ON COLUMN public.school_roteiro_respostas.sessao_id IS
  'Quando preenchido (homologação), isola respostas por sessão nomeada.';

COMMIT;
