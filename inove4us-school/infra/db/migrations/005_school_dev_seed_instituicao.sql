-- inove4us School (B2B) — seed de desenvolvimento: 1 instituição.
-- Pré-requisitos: 001 (school_instituicoes).
-- UUID fixo para o FE apontar via VITE_INSTITUICAO_ID sem auth real (Etapa 4).

BEGIN;

INSERT INTO public.school_instituicoes (
    id,
    razao_social,
    cnpj,
    dominio_email,
    status
)
VALUES (
    'a1111111-1111-4111-8111-111111111111'::uuid,
    'Colégio Horizonte Inovador',
    '12.345.678/0001-90',
    'horizonte.edu.br',
    'ativa'
)
ON CONFLICT (cnpj) DO NOTHING;

COMMIT;
