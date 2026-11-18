-- GESTAO-002 — banco "gestao" e papéis do Loja de Pães – Gestão.
-- Só CREATE e GRANT. Nenhuma alteração em tabela da Loja.
-- Rodar como superusuário do cluster, conectado ao banco "postgres", via psql lendo
-- este arquivo por stdin. Variáveis psql obrigatórias (nunca em argumento de linha de comando):
--   gestao_app_pw, gestao_reader_pw

\set ON_ERROR_STOP on

-- 1) Papel dono do banco do Gestão (leitura e escrita só no banco "gestao")
CREATE ROLE gestao_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT
  CONNECTION LIMIT 10 PASSWORD :'gestao_app_pw';

CREATE DATABASE gestao OWNER gestao_app ENCODING 'UTF8';
REVOKE ALL ON DATABASE gestao FROM PUBLIC;
GRANT CONNECT ON DATABASE gestao TO gestao_app;

-- 2) Papel somente leitura para a Loja
CREATE ROLE gestao_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT
  CONNECTION LIMIT 5 PASSWORD :'gestao_reader_pw';
ALTER ROLE gestao_reader SET default_transaction_read_only = on;
ALTER ROLE gestao_reader SET statement_timeout = '15s';
ALTER ROLE gestao_reader SET idle_in_transaction_session_timeout = '30s';

GRANT CONNECT ON DATABASE lojadepaes TO gestao_reader;
