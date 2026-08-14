-- Seed de curadoria para testar cards + estrelas (Editor Pedagógico).
-- Metodologia canônica: "Aprendizagem baseada em problemas (PBL)" (catálogo 035).
-- Instituição: DEV_INSTITUICAO_ID padrão.
--
-- Aplicar:
--   docker exec -i leaction_db psql -U admin -d inove4us_school -f - < infra/db/seed_curadoria_teste.sql
--   (ou: Get-Content ... | docker exec -i leaction_db psql -U admin -d inove4us_school)

BEGIN;

-- Remove seeds anteriores deste arquivo (idempotente por marca no JSON)
DELETE FROM public.school_curadoria_metodologias
WHERE instituicao_id = 'a1111111-1111-4111-8111-111111111111'::uuid
  AND metodologia_nome = 'Aprendizagem baseada em problemas (PBL)'
  AND COALESCE(sugestao_professor_json->>'seed_tag', '') = 'seed_curadoria_teste';

INSERT INTO public.school_curadoria_metodologias (
    instituicao_id,
    metodologia_nome,
    sugestao_professor_json,
    status_analise
) VALUES
(
    'a1111111-1111-4111-8111-111111111111'::uuid,
    'Aprendizagem baseada em problemas (PBL)',
    '{
      "seed_tag": "seed_curadoria_teste",
      "professor_nome": "Eveline Braga",
      "aula_contexto": "Biologia: Sistema Digestório",
      "teacher_adaptation_text": "Os alunos ficaram confusos na etapa de pesquisa. Sugiro inverter e entregar os papéis antes da pesquisa iniciar.",
      "texto_sugestao": "Os alunos ficaram confusos na etapa de pesquisa. Sugiro inverter e entregar os papéis antes da pesquisa iniciar."
    }'::jsonb,
    'pendente'
),
(
    'a1111111-1111-4111-8111-111111111111'::uuid,
    'Aprendizagem baseada em problemas (PBL)',
    '{
      "seed_tag": "seed_curadoria_teste",
      "professor_nome": "Eveline Braga",
      "aula_contexto": "Biologia: Células e Tecidos (1º Ano)",
      "teacher_adaptation_text": "Na etapa de definição do problema, o tempo estourava. Proponho um timer visual de 8 minutos e um modelo de pergunta-guia no quadro.",
      "texto_sugestao": "Na etapa de definição do problema, o tempo estourava. Proponho um timer visual de 8 minutos e um modelo de pergunta-guia no quadro."
    }'::jsonb,
    'pendente'
),
(
    'a1111111-1111-4111-8111-111111111111'::uuid,
    'Aprendizagem baseada em problemas (PBL)',
    '{
      "seed_tag": "seed_curadoria_teste",
      "professor_nome": "Eveline Braga",
      "aula_contexto": "Ciências: Ecossistemas (2º Ano)",
      "teacher_adaptation_text": "Grupos mistos funcionaram melhor do que escolha livre. Sugiro sortear papéis (pesquisador, sintetizador, apresentador) no início do ciclo.",
      "texto_sugestao": "Grupos mistos funcionaram melhor do que escolha livre. Sugiro sortear papéis (pesquisador, sintetizador, apresentador) no início do ciclo."
    }'::jsonb,
    'pendente'
);

COMMIT;

-- Verificação esperada: 3 linhas / 3 estrelas na listagem do Editor
-- SELECT metodologia_nome, COUNT(*) FROM school_curadoria_metodologias
-- WHERE instituicao_id = 'a1111111-1111-4111-8111-111111111111'
--   AND metodologia_nome = 'Aprendizagem baseada em problemas (PBL)'
-- GROUP BY 1;
