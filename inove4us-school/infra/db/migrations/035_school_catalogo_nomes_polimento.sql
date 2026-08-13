-- inove4us School — Polimento de nomes do catálogo (39).
-- Fonte: proposta-catalogo-39-revisado (apenas Decisão + ajustes da revisão).
-- Só UPDATE de nome por codigo. Não altera descricao nem passos_execucao.

BEGIN;

UPDATE public.school_metodologias_catalogo SET nome = 'Método inove4us', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_eduscrum';

UPDATE public.school_metodologias_catalogo SET nome = 'Vivência Multissensorial', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'imersiva_vivencia_multissensorial';

UPDATE public.school_metodologias_catalogo SET nome = 'Análise da Aprendizagem', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_learning_analytics';

-- AJUSTAR na revisão: "Chatbot pedagógico" (mais amplo que "como tutor")
UPDATE public.school_metodologias_catalogo SET nome = 'Chatbot pedagógico', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_chatbots';

UPDATE public.school_metodologias_catalogo SET nome = 'Pesquisa com fontes confiáveis (RAG)', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_rag';

UPDATE public.school_metodologias_catalogo SET nome = 'Canvas Mania', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_canvas_mania';

UPDATE public.school_metodologias_catalogo SET nome = 'Pitch de elevador', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_elevator_pitch';

UPDATE public.school_metodologias_catalogo SET nome = 'Hackathon', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_hackathons';

UPDATE public.school_metodologias_catalogo SET nome = 'Mapa mental', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_mapeamento_mental';

UPDATE public.school_metodologias_catalogo SET nome = 'Minute Paper', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_minute_paper';

UPDATE public.school_metodologias_catalogo SET nome = 'Pecha Kucha', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_pecha_kucha';

-- AJUSTAR na revisão: escopo além de programação
UPDATE public.school_metodologias_catalogo SET nome = 'Dupla piloto e navegador', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_pedagogia_extrema';

UPDATE public.school_metodologias_catalogo SET nome = 'Gamificação de conteúdo', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'gamificacao_de_conteudo';

UPDATE public.school_metodologias_catalogo SET nome = 'Gamificação estrutural', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'gamificacao_estrutural';

UPDATE public.school_metodologias_catalogo SET nome = 'Aprendizagem baseada em jogos', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'imersiva_aprendizagem_jogos';

UPDATE public.school_metodologias_catalogo SET nome = 'Escape room pedagógico', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'imersiva_escape_room';

UPDATE public.school_metodologias_catalogo SET nome = 'Jogos sérios em ambiente 3D', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'imersiva_jogos_serios_3d';

UPDATE public.school_metodologias_catalogo SET nome = 'Roleplay (dramatização de papéis)', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'imersiva_roleplaying';

UPDATE public.school_metodologias_catalogo SET nome = 'Simulação', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'imersiva_simulacoes';

UPDATE public.school_metodologias_catalogo SET nome = 'Diagnóstico coletivo', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_diagnostico_coletivo';

UPDATE public.school_metodologias_catalogo SET nome = 'Classificação de imagens (treino e teste)', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_dog_or_cat';

UPDATE public.school_metodologias_catalogo SET nome = 'Extrato de participação', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_extrato_participacao';

UPDATE public.school_metodologias_catalogo SET nome = 'IA generativa na aula', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_ia_generativa';

UPDATE public.school_metodologias_catalogo SET nome = 'Mapa de calor', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_mapa_calor';

UPDATE public.school_metodologias_catalogo SET nome = 'Trilhas adaptativas', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_trilhas_adaptativas';

UPDATE public.school_metodologias_catalogo SET nome = 'Aprendizagem baseada em casos', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'aprendizagem_baseada_em_casos';

UPDATE public.school_metodologias_catalogo SET nome = 'Abordagem problematizadora', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_abordagem_problematizadora';

UPDATE public.school_metodologias_catalogo SET nome = 'Aprendizagem baseada em equipes (TBL)', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_aprendizagem_equipes';

UPDATE public.school_metodologias_catalogo SET nome = 'Aprendizagem maker', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_aprendizagem_maker';

UPDATE public.school_metodologias_catalogo SET nome = 'Coaching reverso', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_coaching_reverso';

UPDATE public.school_metodologias_catalogo SET nome = 'Design Thinking express', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_design_thinking_express';

UPDATE public.school_metodologias_catalogo SET nome = 'Mapa de polaridades', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_mapa_polaridades';

UPDATE public.school_metodologias_catalogo SET nome = 'Narrativa transmídia (estações)', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_narrativas_transmidia';

-- AJUSTAR na revisão: manter "diversidade"
UPDATE public.school_metodologias_catalogo SET nome = 'Painel de perspectivas diversas', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_painel_diversidade';

-- Par PBL / PjBL (AJUSTAR na revisão: diferenciar siglas)
UPDATE public.school_metodologias_catalogo SET nome = 'Aprendizagem baseada em problemas (PBL)', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_pbl_problemas';

UPDATE public.school_metodologias_catalogo SET nome = 'Aprendizagem baseada em projetos (PjBL)', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_pbl_projetos';

UPDATE public.school_metodologias_catalogo SET nome = 'Sala de aula invertida', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_sala_invertida';

UPDATE public.school_metodologias_catalogo SET nome = 'Rotina Veja · Pense · Pergunte · Crie', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_veja_pense_pergunte_crie';

UPDATE public.school_metodologias_catalogo SET nome = 'World Café', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_world_cafe';

COMMIT;
