-- inove4us School — cadeia de desafio no espelho de planos (pré-requisito do grafo).
-- Numeração: 010 (009 = léxico Método inove4us).
-- Espelha a ideia de cadeia do B2C (id_evento_pai) sem FK cross-DB.
-- Só altera school_planos_aula_espelhados.

BEGIN;

ALTER TABLE public.school_planos_aula_espelhados
    ADD COLUMN IF NOT EXISTS desafio_grupo_id UUID,
    ADD COLUMN IF NOT EXISTS desafio_titulo TEXT,
    ADD COLUMN IF NOT EXISTS desafio_sequencia INTEGER;

COMMENT ON COLUMN public.school_planos_aula_espelhados.desafio_grupo_id IS
  'Identifica a cadeia do desafio (mesmo valor = mesma cápsula). NULL no Dia a Dia. Espelho lógico da cadeia B2C — sem FK cross-DB.';
COMMENT ON COLUMN public.school_planos_aula_espelhados.desafio_titulo IS
  'Rótulo da cápsula (tema do desafio). Replicado em todas as linhas do mesmo desafio_grupo_id.';
COMMENT ON COLUMN public.school_planos_aula_espelhados.desafio_sequencia IS
  'Posição da aula na cadeia (1, 2, 3…). Independente da data.';

-- Dados de teste já existentes (tipo_aula=desafio sem grupo) precisam de grupo
-- antes do CHECK; gera um UUID estável por linha órfã.
UPDATE public.school_planos_aula_espelhados
SET
    desafio_grupo_id = COALESCE(desafio_grupo_id, gen_random_uuid()),
    desafio_titulo = COALESCE(desafio_titulo, 'Desafio'),
    desafio_sequencia = COALESCE(desafio_sequencia, 1),
    updated_at = CURRENT_TIMESTAMP
WHERE tipo_aula = 'desafio'
  AND desafio_grupo_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_school_planos_aula_desafio_grupo
    ON public.school_planos_aula_espelhados (desafio_grupo_id)
    WHERE desafio_grupo_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_school_planos_aula_desafio_seq
    ON public.school_planos_aula_espelhados (desafio_grupo_id, desafio_sequencia)
    WHERE desafio_grupo_id IS NOT NULL;

ALTER TABLE public.school_planos_aula_espelhados
    DROP CONSTRAINT IF EXISTS chk_school_planos_aula_desafio_cadeia;

ALTER TABLE public.school_planos_aula_espelhados
    ADD CONSTRAINT chk_school_planos_aula_desafio_cadeia
        CHECK (
            (tipo_aula = 'dia_a_dia' AND desafio_grupo_id IS NULL)
            OR (tipo_aula = 'desafio' AND desafio_grupo_id IS NOT NULL)
        );

COMMIT;
