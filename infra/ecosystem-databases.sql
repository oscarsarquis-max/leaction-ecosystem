-- Bancos do monorepo leaction-ecosystem (executado no primeiro start do Postgres).
-- Credenciais padrão: admin / password123 — porta host 5433

SELECT 'CREATE DATABASE "LeAction_SysF"' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'LeAction_SysF')\gexec
SELECT 'CREATE DATABASE "MAtivas"' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'MAtivas')\gexec
SELECT 'CREATE DATABASE chamelleon' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'chamelleon')\gexec
SELECT 'CREATE DATABASE inove4us' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'inove4us')\gexec
SELECT 'CREATE DATABASE prodinx' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'prodinx')\gexec
SELECT 'CREATE DATABASE "LASim"' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'LASim')\gexec
SELECT 'CREATE DATABASE "diario-obra"' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'diario-obra')\gexec
