-- DRY-RUN ONLY — não aplica DELETE.
-- Seed de produção: Escola Teste (escolateste.edu.br)
-- Convenção: razao_social ILIKE '%Escola Teste%' OR dominio_email = 'escolateste.edu.br'
--
-- NÃO EXECUTAR limpeza sem confirmação explícita do Oscar.
-- Este arquivo só inventaria o que seria removido.

\echo '=== dry-run limpeza Escola Teste ==='

SELECT id, razao_social, dominio_email, status, created_at
FROM public.school_instituicoes
WHERE lower(dominio_email) = 'escolateste.edu.br'
   OR razao_social ILIKE '%Escola Teste%';

-- Guarde o id abaixo se a query acima retornar uma linha:
-- \set inst '''<UUID>'''

SELECT i.id AS instituicao_id,
       i.razao_social,
       i.dominio_email,
       (SELECT count(*) FROM public.school_unidades u WHERE u.instituicao_id = i.id) AS unidades,
       (SELECT count(*) FROM public.school_gestores g WHERE g.instituicao_id = i.id) AS gestores,
       (SELECT count(*) FROM public.school_professores_vinculo p WHERE p.instituicao_id = i.id) AS professores_vinculo,
       (SELECT count(*) FROM public.school_periodos_letivos p WHERE p.instituicao_id = i.id) AS periodos,
       (SELECT count(*) FROM public.school_turmas t WHERE t.instituicao_id = i.id) AS turmas,
       (SELECT count(*) FROM public.school_disciplinas d WHERE d.instituicao_id = i.id) AS disciplinas,
       (SELECT count(*) FROM public.school_alunos a WHERE a.instituicao_id = i.id) AS alunos,
       (SELECT count(*) FROM public.school_alocacoes_docentes a WHERE a.instituicao_id = i.id) AS alocacoes,
       (SELECT count(*) FROM public.school_licencas l WHERE l.instituicao_id = i.id) AS licencas,
       (SELECT count(*) FROM public.school_hub_eventos_processados e WHERE e.instituicao_id = i.id) AS hub_eventos
FROM public.school_instituicoes i
WHERE lower(i.dominio_email) = 'escolateste.edu.br'
   OR i.razao_social ILIKE '%Escola Teste%';

SELECT g.email, g.nome, g.ativo
FROM public.school_gestores g
JOIN public.school_instituicoes i ON i.id = g.instituicao_id
WHERE lower(i.dominio_email) = 'escolateste.edu.br'
   OR i.razao_social ILIKE '%Escola Teste%'
ORDER BY g.email;

SELECT p.email_convite, p.status_vinculo
FROM public.school_professores_vinculo p
JOIN public.school_instituicoes i ON i.id = p.instituicao_id
WHERE lower(i.dominio_email) = 'escolateste.edu.br'
   OR i.razao_social ILIKE '%Escola Teste%'
ORDER BY p.email_convite;

-- NÃO EXECUTAR sem confirmação explícita:
-- BEGIN;
-- DELETE FROM public.school_instituicoes
-- WHERE lower(dominio_email) = 'escolateste.edu.br'
--    OR razao_social ILIKE '%Escola Teste%';
-- -- Cascades dependem dos FKs (unidades, gestores, períodos, etc.).
-- -- Também limpar order_id seed se sobrar órfão:
-- -- DELETE FROM public.school_hub_eventos_processados
-- -- WHERE order_id = 'seed-escolateste-escola-inicial-v1';
-- ROLLBACK;
