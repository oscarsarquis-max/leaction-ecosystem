-- Migração 003: chave de imagem do logotipo na interface
INSERT INTO ui_content (content_key, content_value, content_type, label, is_active)
VALUES
    ('assets.logo', '', 'image_url', 'URL do logotipo (vazio = arquivo em /brand/logo.png)', 1)
ON CONFLICT (content_key) DO NOTHING;
