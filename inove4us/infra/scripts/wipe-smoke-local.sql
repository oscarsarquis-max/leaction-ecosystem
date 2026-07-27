-- Wipe smoke / homologação lixo no DB inove4us (local)
-- Mantém: inovador@inove4us.com.br, Escola Exemplo, Matemática,
--         desafios EduScrum reais (wizard_ia / manuais sem "smoke").

BEGIN;

-- 1) Clientes de smoke efêmeros
DELETE FROM public.inove_agenda_eventos
 WHERE id_clie IN (
   SELECT id_clie FROM public.ctdi_clie
    WHERE mail_clie ILIKE '%smoke%'
       OR mail_clie ILIKE 'inove4us.code.%'
 );
DELETE FROM public.inove_aulas_simples
 WHERE id_clie IN (
   SELECT id_clie FROM public.ctdi_clie
    WHERE mail_clie ILIKE '%smoke%'
       OR mail_clie ILIKE 'inove4us.code.%'
 );
DELETE FROM public.ctdi_lead_access
 WHERE id_clie IN (
   SELECT id_clie FROM public.ctdi_clie
    WHERE mail_clie ILIKE '%smoke%'
       OR mail_clie ILIKE 'inove4us.code.%'
 );
DELETE FROM public.ctdi_matu
 WHERE id_clie IN (
   SELECT id_clie FROM public.ctdi_clie
    WHERE mail_clie ILIKE '%smoke%'
       OR mail_clie ILIKE 'inove4us.code.%'
 );
DELETE FROM public.ctdi_clie
 WHERE mail_clie ILIKE '%smoke%'
    OR mail_clie ILIKE 'inove4us.code.%';

-- 2) Instituição alien do smoke (id_clie 12 / paneldx)
DELETE FROM public.inove_disciplinas d
 USING public.inove_cursos c
 JOIN public.inove_periodos_letivos p ON p.id = c.periodo_letivo_id
 JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
 WHERE d.curso_id = c.id
   AND (i.nome ILIKE '%Alien%' OR i.nome ILIKE '%20260725102757%');

DELETE FROM public.inove_cursos c
 USING public.inove_periodos_letivos p
 JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
 WHERE c.periodo_letivo_id = p.id
   AND (i.nome ILIKE '%Alien%' OR i.nome ILIKE '%20260725102757%');

DELETE FROM public.inove_periodos_letivos p
 USING public.inove_instituicoes i
 WHERE p.instituicao_id = i.id
   AND (i.nome ILIKE '%Alien%' OR i.nome ILIKE '%20260725102757%');

DELETE FROM public.inove_agenda_eventos e
 USING public.inove_instituicoes i
 WHERE e.id_clie = i.id_clie
   AND (i.nome ILIKE '%Alien%' OR i.nome ILIKE '%20260725102757%');

DELETE FROM public.inove_aulas_simples a
 USING public.inove_instituicoes i
 WHERE a.id_clie = i.id_clie
   AND (i.nome ILIKE '%Alien%' OR i.nome ILIKE '%20260725102757%');

DELETE FROM public.inove_instituicoes
 WHERE nome ILIKE '%Alien%' OR nome ILIKE '%20260725102757%';

-- 3) Eventos/aulas de smoke do inovador oficial (id via e-mail)
DELETE FROM public.inove_agenda_eventos e
 USING public.ctdi_clie c
 WHERE e.id_clie = c.id_clie
   AND LOWER(TRIM(c.mail_clie)) = 'inovador@inove4us.com.br'
   AND (
     e.titulo ILIKE '%smoke%'
     OR COALESCE(e.id_externo_importacao, '') ~* '(SMOKE|AULA-00|EVT-001|^FREE-|^MISS-)'
     OR e.origem = 'importacao'
   );

DELETE FROM public.inove_aulas_simples a
 USING public.ctdi_clie c
 WHERE a.id_clie = c.id_clie
   AND LOWER(TRIM(c.mail_clie)) = 'inovador@inove4us.com.br'
   AND (
     COALESCE(a.id_externo_importacao, '') ~* '(SMOKE|AULA-00|^FREE-|^MISS-)'
     OR a.origem = 'importacao'
     OR COALESCE(a.tema_aula, '') ILIKE '%smoke%'
   );

DELETE FROM public.inove_importacoes_lote lote
 USING public.ctdi_clie c
 WHERE lote.id_clie = c.id_clie
   AND LOWER(TRIM(c.mail_clie)) = 'inovador@inove4us.com.br';

-- 4) Períodos: um ano letivo limpo 2026 (em curso); remove 2º smoke
UPDATE public.inove_periodos_letivos p
SET rotulo = '2026',
    ano_letivo = 2026,
    data_inicio = DATE '2026-01-01',
    data_fim = DATE '2026-12-31',
    em_curso = TRUE
FROM public.inove_instituicoes i
WHERE p.instituicao_id = i.id
  AND LOWER(TRIM((SELECT mail_clie FROM public.ctdi_clie WHERE id_clie = i.id_clie))) = 'inovador@inove4us.com.br'
  AND p.id = (
    SELECT MIN(p2.id)
      FROM public.inove_periodos_letivos p2
     WHERE p2.instituicao_id = i.id
  );

DELETE FROM public.inove_periodos_letivos p
 USING public.inove_instituicoes i
 WHERE p.instituicao_id = i.id
   AND i.id_clie = (SELECT id_clie FROM public.ctdi_clie WHERE LOWER(TRIM(mail_clie)) = 'inovador@inove4us.com.br')
   AND p.rotulo ILIKE '%smoke%';

UPDATE public.inove_instituicoes i
SET nome = 'Escola Municipal Vale Verde'
WHERE i.id_clie = (SELECT id_clie FROM public.ctdi_clie WHERE LOWER(TRIM(mail_clie)) = 'inovador@inove4us.com.br')
  AND i.nome ILIKE '%Exemplo%';

COMMIT;

-- Conferência
SELECT 'eventos' AS what, COUNT(*)::text AS n FROM public.inove_agenda_eventos
UNION ALL
SELECT 'aulas', COUNT(*)::text FROM public.inove_aulas_simples
UNION ALL
SELECT 'periodos', COUNT(*)::text FROM public.inove_periodos_letivos
UNION ALL
SELECT 'instituicoes', COUNT(*)::text FROM public.inove_instituicoes;

SELECT id_evento, left(titulo,50) t, data_evento::date, disciplina_id, origem
  FROM public.inove_agenda_eventos
 ORDER BY data_evento, id_evento;

SELECT p.id, p.rotulo, p.data_inicio, p.data_fim, p.em_curso, i.nome
  FROM public.inove_periodos_letivos p
  JOIN public.inove_instituicoes i ON i.id = p.instituicao_id;
