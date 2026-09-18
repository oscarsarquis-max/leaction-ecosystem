-- 153 — Evento único (aula | planejamento | treinamento | civico | geral).
-- Não apaga Comunicados nem Planejamento: copia o histórico e passa a ser a
-- superfície canônica. Dual-write nas rotas novas mantém os pipelines 114/104.

ALTER TABLE public.school_comunicacoes_eventos
    DROP CONSTRAINT IF EXISTS school_comunicacoes_eventos_publico_alvo_check;
ALTER TABLE public.school_comunicacoes_eventos
    DROP CONSTRAINT IF EXISTS chk_school_comunicacoes_publico;

ALTER TABLE public.school_comunicacoes_eventos
    ADD CONSTRAINT school_comunicacoes_eventos_publico_alvo_check
    CHECK (publico_alvo IN (
        'toda_instituicao', 'unidade', 'turma', 'professores',
        'disciplina', 'administradores'
    ));

ALTER TABLE public.school_comunicacoes_eventos
    ADD COLUMN IF NOT EXISTS tipo_evento TEXT;

CREATE TABLE IF NOT EXISTS public.school_eventos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    tipo_evento TEXT NOT NULL
        CHECK (tipo_evento IN (
            'aula', 'planejamento', 'treinamento', 'civico', 'geral'
        )),
    titulo TEXT NOT NULL,
    descricao TEXT,
    data_hora_inicio TIMESTAMPTZ NOT NULL,
    data_hora_fim TIMESTAMPTZ,
    publico_alvo TEXT
        CHECK (publico_alvo IS NULL OR publico_alvo IN (
            'toda_instituicao', 'unidade', 'turma', 'professores',
            'disciplina', 'administradores'
        )),
    unidade_id UUID REFERENCES public.school_unidades (id) ON DELETE SET NULL,
    turma_id UUID REFERENCES public.school_turmas (id) ON DELETE SET NULL,
    disciplina_id UUID REFERENCES public.school_disciplinas (id) ON DELETE SET NULL,
    professor_vinculo_id UUID
        REFERENCES public.school_professores_vinculo (id) ON DELETE SET NULL,
    substituicao BOOLEAN NOT NULL DEFAULT FALSE,
    substitui_evento_id UUID
        REFERENCES public.school_eventos (id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'publicado',
    origem_comunicado_id UUID UNIQUE
        REFERENCES public.school_comunicacoes_eventos (id) ON DELETE SET NULL,
    origem_planejamento_id UUID UNIQUE
        REFERENCES public.school_planejamento_escolar (id) ON DELETE SET NULL,
    replicado_b2c BOOLEAN NOT NULL DEFAULT FALSE,
    replicado_b2c_em TIMESTAMPTZ,
    criado_por_gestor_id UUID
        REFERENCES public.school_gestores (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT school_eventos_aula_alocacao CHECK (
        tipo_evento <> 'aula'
        OR (
            professor_vinculo_id IS NOT NULL
            AND turma_id IS NOT NULL
            AND disciplina_id IS NOT NULL
        )
    ),
    CONSTRAINT school_eventos_broadcast_publico CHECK (
        tipo_evento = 'aula' OR publico_alvo IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS idx_school_eventos_inst_inicio
    ON public.school_eventos (instituicao_id, data_hora_inicio);

INSERT INTO public.school_eventos (
    instituicao_id, tipo_evento, titulo, descricao,
    data_hora_inicio, data_hora_fim, publico_alvo,
    unidade_id, turma_id, disciplina_id, status,
    origem_comunicado_id, replicado_b2c, replicado_b2c_em,
    criado_por_gestor_id, created_at, updated_at
)
SELECT
    e.instituicao_id,
    CASE e.tipo
        WHEN 'reuniao_pedagogica' THEN 'planejamento'
        ELSE 'geral'
    END,
    e.titulo,
    e.descricao,
    e.data_hora_inicio,
    e.data_hora_fim,
    e.publico_alvo,
    e.unidade_id,
    e.turma_id,
    e.disciplina_id,
    e.status,
    e.id,
    e.replicado_b2c,
    e.replicado_b2c_em,
    e.criado_por_gestor_id,
    e.created_at,
    e.updated_at
FROM public.school_comunicacoes_eventos e
WHERE NOT EXISTS (
    SELECT 1 FROM public.school_eventos x WHERE x.origem_comunicado_id = e.id
);

INSERT INTO public.school_eventos (
    instituicao_id, tipo_evento, titulo, descricao,
    data_hora_inicio, data_hora_fim, publico_alvo,
    turma_id, disciplina_id, professor_vinculo_id,
    substituicao, status, origem_planejamento_id, created_at, updated_at
)
SELECT
    p.instituicao_id,
    'aula',
    p.titulo,
    p.observacoes,
    (p.data::timestamp + COALESCE(p.hora_inicio, TIME '12:00'))
        AT TIME ZONE 'America/Sao_Paulo',
    (p.data::timestamp + COALESCE(p.hora_fim, TIME '12:50'))
        AT TIME ZONE 'America/Sao_Paulo',
    NULL,
    p.turma_id,
    p.disciplina_id,
    p.professor_vinculo_id,
    COALESCE(p.substituicao, FALSE),
    CASE p.status_push
        WHEN 'enviado' THEN 'enviado'
        WHEN 'erro' THEN 'erro'
        ELSE 'rascunho'
    END,
    p.id,
    p.created_at,
    p.updated_at
FROM public.school_planejamento_escolar p
WHERE NOT EXISTS (
    SELECT 1 FROM public.school_eventos x WHERE x.origem_planejamento_id = p.id
);

COMMENT ON TABLE public.school_eventos IS
  '153 — superfície única. tipo=aula usa pipeline de Planejamento (104); demais usam Comunicados (114).';
