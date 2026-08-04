-- inove4us School (B2B) — Pilar 3: Governança Pedagógica.
-- Pré-requisitos:
--   001 (school_instituicoes, school_professores_vinculo)
--   002 (school_turmas, school_alunos)
--   003 (school_professor_turma) — não alterada nesta etapa
-- Prefixo obrigatório: school_*
-- Aplicar: via bootstrap-db.ps1
--
-- Decisão: school_editor_pedagogico (001) fica superada — 1 metodologia/instituição.
-- Como está vazia (0 linhas), esta migration a REMOVE. O .down.sql a recria.
-- Seed do catálogo: só PBL, EduScrum, Mapas Mentais (placeholders). Demais ~21 = pendência de conteúdo.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1) Catálogo global de metodologias (sem FK de instituição)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_metodologias_catalogo (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome              TEXT NOT NULL,
    descricao         TEXT,
    passos_execucao   JSONB NOT NULL,
    ativo             BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_metodologias_catalogo_nome UNIQUE (nome)
);

COMMENT ON TABLE public.school_metodologias_catalogo IS
  'Catálogo global de metodologias (padrão ouro). Seed parcial: 3 confirmadas; as ~21 restantes são pendência de conteúdo.';
COMMENT ON COLUMN public.school_metodologias_catalogo.passos_execucao IS
  'Lista estruturada de passos do padrão de excelência (JSONB).';

-- Seed idempotente: apenas as 3 metodologias confirmadas na síntese do produto.
INSERT INTO public.school_metodologias_catalogo (nome, descricao, passos_execucao)
VALUES
    ('PBL', 'Aprendizagem Baseada em Projetos / Problemas', '["a detalhar"]'::jsonb),
    ('EduScrum', 'EduScrum — gestão ágil da aprendizagem', '["a detalhar"]'::jsonb),
    ('Mapas Mentais', 'Mapas Mentais como ferramenta de organização e síntese', '["a detalhar"]'::jsonb)
ON CONFLICT (nome) DO UPDATE SET
    descricao = EXCLUDED.descricao,
    passos_execucao = EXCLUDED.passos_execucao,
    updated_at = CURRENT_TIMESTAMP;

-- ---------------------------------------------------------------------------
-- 2) Override de metodologia por instituição
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_metodologia_config (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id           UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    metodologia_catalogo_id  UUID NOT NULL
        REFERENCES public.school_metodologias_catalogo (id) ON DELETE CASCADE,
    diretriz_customizada     TEXT,
    is_active                BOOLEAN NOT NULL DEFAULT TRUE,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_metodologia_config_inst_cat
        UNIQUE (instituicao_id, metodologia_catalogo_id)
);

CREATE INDEX IF NOT EXISTS idx_school_metodologia_config_instituicao
    ON public.school_metodologia_config (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_metodologia_config_catalogo
    ON public.school_metodologia_config (metodologia_catalogo_id);

COMMENT ON TABLE public.school_metodologia_config IS
  'Override por instituição × metodologia do catálogo. NULL em diretriz_customizada = usa o padrão do catálogo.';
COMMENT ON COLUMN public.school_metodologia_config.diretriz_customizada IS
  'NULL = usa o padrão (passos_execucao) do catálogo global.';

-- ---------------------------------------------------------------------------
-- 3) Diretriz PEI institucional por tipo de neurodivergência
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_pei_diretriz_base (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id          UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    tipo_neurodivergencia   TEXT NOT NULL,
    diretriz                TEXT NOT NULL,
    ativo                   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_pei_diretriz_base_inst_tipo
        UNIQUE (instituicao_id, tipo_neurodivergencia)
);

CREATE INDEX IF NOT EXISTS idx_school_pei_diretriz_base_instituicao
    ON public.school_pei_diretriz_base (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_pei_diretriz_base_ativo
    ON public.school_pei_diretriz_base (instituicao_id)
    WHERE ativo = TRUE;

COMMENT ON TABLE public.school_pei_diretriz_base IS
  'Diretriz institucional de PEI por tipo de neurodivergência (texto livre até haver taxonomia oficial).';
COMMENT ON COLUMN public.school_pei_diretriz_base.tipo_neurodivergencia IS
  'Texto livre por ora (ex.: TDAH, TEA, Dislexia). Sem taxonomia fixa.';

-- ---------------------------------------------------------------------------
-- 4) PEI individualizado — dossiê do aluno
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_pei_individualizado (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id               UUID NOT NULL
        REFERENCES public.school_alunos (id) ON DELETE CASCADE,
    pei_diretriz_base_id   UUID NOT NULL
        REFERENCES public.school_pei_diretriz_base (id) ON DELETE CASCADE,
    particularidades       TEXT,
    ativo                  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_pei_individualizado_aluno_diretriz
        UNIQUE (aluno_id, pei_diretriz_base_id)
);

CREATE INDEX IF NOT EXISTS idx_school_pei_individualizado_aluno
    ON public.school_pei_individualizado (aluno_id);

CREATE INDEX IF NOT EXISTS idx_school_pei_individualizado_diretriz
    ON public.school_pei_individualizado (pei_diretriz_base_id);

COMMENT ON TABLE public.school_pei_individualizado IS
  'Dossiê PEI do aluno. Um aluno pode ter mais de uma diretriz base (múltiplas condições).';
COMMENT ON COLUMN public.school_pei_individualizado.particularidades IS
  'Particularidades do aluno (ex.: sentar na primeira fileira, usar fone abafador).';

-- ---------------------------------------------------------------------------
-- 5) Planos de aula espelhados — loop de auditoria (raio-x do coordenador)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_planos_aula_espelhados (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id           UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    professor_vinculo_id     UUID NOT NULL
        REFERENCES public.school_professores_vinculo (id) ON DELETE CASCADE,
    turma_id                 UUID NOT NULL
        REFERENCES public.school_turmas (id) ON DELETE CASCADE,
    metodologia_catalogo_id  UUID NOT NULL
        REFERENCES public.school_metodologias_catalogo (id) ON DELETE RESTRICT,
    pei_individualizado_id   UUID
        REFERENCES public.school_pei_individualizado (id) ON DELETE SET NULL,
    semana_referencia        DATE NOT NULL,
    conteudo_resumo          TEXT,
    status                   TEXT NOT NULL DEFAULT 'pendente',
    observacoes_coordenador  TEXT,
    origem_plano_b2c_id      UUID,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_school_planos_aula_espelhados_status
        CHECK (status IN ('pendente', 'aprovado', 'reprovado'))
);

CREATE INDEX IF NOT EXISTS idx_school_planos_aula_instituicao
    ON public.school_planos_aula_espelhados (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_planos_aula_professor
    ON public.school_planos_aula_espelhados (professor_vinculo_id);

CREATE INDEX IF NOT EXISTS idx_school_planos_aula_turma
    ON public.school_planos_aula_espelhados (turma_id);

CREATE INDEX IF NOT EXISTS idx_school_planos_aula_status
    ON public.school_planos_aula_espelhados (instituicao_id, status);

CREATE INDEX IF NOT EXISTS idx_school_planos_aula_semana
    ON public.school_planos_aula_espelhados (instituicao_id, semana_referencia);

COMMENT ON TABLE public.school_planos_aula_espelhados IS
  'Loop de auditoria: espelho do planejamento feito no B2C. Alimenta o raio-x do coordenador.';
COMMENT ON COLUMN public.school_planos_aula_espelhados.pei_individualizado_id IS
  'NULLABLE: nem toda aula envolve adaptação PEI.';
COMMENT ON COLUMN public.school_planos_aula_espelhados.origem_plano_b2c_id IS
  'Referência lógica ao plano original no B2C — NÃO é FK (contrato: sem FK cross-DB).';
COMMENT ON COLUMN public.school_planos_aula_espelhados.status IS
  'pendente | aprovado | reprovado';

-- ---------------------------------------------------------------------------
-- Catálogo global — seed parcial (3 metodologias confirmadas)
-- ---------------------------------------------------------------------------
-- (seed fica após CREATE da tabela; ver bloco CREATE school_metodologias_catalogo acima
-- Na prática o seed está junto ao CREATE acima — mantido aqui só como documentação.

-- ---------------------------------------------------------------------------
-- Limpeza: school_editor_pedagogico superada (1 metodologia/instituição).
-- Tabela vazia (0 linhas) — remove com segurança. Recriada no .down.sql.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS public.school_editor_pedagogico CASCADE;

COMMIT;
