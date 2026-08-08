-- 031: Planejamento Escolar (Secretaria → push B2C esqueleto aula/evento)

CREATE TABLE IF NOT EXISTS public.school_planejamento_escolar (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id        UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    turma_id              UUID NOT NULL
        REFERENCES public.school_turmas (id) ON DELETE RESTRICT,
    disciplina_id         UUID NOT NULL
        REFERENCES public.school_disciplinas (id) ON DELETE RESTRICT,
    professor_vinculo_id  UUID NOT NULL
        REFERENCES public.school_professores_vinculo (id) ON DELETE RESTRICT,
    titulo                TEXT NOT NULL,
    tipo                  TEXT NOT NULL DEFAULT 'aula'
        CHECK (tipo IN ('aula', 'evento')),
    data                  DATE NOT NULL,
    hora_inicio           TIME,
    hora_fim              TIME,
    observacoes           TEXT,
    item_pai_id           UUID
        REFERENCES public.school_planejamento_escolar (id) ON DELETE SET NULL,
    status_push           TEXT NOT NULL DEFAULT 'rascunho'
        CHECK (status_push IN ('rascunho', 'enviado', 'erro')),
    enviado_em            TIMESTAMPTZ,
    resposta_b2c_json     JSONB,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_school_planejamento_instituicao
    ON public.school_planejamento_escolar (instituicao_id, data DESC);

CREATE INDEX IF NOT EXISTS idx_school_planejamento_turma
    ON public.school_planejamento_escolar (turma_id, status_push);

CREATE INDEX IF NOT EXISTS idx_school_planejamento_status
    ON public.school_planejamento_escolar (instituicao_id, status_push);

COMMENT ON TABLE public.school_planejamento_escolar IS
  'Planejamento simplificado da Secretaria; push cria esqueleto no B2C (agenda do professor).';
COMMENT ON COLUMN public.school_planejamento_escolar.professor_vinculo_id IS
  'Resolvido via Alocação Docente (turma + disciplina) na criação — não escolhido à mão.';
COMMENT ON COLUMN public.school_planejamento_escolar.status_push IS
  'rascunho | enviado | erro — itens enviados ficam como registro histórico.';
COMMENT ON COLUMN public.school_planejamento_escolar.item_pai_id IS
  'Self-ref; no push vira vinculo_pai_id_externo (sequências tipo desafio).';
