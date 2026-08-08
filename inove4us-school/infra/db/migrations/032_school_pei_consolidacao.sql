-- 032: Consolidar PEI no modelo AEE/pei_alunos (retirar legado Ciclo Vivo).
-- Decisão Oscar 2026-08-08: school_pei_individualizado + metodologia_adaptacao
-- saem. school_pei_alunos ganha aluno_id → school_alunos.
--
-- Passo 0 (local 2026-08-08): pei_individualizado=0; metodologia_adaptacao=1
-- (smoke Canvas Mania sem pei_aluno_id); curadoria_pei=0; planos com FK=0.
-- Seguro descartar legado sem migração de conteúdo.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) Desligar FKs que apontam para o legado
-- ---------------------------------------------------------------------------
ALTER TABLE public.school_curadoria_pei
    DROP CONSTRAINT IF EXISTS school_curadoria_pei_pei_aluno_id_fkey;

ALTER TABLE public.school_planos_aula_espelhados
    DROP CONSTRAINT IF EXISTS school_planos_aula_espelhados_pei_individualizado_id_fkey;

-- ---------------------------------------------------------------------------
-- 2) Dropar tabelas do Ciclo Vivo
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS public.school_pei_metodologia_adaptacao CASCADE;
DROP TABLE IF EXISTS public.school_pei_individualizado CASCADE;

-- Curadoria PEI passa a referenciar PEI documental (opcional)
ALTER TABLE public.school_curadoria_pei
    ADD CONSTRAINT school_curadoria_pei_pei_aluno_id_fkey
    FOREIGN KEY (pei_aluno_id)
    REFERENCES public.school_pei_alunos (id)
    ON DELETE SET NULL;

COMMENT ON COLUMN public.school_curadoria_pei.pei_aluno_id IS
  'Referência lógica ao PEI documental (school_pei_alunos). NULL = sugestão só por metodologia.';

COMMENT ON COLUMN public.school_planos_aula_espelhados.pei_individualizado_id IS
  'LEGADO (coluna órfã): antigo school_pei_individualizado. Não usar — preferir vínculo via mesa/payload.';

-- ---------------------------------------------------------------------------
-- 3) Ligar school_pei_alunos a aluno real (Secretaria)
-- ---------------------------------------------------------------------------
ALTER TABLE public.school_pei_alunos
    ADD COLUMN IF NOT EXISTS aluno_id UUID;

-- Garante alunos secretaria a partir dos PEIs de teste (nome/matrícula livres)
INSERT INTO public.school_alunos (instituicao_id, nome, matricula)
SELECT DISTINCT ON (
        p.instituicao_id,
        COALESCE(NULLIF(TRIM(p.matricula), ''), 'PEI-' || LEFT(p.id::text, 8))
    )
    p.instituicao_id,
    COALESCE(NULLIF(TRIM(p.nome_completo), ''), 'Aluno PEI'),
    COALESCE(NULLIF(TRIM(p.matricula), ''), 'PEI-' || LEFT(p.id::text, 8))
FROM public.school_pei_alunos p
WHERE p.aluno_id IS NULL
ON CONFLICT (instituicao_id, matricula) DO NOTHING;

-- Match por matrícula
UPDATE public.school_pei_alunos p
SET aluno_id = a.id
FROM public.school_alunos a
WHERE p.aluno_id IS NULL
  AND a.instituicao_id = p.instituicao_id
  AND a.matricula = COALESCE(NULLIF(TRIM(p.matricula), ''), 'PEI-' || LEFT(p.id::text, 8));

-- Match por nome (fallback)
UPDATE public.school_pei_alunos p
SET aluno_id = a.id
FROM public.school_alunos a
WHERE p.aluno_id IS NULL
  AND a.instituicao_id = p.instituicao_id
  AND LOWER(TRIM(a.nome)) = LOWER(TRIM(p.nome_completo));

-- Qualquer residual: cria aluno dedicado
INSERT INTO public.school_alunos (instituicao_id, nome, matricula)
SELECT
    p.instituicao_id,
    COALESCE(NULLIF(TRIM(p.nome_completo), ''), 'Aluno PEI'),
    'PEI-' || LEFT(p.id::text, 8)
FROM public.school_pei_alunos p
WHERE p.aluno_id IS NULL
ON CONFLICT (instituicao_id, matricula) DO NOTHING;

UPDATE public.school_pei_alunos p
SET aluno_id = a.id
FROM public.school_alunos a
WHERE p.aluno_id IS NULL
  AND a.instituicao_id = p.instituicao_id
  AND a.matricula = 'PEI-' || LEFT(p.id::text, 8);

ALTER TABLE public.school_pei_alunos
    ALTER COLUMN aluno_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'school_pei_alunos_aluno_id_fkey'
    ) THEN
        ALTER TABLE public.school_pei_alunos
            ADD CONSTRAINT school_pei_alunos_aluno_id_fkey
            FOREIGN KEY (aluno_id)
            REFERENCES public.school_alunos (id)
            ON DELETE RESTRICT;
    END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_school_pei_alunos_aluno
    ON public.school_pei_alunos (aluno_id);

COMMENT ON COLUMN public.school_pei_alunos.aluno_id IS
  'Aluno real da Secretaria (school_alunos). nome_completo/matricícula ficam como cache de exibição.';

COMMIT;
