-- Rollback 002_school_gestao_academica_schema.sql
-- Ordem: filhos antes dos pais (alunos antes de turmas).

BEGIN;

DROP TABLE IF EXISTS public.school_curriculo CASCADE;
DROP TABLE IF EXISTS public.school_calendario_letivo CASCADE;
DROP TABLE IF EXISTS public.school_alunos CASCADE;
DROP TABLE IF EXISTS public.school_turmas CASCADE;

COMMIT;
