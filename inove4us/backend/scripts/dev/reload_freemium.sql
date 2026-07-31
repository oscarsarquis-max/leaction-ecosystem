-- Recarrega freemium local: inovador@inove4us.com.br
UPDATE public.ctdi_clie
   SET creditos_ia = 20,
       is_test = TRUE
 WHERE LOWER(TRIM(mail_clie)) = 'inovador@inove4us.com.br';

UPDATE public.inove_aulas_simples a
   SET created_at = created_at - INTERVAL '32 days'
  FROM public.ctdi_clie c
 WHERE a.id_clie = c.id_clie
   AND LOWER(TRIM(c.mail_clie)) = 'inovador@inove4us.com.br'
   AND date_trunc('month', COALESCE(a.created_at, CURRENT_TIMESTAMP))
       = date_trunc('month', CURRENT_TIMESTAMP);

SELECT id_clie, mail_clie, creditos_ia, plan_tier, COALESCE(is_test, FALSE) AS is_test
  FROM public.ctdi_clie
 WHERE LOWER(TRIM(mail_clie)) = 'inovador@inove4us.com.br'
 ORDER BY id_clie DESC;
