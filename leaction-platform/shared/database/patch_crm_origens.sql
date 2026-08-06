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
    ('inove4us', 'inove4us', 'Mesa do Inovador (freemium)'),
    ('inove4us-school', 'inove4us School', 'B2B escolar — Editor Pedagógico, AEE/PEI e operação')
ON CONFLICT (slug) DO UPDATE SET
    nome = EXCLUDED.nome,
    descricao = COALESCE(EXCLUDED.descricao, crm_origens.descricao),
    ativo = TRUE,
    atualizado_em = CURRENT_TIMESTAMP;
