-- Smoke UX: 12 aulas no MESMO dia para um professor (manhã×4, tarde×4, noite×4).
-- Objetivo: validar stacking de pílulas no Grafo do Radar.
--
-- Aplicar:
--   Get-Content infra/db/seed_smoke_grafo_12.sql -Raw | docker exec -i leaction_db psql -U admin -d inove4us_school

BEGIN;

-- Limpa smoke anterior
DELETE FROM public.school_planos_aula_espelhados
WHERE instituicao_id = 'a1111111-1111-4111-8111-111111111111'::uuid
  AND COALESCE(mesa_payload_json->>'seed_tag', '') = 'smoke_grafo_12';

DELETE FROM public.school_turmas
WHERE instituicao_id = 'a1111111-1111-4111-8111-111111111111'::uuid
  AND nome LIKE 'Smoke %';

-- Garante professor Seed (e-mail → "Prof. Seed" no FE).
-- professor_b2c_id = INTEGER (id_clie B2C); 900001 = placeholder de smoke, não produção.
INSERT INTO public.school_professores_vinculo (
    id, instituicao_id, professor_b2c_id, email_convite, status_vinculo
) VALUES (
    'd4444444-4444-4444-8444-444444444444'::uuid,
    'a1111111-1111-4111-8111-111111111111'::uuid,
    900001,
    'professor.seed@horizonte.edu.br',
    'ativo'
)
ON CONFLICT (id) DO UPDATE SET
    professor_b2c_id = EXCLUDED.professor_b2c_id,
    email_convite = EXCLUDED.email_convite,
    status_vinculo = 'ativo',
    updated_at = CURRENT_TIMESTAMP;

-- 12 turmas (4 por turno) — nomes curtos para as pílulas
WITH specs(seq, turno, label) AS (
    VALUES
        (1,  'manha', 'Smoke 6A M1'),
        (2,  'manha', 'Smoke 6B M2'),
        (3,  'manha', 'Smoke 7A M3'),
        (4,  'manha', 'Smoke 7B M4'),
        (5,  'tarde', 'Smoke 8A T1'),
        (6,  'tarde', 'Smoke 8B T2'),
        (7,  'tarde', 'Smoke 9A T3'),
        (8,  'tarde', 'Smoke 9B T4'),
        (9,  'noite', 'Smoke 1EM N1'),
        (10, 'noite', 'Smoke 2EM N2'),
        (11, 'noite', 'Smoke 3EM N3'),
        (12, 'noite', 'Smoke EJA N4')
)
INSERT INTO public.school_turmas (
    id, instituicao_id, unidade_id, nome, serie_ano, turno, ano_letivo, ativa
)
SELECT
    ('e5555555-5555-4555-8555-' || lpad(seq::text, 12, '0'))::uuid,
    'a1111111-1111-4111-8111-111111111111'::uuid,
    'b2222222-2222-4222-8222-222222222222'::uuid,
    label,
    CASE
        WHEN seq <= 4 THEN 'EF'
        WHEN seq <= 8 THEN 'EF'
        ELSE 'EM'
    END,
    turno,
    EXTRACT(YEAR FROM CURRENT_DATE)::int,
    TRUE
FROM specs
ON CONFLICT (instituicao_id, nome, ano_letivo) DO UPDATE SET
    turno = EXCLUDED.turno,
    ativa = TRUE,
    updated_at = CURRENT_TIMESTAMP;

-- Metodologia + desafio grupo
DO $$
DECLARE
    v_met UUID;
    v_prof UUID := 'd4444444-4444-4444-8444-444444444444'::uuid;
    v_inst UUID := 'a1111111-1111-4111-8111-111111111111'::uuid;
    v_dia DATE := CURRENT_DATE;
    v_desafio UUID := 'f6666666-6666-4666-8666-666666666666'::uuid;
    r RECORD;
    i INT := 0;
    v_tipo TEXT;
    v_status TEXT;
    v_mesa JSONB;
    v_origem UUID;
BEGIN
    SELECT id INTO v_met
    FROM public.school_metodologias_catalogo
    WHERE nome = 'Aprendizagem Baseada em Problemas'
    LIMIT 1;

    IF v_met IS NULL THEN
        SELECT id INTO v_met FROM public.school_metodologias_catalogo WHERE ativo LIMIT 1;
    END IF;

    FOR r IN
        SELECT id, nome, turno
        FROM public.school_turmas
        WHERE instituicao_id = v_inst AND nome LIKE 'Smoke %'
        ORDER BY
            CASE turno WHEN 'manha' THEN 1 WHEN 'tarde' THEN 2 ELSE 3 END,
            nome
    LOOP
        i := i + 1;
        -- Alterna Dia a Dia / Desafio; 3 com curadoria (brilho lilás)
        v_tipo := CASE WHEN i % 3 = 0 THEN 'desafio' ELSE 'dia_a_dia' END;
        v_status := CASE WHEN i <= 8 THEN 'pendente' ELSE 'aprovado' END;
        v_origem := ('a7777777-7777-4777-8777-' || lpad(i::text, 12, '0'))::uuid;
        v_mesa := jsonb_build_object(
            'seed_tag', 'smoke_grafo_12',
            'titulo', r.nome || ' · ' || upper(r.turno),
            'status', CASE WHEN v_status = 'aprovado' THEN 'concluido' ELSE 'em_execucao' END,
            'metodologia_nome', 'Aprendizagem Baseada em Problemas',
            'turno', r.turno,
            'has_teacher_adaptations', (i IN (3, 7, 11)),
            'texto_sugestao', CASE
                WHEN i IN (3, 7, 11)
                THEN 'Smoke: sugestão à coordenação para validar highlight de curadoria.'
                ELSE NULL
            END,
            'cards', jsonb_build_array(
                jsonb_build_object(
                    'id', 'c1',
                    'titulo', 'Abertura',
                    'coluna', 'pronto',
                    'duracao_minutos', 10
                ),
                jsonb_build_object(
                    'id', 'c2',
                    'titulo', 'Desenvolvimento',
                    'coluna', CASE WHEN v_status = 'aprovado' THEN 'pronto' ELSE 'fazendo' END,
                    'duracao_minutos', 30,
                    'ultima_observacao', 'Obs smoke ' || r.turno,
                    'historico', jsonb_build_array(
                        jsonb_build_object(
                            'de', 'para_fazer',
                            'para', 'fazendo',
                            'nota', 'Transição smoke · ' || r.turno,
                            'em', now()
                        )
                    )
                )
            )
        );

        INSERT INTO public.school_planos_aula_espelhados (
            instituicao_id,
            professor_vinculo_id,
            turma_id,
            metodologia_catalogo_id,
            semana_referencia,
            conteudo_resumo,
            status,
            origem_plano_b2c_id,
            tipo_aula,
            desafio_grupo_id,
            desafio_titulo,
            desafio_sequencia,
            mesa_payload_json
        ) VALUES (
            v_inst,
            v_prof,
            r.id,
            v_met,
            v_dia,
            'Smoke ' || upper(r.turno) || ' · ' || r.nome,
            v_status,
            v_origem,
            v_tipo,
            CASE WHEN v_tipo = 'desafio' THEN v_desafio ELSE NULL END,
            CASE WHEN v_tipo = 'desafio' THEN 'Desafio Smoke Radar' ELSE NULL END,
            CASE WHEN v_tipo = 'desafio' THEN i ELSE NULL END,
            v_mesa
        );
    END LOOP;
END $$;

COMMIT;

-- Verificação
SELECT
    t.turno,
    COUNT(*) AS aulas,
    string_agg(t.nome, ', ' ORDER BY t.nome) AS turmas
FROM public.school_planos_aula_espelhados p
JOIN public.school_turmas t ON t.id = p.turma_id
WHERE p.instituicao_id = 'a1111111-1111-4111-8111-111111111111'::uuid
  AND COALESCE(p.mesa_payload_json->>'seed_tag', '') = 'smoke_grafo_12'
GROUP BY t.turno
ORDER BY 1;

SELECT COUNT(*) AS total_smoke
FROM public.school_planos_aula_espelhados
WHERE COALESCE(mesa_payload_json->>'seed_tag', '') = 'smoke_grafo_12';
