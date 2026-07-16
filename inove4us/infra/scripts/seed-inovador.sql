-- Seed canônico inove4us (somente DB inove4us — nunca LeAction_SysF)
-- E-mail: inovador@inove4us.com.br
-- Código: LA-INOVE1

BEGIN;

WITH upsert_clie AS (
  INSERT INTO public.ctdi_clie (
    nome_clie, mail_clie, empresa_clie, init_role,
    has_active_project, justificativa_solo
  )
  SELECT
    'Inovador inove4us',
    'inovador@inove4us.com.br',
    'inove4us',
    'GENERAL',
    false,
    'Seed oficial local — Mesa do Inovador'
  WHERE NOT EXISTS (
    SELECT 1 FROM public.ctdi_clie
    WHERE LOWER(TRIM(mail_clie)) = 'inovador@inove4us.com.br'
  )
  RETURNING id_clie
),
resolved AS (
  SELECT id_clie FROM upsert_clie
  UNION ALL
  SELECT id_clie FROM public.ctdi_clie
  WHERE LOWER(TRIM(mail_clie)) = 'inovador@inove4us.com.br'
  LIMIT 1
)
INSERT INTO public.ctdi_matu (id_clie, status_ia)
SELECT r.id_clie, 'SANDBOX'
FROM resolved r
WHERE NOT EXISTS (
  SELECT 1 FROM public.ctdi_matu m WHERE m.id_clie = r.id_clie
);

INSERT INTO public.ctdi_lead_access (id_clie, access_code)
SELECT c.id_clie, 'LA-INOVE1'
FROM public.ctdi_clie c
WHERE LOWER(TRIM(c.mail_clie)) = 'inovador@inove4us.com.br'
ON CONFLICT (id_clie) DO UPDATE
  SET access_code = EXCLUDED.access_code,
      created_at = now();

COMMIT;

SELECT c.id_clie, c.nome_clie, c.mail_clie, a.access_code, m.status_ia
FROM public.ctdi_clie c
LEFT JOIN public.ctdi_lead_access a ON a.id_clie = c.id_clie
LEFT JOIN public.ctdi_matu m ON m.id_clie = c.id_clie
WHERE LOWER(TRIM(c.mail_clie)) = 'inovador@inove4us.com.br';
