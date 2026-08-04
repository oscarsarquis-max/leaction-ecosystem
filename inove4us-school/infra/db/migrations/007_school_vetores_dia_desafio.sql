-- inove4us School — dicotomia pedagógica alinhada ao B2C (Dia a Dia × Desafio).
-- Léxico público (mesmo do professor): "Dia a Dia · ciclo rápido" e "Desafio · método inove4us".
-- Pré-requisitos: 006.

BEGIN;

ALTER TABLE public.school_metodologia_config
    ADD COLUMN IF NOT EXISTS ativo_dia_a_dia BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS ativo_desafio BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN public.school_metodologia_config.ativo_dia_a_dia IS
  'Disponível para o vetor Dia a Dia (ciclo rápido ~50 min) na instituição.';
COMMENT ON COLUMN public.school_metodologia_config.ativo_desafio IS
  'Disponível para o vetor Desafio (método inove4us / projetos) na instituição.';

-- Todas as metodologias de referência servem aos dois vetores (espelho semântico do B2C).
ALTER TABLE public.school_metodologias_catalogo
    ADD COLUMN IF NOT EXISTS vetor_dia_a_dia BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS vetor_desafio BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN public.school_metodologias_catalogo.vetor_dia_a_dia IS
  'Pertence ao repertório Dia a Dia no inove4us (atividade em campo / ciclo rápido).';
COMMENT ON COLUMN public.school_metodologias_catalogo.vetor_desafio IS
  'Pertence ao repertório Desafio no inove4us (wizard / método inove4us).';

UPDATE public.school_metodologias_catalogo
SET
    vetor_dia_a_dia = TRUE,
    vetor_desafio = TRUE,
    updated_at = CURRENT_TIMESTAMP
WHERE origem = 'padrao';

COMMIT;
