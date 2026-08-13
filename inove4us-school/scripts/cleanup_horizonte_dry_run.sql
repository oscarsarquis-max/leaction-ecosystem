-- DRY-RUN ONLY — não aplica DELETE.
-- Instituição seed: Colégio Horizonte Inovador
-- id fixo da seed: a1111111-1111-4111-8111-111111111111
--
-- ATENÇÃO: em produção atual esta é tipicamente a ÚNICA instituição.
-- Apagar = limpar o ambiente demo inteiro, não "remover lixo smoke".

\set inst '''a1111111-1111-4111-8111-111111111111'''

SELECT id, razao_social, created_at
FROM school_instituicoes
WHERE id = :inst::uuid
   OR razao_social ILIKE '%horizonte%'
   OR razao_social ILIKE '%smoke%';

SELECT 'unidades' AS entidade, count(*) AS n
FROM school_unidades WHERE instituicao_id = :inst::uuid
UNION ALL
SELECT 'gestores', count(*) FROM school_gestores WHERE instituicao_id = :inst::uuid
UNION ALL
SELECT 'professores_vinculo', count(*) FROM school_professores_vinculo WHERE instituicao_id = :inst::uuid
UNION ALL
SELECT 'avisos_mesa', count(*) FROM school_avisos_mesa WHERE instituicao_id = :inst::uuid;

-- Turmas/alunos via unidade (quando existirem)
SELECT 'turmas_via_unidade' AS entidade, count(*) AS n
FROM school_turmas t
JOIN school_unidades u ON u.id = t.unidade_id
WHERE u.instituicao_id = :inst::uuid;

-- NÃO EXECUTAR sem confirmação explícita:
-- BEGIN;
-- DELETE FROM school_instituicoes WHERE id = 'a1111111-1111-4111-8111-111111111111';
-- -- (cascades dependem dos FKs; validar antes)
-- ROLLBACK;
