-- Seat-based pricing: limite de usuários por plano comercial (dx_planos.max_usuarios)
-- Nota: 019 já é dx_vitrine_publicacoes — esta migration usa o próximo número livre.

BEGIN;

ALTER TABLE public.dx_planos
    ADD COLUMN IF NOT EXISTS max_usuarios INTEGER NOT NULL DEFAULT 5;

COMMENT ON COLUMN public.dx_planos.max_usuarios IS
    'Quantidade máxima de usuários ativos (paneldx_usuarios) por cliente no plano';

UPDATE public.dx_planos
SET max_usuarios = CASE
    WHEN LOWER(TRIM(nome)) LIKE '%premium%' THEN 999
    WHEN LOWER(TRIM(nome)) LIKE '%avançad%' OR LOWER(TRIM(nome)) LIKE '%avancad%' THEN 15
    WHEN LOWER(TRIM(nome)) LIKE '%básic%' OR LOWER(TRIM(nome)) LIKE '%basic%' THEN 5
    ELSE max_usuarios
END,
atualizado_em = NOW()
WHERE max_usuarios = 5 OR max_usuarios IS NULL;

COMMIT;
