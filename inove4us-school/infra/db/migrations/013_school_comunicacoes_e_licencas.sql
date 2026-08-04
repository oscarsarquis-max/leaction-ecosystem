-- inove4us School — Etapa 12: comunicações/eventos + licenças.
-- Numeração: 013 (012 = zonas RBAC).
--
-- 1) school_comunicacoes_eventos — cadastro institucional (push B2C = Etapa 14).
-- 2) school_instituicoes — licencas_contratadas + link_plano_actionhub (nullable).
--    link_plano_actionhub: fallback até o Hub definir se a URL é fixa por escola
--    ou montável por padrão (ex.: ?instituicao_id=); não trava o resto do schema.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) Comunicações e eventos
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_comunicacoes_eventos (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id          UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    unidade_id              UUID
        REFERENCES public.school_unidades (id) ON DELETE SET NULL,
    titulo                  TEXT NOT NULL,
    descricao               TEXT,
    tipo                    TEXT NOT NULL,
    data_hora_inicio        TIMESTAMPTZ NOT NULL,
    data_hora_fim           TIMESTAMPTZ,
    publico_alvo            TEXT NOT NULL,
    turma_id                UUID
        REFERENCES public.school_turmas (id) ON DELETE SET NULL,
    status                  TEXT NOT NULL DEFAULT 'agendado',
    replicado_b2c           BOOLEAN NOT NULL DEFAULT FALSE,
    replicado_b2c_em        TIMESTAMPTZ,
    criado_por_gestor_id    UUID
        REFERENCES public.school_gestores (id) ON DELETE SET NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_school_comunicacoes_tipo
        CHECK (tipo IN ('reuniao_pedagogica', 'evento_escolar')),
    CONSTRAINT chk_school_comunicacoes_publico
        CHECK (publico_alvo IN (
            'toda_instituicao',
            'unidade',
            'turma',
            'professores'
        )),
    CONSTRAINT chk_school_comunicacoes_status
        CHECK (status IN ('agendado', 'publicado', 'cancelado'))
);

CREATE INDEX IF NOT EXISTS idx_school_comunicacoes_instituicao
    ON public.school_comunicacoes_eventos (instituicao_id, data_hora_inicio DESC);

CREATE INDEX IF NOT EXISTS idx_school_comunicacoes_unidade
    ON public.school_comunicacoes_eventos (unidade_id)
    WHERE unidade_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_school_comunicacoes_status
    ON public.school_comunicacoes_eventos (instituicao_id, status);

CREATE INDEX IF NOT EXISTS idx_school_comunicacoes_pendente_b2c
    ON public.school_comunicacoes_eventos (instituicao_id)
    WHERE replicado_b2c = FALSE AND status = 'publicado';

COMMENT ON TABLE public.school_comunicacoes_eventos IS
  'Reuniões pedagógicas e eventos escolares. Push real pro mural/agenda B2C = Etapa 14.';
COMMENT ON COLUMN public.school_comunicacoes_eventos.unidade_id IS
  'NULL = instituição inteira; preenchido = só aquela unidade (mesmo padrão do calendário letivo).';
COMMENT ON COLUMN public.school_comunicacoes_eventos.turma_id IS
  'Usado quando publico_alvo = turma.';
COMMENT ON COLUMN public.school_comunicacoes_eventos.replicado_b2c IS
  'Idempotência do push B2C — true após envio bem-sucedido (Etapa 14).';

-- ---------------------------------------------------------------------------
-- 2) Licenças na instituição (contadores Equipe = Etapa 15)
-- ---------------------------------------------------------------------------
ALTER TABLE public.school_instituicoes
    ADD COLUMN IF NOT EXISTS licencas_contratadas INTEGER,
    ADD COLUMN IF NOT EXISTS link_plano_actionhub TEXT;

COMMENT ON COLUMN public.school_instituicoes.licencas_contratadas IS
  'Qtd. de licenças contratadas (manual até existir sync real com Action Hub).';
COMMENT ON COLUMN public.school_instituicoes.link_plano_actionhub IS
  'URL da página de planos do Hub pra esta escola (nullable; pode ser substituída por padrão montável).';

COMMIT;
