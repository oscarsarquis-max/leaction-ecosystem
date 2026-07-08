-- Micro-CMS PanelDX: configuração de conteúdo público (landing + instruções)
CREATE TABLE IF NOT EXISTS public.ctdi_cms_config (
    id_cms              SERIAL PRIMARY KEY,
    config_key          VARCHAR(50) NOT NULL DEFAULT 'default',
    landing_page_data   JSONB NOT NULL DEFAULT '{}'::jsonb,
    instructions_data   TEXT,
    updated_at          TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ctdi_cms_config_key UNIQUE (config_key)
);

INSERT INTO public.ctdi_cms_config (config_key, landing_page_data, instructions_data)
VALUES (
    'default',
    '{
        "hero": {
            "leaction_title": "LeAction System",
            "paneldx_title": "PanelDX",
            "subtitle": "Transformação Digital Educacional DX",
            "description": "Inteligência, metodologia e execução para escolas e redes de ensino."
        },
        "columns": [
            {
                "image_url": "/images/logo3.jpg",
                "title": "Conteúdo de Interesse",
                "description": "Destaque institucional, notícias ou materiais estratégicos para sua rede de ensino."
            },
            {
                "video_url": "",
                "image_url": "",
                "title": "Metodologia CTDI",
                "description": "Framework integrado para diagnóstico, planejamento e execução da transformação digital educacional.",
                "visible": true
            },
            {
                "image_url": "",
                "title": "Destaque Complementar 1",
                "description": "Espaço adicional para conteúdo institucional, cases ou materiais de apoio."
            },
            {
                "image_url": "",
                "title": "Destaque Complementar 2",
                "description": "Segundo bloco da segunda linha do grid — eventos, parcerias ou novidades."
            },
            {
                "image_url": "",
                "title": "Destaque Complementar 3",
                "description": "Terceiro bloco da segunda linha — links úteis, vídeos ou chamadas secundárias."
            }
        ],
        "cta_consultor": {
            "title": "Descubra como resolver seu maior desafio de gestão em segundos.",
            "button_text": "Falar com Consultor IA (Gratuito)"
        }
    }'::jsonb,
    '<h2>Guia Rápido: Diagnóstico de Maturidade Digital</h2><p>A <strong>Transformação Digital</strong> é um imperativo no setor educacional. A <strong>Avaliação de Maturidade LeAction</strong> oferece um diagnóstico preciso da situação atual de sua organização.</p><h3>1. Oportunidade e Estratégia</h3><p>Use o framework LeActionF como espinha dorsal do processo, garantindo comparabilidade e relevância para escolas e redes.</p><h3>2. Sobre a Avaliação</h3><ul><li><strong>90 questões</strong> estratégicas (escala 1 a 5)</li><li>Respostas completas são essenciais para a precisão do diagnóstico</li><li>Reserve tempo adequado para preenchimento</li></ul><h3>3. Fluxo de Acesso</h3><ol><li>Inicie o diagnóstico em <strong>Iniciar Diagnóstico</strong> (cadastro)</li><li>Aceite o Termo de Privacidade/NDA</li><li>Obtenha o código de acesso por e-mail</li><li>Faça login com e-mail + código</li><li>Preencha o questionário e exporte o relatório em PDF</li></ol><p><strong>Suporte:</strong> <a href="mailto:conhecer@leaction.com.br">conhecer@leaction.com.br</a></p>'
)
ON CONFLICT (config_key) DO NOTHING;
