-- PanelDX — Mapeamento leaf_dime → área escolar (Panorama Executivo / heatmap)
-- Idempotente: pode ser executado mais de uma vez.

ALTER TABLE public.leaf_dime
    ADD COLUMN IF NOT EXISTS area_escolar VARCHAR(80);

COMMENT ON COLUMN public.leaf_dime.area_escolar IS
    'Área operacional da escola para alocação no mapa de calor do Panorama Executivo.';

UPDATE public.leaf_dime SET area_escolar = 'Diretoria'
WHERE UPPER(TRIM(COALESCE(code_dime, ''))) = 'SV'
   OR name_dime ILIKE '%Visão Compartilhada%';

UPDATE public.leaf_dime SET area_escolar = 'Desenvolvimento Humano'
WHERE UPPER(TRIM(COALESCE(code_dime, ''))) = 'HC'
   OR name_dime ILIKE '%Coração e Conexão%';

UPDATE public.leaf_dime SET area_escolar = 'Administração e Secretaria'
WHERE UPPER(TRIM(COALESCE(code_dime, ''))) = 'FS'
   OR name_dime ILIKE '%Estrutura Fluida%';

UPDATE public.leaf_dime SET area_escolar = 'Pedagógico'
WHERE UPPER(TRIM(COALESCE(code_dime, ''))) = 'LA'
   OR name_dime ILIKE '%Aprendizagem em Ação%';

UPDATE public.leaf_dime SET area_escolar = 'Tecnologia da Informação'
WHERE UPPER(TRIM(COALESCE(code_dime, ''))) = 'DA'
   OR name_dime ILIKE '%Arquitetura Digital%';
