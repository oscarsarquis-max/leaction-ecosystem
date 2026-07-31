UPDATE public.ctdi_clie
   SET creditos_ia = 20,
       is_test = TRUE
 WHERE LOWER(TRIM(mail_clie)) = 'inovador@inove4us.com.br';

SELECT id_clie, mail_clie, creditos_ia, plan_tier
  FROM public.ctdi_clie
 WHERE LOWER(TRIM(mail_clie)) = 'inovador@inove4us.com.br';
