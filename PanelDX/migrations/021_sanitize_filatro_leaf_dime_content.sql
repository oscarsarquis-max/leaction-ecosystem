-- Remove menções a Andrea Filatro no conteúdo de dimensões (leaf_dime)
BEGIN;

UPDATE public.leaf_dime
SET long_description = regexp_replace(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    regexp_replace(long_description, 'Profa\.?\s*Filatro', 'padrões de mercado', 'gi'),
                    'Prof\.?\s*Filatro', 'padrões de mercado', 'gi'),
                'Andrea\s+Filatro', 'padrões de mercado', 'gi'),
            'abordagem\s+de\s+Andrea\s+Filatro', 'padrões de mercado', 'gi'),
        'Filatro', 'padrões de mercado', 'gi')
WHERE long_description IS NOT NULL
  AND long_description ~* 'filatro|andrea';

UPDATE public.leaf_dime
SET desc_dime = regexp_replace(
        regexp_replace(
            regexp_replace(desc_dime, 'Andrea\s+Filatro', 'padrões de mercado', 'gi'),
            'Filatro', 'padrões de mercado', 'gi'),
        '\s{2,}', ' ', 'g')
WHERE desc_dime IS NOT NULL
  AND desc_dime ~* 'filatro|andrea';

COMMIT;
