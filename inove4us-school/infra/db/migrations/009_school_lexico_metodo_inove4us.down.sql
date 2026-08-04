BEGIN;

UPDATE public.school_metodologias_catalogo
SET
    nome = 'EduScrum',
    updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_eduscrum';

COMMIT;
