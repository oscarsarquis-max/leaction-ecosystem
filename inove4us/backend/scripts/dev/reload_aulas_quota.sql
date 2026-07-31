UPDATE public.inove_aulas_simples a
   SET created_at = created_at - INTERVAL '32 days'
  FROM public.ctdi_clie c
 WHERE a.id_clie = c.id_clie
   AND LOWER(TRIM(c.mail_clie)) = 'inovador@inove4us.com.br'
   AND date_trunc('month', COALESCE(a.created_at, CURRENT_TIMESTAMP))
       = date_trunc('month', CURRENT_TIMESTAMP);
