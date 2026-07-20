-- Seed / reset canônico inove4us (somente DB inove4us — nunca LeAction_SysF)
-- E-mail: inovador@inove4us.com.br
-- Código: LA-INOVE1
-- Créditos gratuitos: 3 (cota freemium reduzida — uso intensivo de IA)
--
-- Idempotente: recria/atualiza o inovador, zera créditos para o freemium
-- e remove desafios/agenda anteriores desse cliente.

BEGIN;

-- 1) Cliente (insert se não existir)
INSERT INTO public.ctdi_clie (
  nome_clie, mail_clie, empresa_clie, init_role,
  has_active_project, justificativa_solo, creditos_ia
)
SELECT
  'Inovador inove4us',
  'inovador@inove4us.com.br',
  'inove4us',
  'GENERAL',
  false,
  'Seed oficial local — Mesa do Inovador',
  3
WHERE NOT EXISTS (
  SELECT 1 FROM public.ctdi_clie
  WHERE LOWER(TRIM(mail_clie)) = 'inovador@inove4us.com.br'
);

-- 2) Reset perfil + créditos gratuitos
UPDATE public.ctdi_clie
SET
  nome_clie = 'Inovador inove4us',
  empresa_clie = 'inove4us',
  init_role = 'GENERAL',
  has_active_project = false,
  justificativa_solo = 'Seed oficial local — Mesa do Inovador',
  creditos_ia = 3
WHERE LOWER(TRIM(mail_clie)) = 'inovador@inove4us.com.br';

-- 3) Limpa desafios / realizações / agenda desse inovador
DELETE FROM public.inove_agenda_eventos e
USING public.ctdi_clie c
WHERE e.id_clie = c.id_clie
  AND LOWER(TRIM(c.mail_clie)) = 'inovador@inove4us.com.br';

DELETE FROM public.inov_agenda_notas n
USING public.ctdi_clie c
WHERE n.id_clie = c.id_clie
  AND LOWER(TRIM(c.mail_clie)) = 'inovador@inove4us.com.br';

DELETE FROM public.inov_agenda_rotina r
USING public.ctdi_clie c
WHERE r.id_clie = c.id_clie
  AND LOWER(TRIM(c.mail_clie)) = 'inovador@inove4us.com.br';

-- 4) Maturidade sandbox
INSERT INTO public.ctdi_matu (id_clie, status_ia)
SELECT c.id_clie, 'SANDBOX'
FROM public.ctdi_clie c
WHERE LOWER(TRIM(c.mail_clie)) = 'inovador@inove4us.com.br'
  AND NOT EXISTS (
    SELECT 1 FROM public.ctdi_matu m WHERE m.id_clie = c.id_clie
  );

-- 5) Código de acesso
INSERT INTO public.ctdi_lead_access (id_clie, access_code)
SELECT c.id_clie, 'LA-INOVE1'
FROM public.ctdi_clie c
WHERE LOWER(TRIM(c.mail_clie)) = 'inovador@inove4us.com.br'
ON CONFLICT (id_clie) DO UPDATE
  SET access_code = EXCLUDED.access_code,
      created_at = now();

COMMIT;

SELECT
  c.id_clie,
  c.nome_clie,
  c.mail_clie,
  c.creditos_ia,
  a.access_code,
  m.status_ia,
  (
    SELECT COUNT(*) FROM public.inove_agenda_eventos e WHERE e.id_clie = c.id_clie
  ) AS desafios_restantes
FROM public.ctdi_clie c
LEFT JOIN public.ctdi_lead_access a ON a.id_clie = c.id_clie
LEFT JOIN public.ctdi_matu m ON m.id_clie = c.id_clie
WHERE LOWER(TRIM(c.mail_clie)) = 'inovador@inove4us.com.br';
