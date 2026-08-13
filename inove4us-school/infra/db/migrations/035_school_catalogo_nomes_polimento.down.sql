-- Rollback 035 — restaura nomes anteriores ao polimento.

BEGIN;

UPDATE public.school_metodologias_catalogo SET nome = 'Método inove4us', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_eduscrum';
UPDATE public.school_metodologias_catalogo SET nome = 'Vivência Metodologia imersiva Multissensorial', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'imersiva_vivencia_multissensorial';
UPDATE public.school_metodologias_catalogo SET nome = 'Metodologia analítica da Aprendizagem', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_learning_analytics';
UPDATE public.school_metodologias_catalogo SET nome = 'Chatbots', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_chatbots';
UPDATE public.school_metodologias_catalogo SET nome = 'RAG', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_rag';
UPDATE public.school_metodologias_catalogo SET nome = 'Canvas Mania', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_canvas_mania';
UPDATE public.school_metodologias_catalogo SET nome = 'Discurso de Elevador', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_elevator_pitch';
UPDATE public.school_metodologias_catalogo SET nome = 'Hackathons', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_hackathons';
UPDATE public.school_metodologias_catalogo SET nome = 'Mapeamento mental', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_mapeamento_mental';
UPDATE public.school_metodologias_catalogo SET nome = 'Minute Paper', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_minute_paper';
UPDATE public.school_metodologias_catalogo SET nome = 'Pecha Kucha', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_pecha_kucha';
UPDATE public.school_metodologias_catalogo SET nome = 'Pedagogia Extrema', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_pedagogia_extrema';
UPDATE public.school_metodologias_catalogo SET nome = 'Gamificação de Conteúdo', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'gamificacao_de_conteudo';
UPDATE public.school_metodologias_catalogo SET nome = 'Gamificação Estrutural', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'gamificacao_estrutural';
UPDATE public.school_metodologias_catalogo SET nome = 'Aprendizagem Baseada em Jogos', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'imersiva_aprendizagem_jogos';
UPDATE public.school_metodologias_catalogo SET nome = 'Escape Room', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'imersiva_escape_room';
UPDATE public.school_metodologias_catalogo SET nome = 'Jogos Sérios com Blocos 3D', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'imersiva_jogos_serios_3d';
UPDATE public.school_metodologias_catalogo SET nome = 'Roleplay', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'imersiva_roleplaying';
UPDATE public.school_metodologias_catalogo SET nome = 'Simulações', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'imersiva_simulacoes';
UPDATE public.school_metodologias_catalogo SET nome = 'Diagnóstico Coletivo', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_diagnostico_coletivo';
UPDATE public.school_metodologias_catalogo SET nome = 'Dog or Cat: Reconhecimento de Imagens', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_dog_or_cat';
UPDATE public.school_metodologias_catalogo SET nome = 'Extrato de Participação', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_extrato_participacao';
UPDATE public.school_metodologias_catalogo SET nome = 'Inteligência Artificial Generativa', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_ia_generativa';
UPDATE public.school_metodologias_catalogo SET nome = 'Mapa de Calor', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_mapa_calor';
UPDATE public.school_metodologias_catalogo SET nome = 'Trilhas de Aprendizagem', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'analitica_trilhas_adaptativas';
UPDATE public.school_metodologias_catalogo SET nome = 'Aprendizagem Baseada em Casos', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'aprendizagem_baseada_em_casos';
UPDATE public.school_metodologias_catalogo SET nome = 'Abordagem Problematizadora', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_abordagem_problematizadora';
UPDATE public.school_metodologias_catalogo SET nome = 'Aprendizagem Baseada em Equipes', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_aprendizagem_equipes';
UPDATE public.school_metodologias_catalogo SET nome = 'Aprendizagem Maker', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_aprendizagem_maker';
UPDATE public.school_metodologias_catalogo SET nome = 'Coaching Reverso', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_coaching_reverso';
UPDATE public.school_metodologias_catalogo SET nome = 'Design Thinking', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_design_thinking_express';
UPDATE public.school_metodologias_catalogo SET nome = 'Mapa de Polaridades', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_mapa_polaridades';
UPDATE public.school_metodologias_catalogo SET nome = 'Narrativas Transmídia em Rotação por Estações', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_narrativas_transmidia';
UPDATE public.school_metodologias_catalogo SET nome = 'Painel da Diversidade de Perspectivas', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_painel_diversidade';
UPDATE public.school_metodologias_catalogo SET nome = 'Aprendizagem Baseada em Problemas', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_pbl_problemas';
UPDATE public.school_metodologias_catalogo SET nome = 'Aprendizagem Baseada em Projetos', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_pbl_projetos';
UPDATE public.school_metodologias_catalogo SET nome = 'Sala de Aula Invertida', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_sala_invertida';
UPDATE public.school_metodologias_catalogo SET nome = 'Rotina Veja-Pense-Pergunte-Crie', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_veja_pense_pergunte_crie';
UPDATE public.school_metodologias_catalogo SET nome = 'World Café', updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'criativa_world_cafe';

COMMIT;
