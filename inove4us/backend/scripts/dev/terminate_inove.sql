SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
 WHERE datname = 'inove4us'
   AND pid <> pg_backend_pid();
