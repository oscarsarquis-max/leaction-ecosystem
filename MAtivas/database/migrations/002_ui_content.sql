-- Migração 002: Conteúdo dinâmico da interface (textos e imagens)
CREATE TABLE IF NOT EXISTS ui_content (
    id              SERIAL PRIMARY KEY,
    content_key     VARCHAR(120) UNIQUE NOT NULL,
    content_value   VARCHAR(2000) NOT NULL,
    content_type    VARCHAR(20) NOT NULL DEFAULT 'text',
    label           VARCHAR(255),
    is_active       INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_ui_content_active ON ui_content (is_active);

INSERT INTO ui_content (content_key, content_value, content_type, label, is_active)
VALUES
    ('home.titulo', 'Olá, Professor(a)! Como posso ajudar na sua próxima aula?', 'text', 'Home — título principal', 1),
    ('home.subtitulo', 'Conte qual desafio você está enfrentando em sala e receba uma metodologia inov-ativa sob medida, com um roteiro pronto para aplicar.', 'text', 'Home — subtítulo', 1),
    ('home.livro_titulo', 'Metodologias inov-ativas na educação', 'text', 'Home — título do livro', 1),
    ('home.livro_descricao', 'As metodologias sugeridas são baseadas nesta obra de Andrea Filatro.', 'text', 'Home — descrição do livro', 1),
    ('resultado.previa_fallback', 'Ao gerar seu roteiro, identificaremos o grupo e a metodologia inov-ativa mais adequados ao seu desafio — com uma justificativa para a sua turma.', 'text', 'Resultado — texto quando prévia indisponível', 1),
    ('resultado.grupo_nota', 'A metodologia específica será definida na geração do seu roteiro, dentro deste grupo da Biblioteca de Metodologias Inov-ativas.', 'text', 'Resultado — nota abaixo do grupo', 1),
    ('exemplo.titulo', 'Veja como a plataforma responde', 'text', 'Exemplo — título', 1),
    ('cadastro.privacidade', 'Usamos seus dados apenas para enviar o roteiro de aulas por e-mail e, se você autorizar, novidades sobre metodologias inov-ativas.', 'text', 'Cadastro — aviso de privacidade', 1),
    ('livro.ecossistema', 'Quero fazer parte do Ecossistema de Metodologias Inov-ativas', 'text', 'Livro — opt-in ecossistema', 1),
    ('livro.titulo', 'Você já conhece o livro Metodologias inov-ativas na educação?', 'text', 'Livro — pergunta principal', 1),
    ('roteiro.email_aviso', 'Enviamos uma cópia do roteiro para o e-mail informado quando o serviço de e-mail estiver ativo.', 'text', 'Roteiro — banner de e-mail', 1),
    ('roteiro.livro_titulo', 'Metodologias inov-ativas na educação.', 'text', 'Roteiro — banner do livro', 1),
    ('brand.aria_label', 'metodologias INOV-ativas na educação', 'text', 'Marca — rótulo acessível', 1),
    ('brand.linha_superior', 'metodologias', 'text', 'Marca — linha superior', 1),
    ('brand.pill', 'INOV-', 'text', 'Marca — destaque INOV-', 1),
    ('brand.sufixo', 'ativas', 'text', 'Marca — sufixo ativas', 1),
    ('brand.linha_inferior', 'na educação', 'text', 'Marca — linha inferior', 1),
    ('assets.capa_livro', '', 'image_url', 'URL da capa do livro (vazio = imagem padrão do app)', 1),
    ('assets.foto_andrea', '', 'image_url', 'URL da foto da autora (vazio = imagem padrão do app)', 1)
ON CONFLICT (content_key) DO NOTHING;
