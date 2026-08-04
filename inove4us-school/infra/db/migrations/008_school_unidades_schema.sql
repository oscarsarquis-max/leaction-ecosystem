-- inove4us School — Unidades (campus) + vínculos necessários ao Dashboard.
-- Numeração: 008 (005–007 já usadas: seed instituição, metodologias 39, vetores).
-- Pré-requisitos: 001–004 (instituicoes, gestores, turmas, calendario, planos_aula).
--
-- Normalização: unidade_id só em turmas (e gestores/calendário quando escopo local).
-- Alunos, professor_turma e planos_aula chegam à unidade via turma_id.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1) Unidades (campus)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_unidades (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id   UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    nome             TEXT NOT NULL,
    codigo           TEXT,
    cidade           TEXT,
    uf               TEXT,
    endereco         TEXT,
    ativo            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_unidades_inst_nome UNIQUE (instituicao_id, nome)
);

CREATE INDEX IF NOT EXISTS idx_school_unidades_instituicao
    ON public.school_unidades (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_unidades_ativo
    ON public.school_unidades (instituicao_id)
    WHERE ativo = TRUE;

COMMENT ON TABLE public.school_unidades IS
  'Campus / unidade de ensino de uma instituição. Base para agregação do dashboard por unidade.';

-- Unidade de desenvolvimento (opcional) — desbloqueia testes com a instituição seed.
INSERT INTO public.school_unidades (
    id, instituicao_id, nome, codigo, cidade, uf, ativo
)
SELECT
    'b2222222-2222-4222-8222-222222222222'::uuid,
    i.id,
    'Unidade Centro',
    'CENTRO',
    'São Paulo',
    'SP',
    TRUE
FROM public.school_instituicoes i
WHERE i.id = 'a1111111-1111-4111-8111-111111111111'::uuid
ON CONFLICT (instituicao_id, nome) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2) Turmas — unidade obrigatória (aula acontece em um campus)
-- ---------------------------------------------------------------------------
ALTER TABLE public.school_turmas
    ADD COLUMN IF NOT EXISTS unidade_id UUID
        REFERENCES public.school_unidades (id) ON DELETE RESTRICT;

-- Tabela vazia hoje; se houver linhas futuras sem unidade, não força cegamente.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'school_turmas'
          AND column_name = 'unidade_id'
          AND is_nullable = 'YES'
    ) THEN
        IF EXISTS (SELECT 1 FROM public.school_turmas WHERE unidade_id IS NULL) THEN
            RAISE EXCEPTION
                'school_turmas.unidade_id tem NULLs — associe cada turma a uma unidade antes de NOT NULL';
        END IF;
        ALTER TABLE public.school_turmas
            ALTER COLUMN unidade_id SET NOT NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_school_turmas_unidade
    ON public.school_turmas (unidade_id);

COMMENT ON COLUMN public.school_turmas.unidade_id IS
  'Campus onde a turma acontece. Fonte da verdade de unidade para alunos/planos via join.';

-- ---------------------------------------------------------------------------
-- 3) Gestores — NULL = escopo institucional; preenchido = escopo da unidade
-- ---------------------------------------------------------------------------
ALTER TABLE public.school_gestores
    ADD COLUMN IF NOT EXISTS unidade_id UUID
        REFERENCES public.school_unidades (id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_school_gestores_unidade
    ON public.school_gestores (unidade_id)
    WHERE unidade_id IS NOT NULL;

COMMENT ON COLUMN public.school_gestores.unidade_id IS
  'NULL = gestor da instituição inteira (ex.: Diretor). Preenchido = gestor da unidade (ex.: Coordenador local).';

-- ---------------------------------------------------------------------------
-- 4) Calendário letivo — NULL = instituição; preenchido = só aquela unidade
-- ---------------------------------------------------------------------------
ALTER TABLE public.school_calendario_letivo
    ADD COLUMN IF NOT EXISTS unidade_id UUID
        REFERENCES public.school_unidades (id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_school_calendario_unidade
    ON public.school_calendario_letivo (unidade_id)
    WHERE unidade_id IS NOT NULL;

COMMENT ON COLUMN public.school_calendario_letivo.unidade_id IS
  'NULL = evento para a instituição inteira. Preenchido = específico da unidade (ex.: feriado municipal).';

-- ---------------------------------------------------------------------------
-- 5) Planos espelhados — Dia a Dia × Desafio (léxico do professor)
-- ---------------------------------------------------------------------------
ALTER TABLE public.school_planos_aula_espelhados
    ADD COLUMN IF NOT EXISTS tipo_aula TEXT NOT NULL DEFAULT 'dia_a_dia';

ALTER TABLE public.school_planos_aula_espelhados
    DROP CONSTRAINT IF EXISTS chk_school_planos_aula_espelhados_tipo_aula;

ALTER TABLE public.school_planos_aula_espelhados
    ADD CONSTRAINT chk_school_planos_aula_espelhados_tipo_aula
        CHECK (tipo_aula IN ('dia_a_dia', 'desafio'));

CREATE INDEX IF NOT EXISTS idx_school_planos_aula_tipo
    ON public.school_planos_aula_espelhados (instituicao_id, tipo_aula);

COMMENT ON COLUMN public.school_planos_aula_espelhados.tipo_aula IS
  'dia_a_dia | desafio — mesma distinção do inove4us do professor.';

COMMIT;
