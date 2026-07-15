-- Catálogo de origens do Action-Sponge (sistemas que enviam tracking)
-- Banco: leaction_hub

CREATE TABLE IF NOT EXISTS crm_origens (
    slug VARCHAR(64) PRIMARY KEY,
    nome VARCHAR(160) NOT NULL,
    descricao TEXT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO crm_origens (slug, nome, descricao)
VALUES
    ('paneldx', 'PanelDX', 'Transformação Digital Educacional'),
    ('inove4us', 'inove4us', 'Mesa do Inovador (freemium)')
ON CONFLICT (slug) DO NOTHING;
