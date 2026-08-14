-- Aliases dos nomes polidos (035) para curadoria / AEE / PEI / webhook B2C
-- continuarem encaixando nas metodologias canônicas pelo codigo.

BEGIN;

CREATE TABLE IF NOT EXISTS public.school_metodologias_aliases (
    alias_norm  TEXT PRIMARY KEY,
    codigo      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_school_metodologias_aliases_codigo
    ON public.school_metodologias_aliases (codigo);

COMMENT ON TABLE public.school_metodologias_aliases IS
  'Rótulos antigos e alternativos → codigo do catálogo canônico (39).';

INSERT INTO public.school_metodologias_aliases (alias_norm, codigo)
SELECT LOWER(TRIM(codigo)), codigo
FROM public.school_metodologias_catalogo
WHERE codigo IS NOT NULL AND TRIM(codigo) <> ''
ON CONFLICT (alias_norm) DO UPDATE SET codigo = EXCLUDED.codigo;

INSERT INTO public.school_metodologias_aliases (alias_norm, codigo)
SELECT LOWER(TRIM(nome)), codigo
FROM public.school_metodologias_catalogo
WHERE nome IS NOT NULL AND TRIM(nome) <> '' AND codigo IS NOT NULL
ON CONFLICT (alias_norm) DO UPDATE SET codigo = EXCLUDED.codigo;

INSERT INTO public.school_metodologias_aliases (alias_norm, codigo) VALUES
    ('eduscrum', 'agil_eduscrum'),
    ('discurso de elevador', 'agil_elevator_pitch'),
    ('elevator pitch', 'agil_elevator_pitch'),
    ('hackathons', 'agil_hackathons'),
    ('mapeamento mental', 'agil_mapeamento_mental'),
    ('pedagogia extrema', 'agil_pedagogia_extrema'),
    ('gamificação de conteúdo', 'gamificacao_de_conteudo'),
    ('gamificação estrutural', 'gamificacao_estrutural'),
    ('gamificação estrutural/conteúdo', 'gamificacao_estrutural'),
    ('aprendizagem baseada em jogos', 'imersiva_aprendizagem_jogos'),
    ('escape room', 'imersiva_escape_room'),
    ('escape room educacional', 'imersiva_escape_room'),
    ('jogos sérios com blocos 3d', 'imersiva_jogos_serios_3d'),
    ('jogos sérios 3d', 'imersiva_jogos_serios_3d'),
    ('roleplay', 'imersiva_roleplaying'),
    ('roleplaying', 'imersiva_roleplaying'),
    ('jogo de papéis', 'imersiva_roleplaying'),
    ('simulações', 'imersiva_simulacoes'),
    ('vivência imersiva multissensorial', 'imersiva_vivencia_multissensorial'),
    ('vivência metodologia imersiva multissensorial', 'imersiva_vivencia_multissensorial'),
    ('chatbots', 'analitica_chatbots'),
    ('bots personalizáveis', 'analitica_chatbots'),
    ('diagnóstico coletivo', 'analitica_diagnostico_coletivo'),
    ('dog or cat: reconhecimento de imagens', 'analitica_dog_or_cat'),
    ('dog or cat', 'analitica_dog_or_cat'),
    ('extrato de participação', 'analitica_extrato_participacao'),
    ('extrato de participações', 'analitica_extrato_participacao'),
    ('ia generativa', 'analitica_ia_generativa'),
    ('inteligência artificial generativa', 'analitica_ia_generativa'),
    ('mapa de calor', 'analitica_mapa_calor'),
    ('analítica da aprendizagem', 'analitica_learning_analytics'),
    ('metodologia analítica da aprendizagem', 'analitica_learning_analytics'),
    ('learning analytics', 'analitica_learning_analytics'),
    ('rag', 'analitica_rag'),
    ('trilhas de aprendizagem', 'analitica_trilhas_adaptativas'),
    ('trilhas de aprendizagem adaptativas', 'analitica_trilhas_adaptativas'),
    ('trilha de aprendizagem adaptativa', 'analitica_trilhas_adaptativas'),
    ('aprendizagem baseada em casos', 'aprendizagem_baseada_em_casos'),
    ('caso empático', 'aprendizagem_baseada_em_casos'),
    ('abordagem problematizadora', 'criativa_abordagem_problematizadora'),
    ('aprendizagem baseada em equipes', 'criativa_aprendizagem_equipes'),
    ('team-based learning', 'criativa_aprendizagem_equipes'),
    ('tbl', 'criativa_aprendizagem_equipes'),
    ('aprendizagem maker', 'criativa_aprendizagem_maker'),
    ('coaching reverso', 'criativa_coaching_reverso'),
    ('design thinking', 'criativa_design_thinking_express'),
    ('design thinking express', 'criativa_design_thinking_express'),
    ('dt express', 'criativa_design_thinking_express'),
    ('mapa de polaridades', 'criativa_mapa_polaridades'),
    ('narrativas transmídia', 'criativa_narrativas_transmidia'),
    ('narrativas transmídia em rotação por estações', 'criativa_narrativas_transmidia'),
    ('rotação por estações', 'criativa_narrativas_transmidia'),
    ('painel da diversidade de perspectivas', 'criativa_painel_diversidade'),
    ('painel de diversidade', 'criativa_painel_diversidade'),
    ('aprendizagem baseada em problemas', 'criativa_pbl_problemas'),
    ('aprendizagem baseada em problemas (pbl)', 'criativa_pbl_problemas'),
    ('pbl', 'criativa_pbl_problemas'),
    ('abp', 'criativa_pbl_problemas'),
    ('aprendizagem baseada em projetos', 'criativa_pbl_projetos'),
    ('pjbl', 'criativa_pbl_projetos'),
    ('sala de aula invertida', 'criativa_sala_invertida'),
    ('flipped classroom', 'criativa_sala_invertida'),
    ('rotina veja-pense-pergunte-crie', 'criativa_veja_pense_pergunte_crie'),
    ('world cafe', 'criativa_world_cafe')
ON CONFLICT (alias_norm) DO UPDATE SET codigo = EXCLUDED.codigo;

-- Regrava nomes denormalizados para o rótulo canônico atual (tabela a tabela).
DO $$
BEGIN
    IF to_regclass('public.school_curadoria_metodologias') IS NOT NULL THEN
        UPDATE public.school_curadoria_metodologias cur
        SET metodologia_nome = c.nome
        FROM public.school_metodologias_aliases a
        JOIN public.school_metodologias_catalogo c ON c.codigo = a.codigo
        WHERE a.alias_norm = LOWER(TRIM(cur.metodologia_nome))
          AND cur.metodologia_nome IS DISTINCT FROM c.nome;
    END IF;

    IF to_regclass('public.school_curadoria_pei') IS NOT NULL THEN
        UPDATE public.school_curadoria_pei cur
        SET metodologia_nome = c.nome
        FROM public.school_metodologias_aliases a
        JOIN public.school_metodologias_catalogo c ON c.codigo = a.codigo
        WHERE a.alias_norm = LOWER(TRIM(cur.metodologia_nome))
          AND cur.metodologia_nome IS DISTINCT FROM c.nome;
    END IF;

    IF to_regclass('public.school_aee_metodologias_org') IS NOT NULL THEN
        UPDATE public.school_aee_metodologias_org org
        SET metodologia_nome = c.nome
        FROM public.school_metodologias_aliases a
        JOIN public.school_metodologias_catalogo c ON c.codigo = a.codigo
        WHERE a.alias_norm = LOWER(TRIM(org.metodologia_nome))
          AND org.metodologia_nome IS DISTINCT FROM c.nome
          AND NOT EXISTS (
                SELECT 1
                FROM public.school_aee_metodologias_org other
                WHERE other.aee_matriz_id = org.aee_matriz_id
                  AND other.metodologia_nome = c.nome
                  AND other.id IS DISTINCT FROM org.id
              );
    END IF;

    IF to_regclass('public.school_pei_metodologia_adaptacao') IS NOT NULL THEN
        UPDATE public.school_pei_metodologia_adaptacao pei
        SET metodologia_nome = c.nome
        FROM public.school_metodologias_aliases a
        JOIN public.school_metodologias_catalogo c ON c.codigo = a.codigo
        WHERE a.alias_norm = LOWER(TRIM(pei.metodologia_nome))
          AND pei.metodologia_nome IS DISTINCT FROM c.nome;
    END IF;

    IF to_regclass('public.school_planos_aula_espelhados') IS NOT NULL THEN
        UPDATE public.school_planos_aula_espelhados p
        SET mesa_payload_json = jsonb_set(
                p.mesa_payload_json,
                '{metodologia_nome}',
                to_jsonb(c.nome)
            )
        FROM public.school_metodologias_aliases a
        JOIN public.school_metodologias_catalogo c ON c.codigo = a.codigo
        WHERE p.mesa_payload_json ? 'metodologia_nome'
          AND a.alias_norm = LOWER(TRIM(p.mesa_payload_json->>'metodologia_nome'))
          AND (p.mesa_payload_json->>'metodologia_nome') IS DISTINCT FROM c.nome;
    END IF;
END $$;

COMMIT;
