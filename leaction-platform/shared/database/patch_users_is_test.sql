-- Marca contas de teste — excluídas de estatísticas de pagamento/acesso.
BEGIN;

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS is_test BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_users_is_test
  ON public.users (is_test)
  WHERE is_test = TRUE;

-- Contas de homologação conhecidas
UPDATE public.users
SET is_test = TRUE
WHERE LOWER(TRIM(email)) IN (
  'inovador@inove4us.com.br',
  'admin@actionhub.com.br'
);

COMMIT;
