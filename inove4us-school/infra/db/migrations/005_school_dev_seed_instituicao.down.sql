-- Remove apenas a instituição de desenvolvimento da Etapa 4.
BEGIN;

DELETE FROM public.school_instituicoes
WHERE id = 'a1111111-1111-4111-8111-111111111111'::uuid
   OR cnpj = '12.345.678/0001-90';

COMMIT;
