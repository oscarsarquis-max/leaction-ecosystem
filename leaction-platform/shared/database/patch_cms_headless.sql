-- Headless CMS — conteúdo editorial distribuído aos satélites
-- Banco: leaction_hub

CREATE TABLE IF NOT EXISTS cms_posts (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(255) NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    resumo TEXT NULL,
    conteudo_html TEXT NULL,
    imagem_capa VARCHAR(255) NULL,
    sistema_destino VARCHAR(50) NOT NULL DEFAULT 'todos',
    status VARCHAR(20) NOT NULL DEFAULT 'rascunho',
    publicado_em TIMESTAMPTZ NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cms_posts_slug UNIQUE (slug),
    CONSTRAINT chk_cms_posts_status CHECK (status IN ('rascunho', 'publicado')),
    CONSTRAINT chk_cms_posts_destino CHECK (
        sistema_destino IN (
            'hub-publico',
            'actionhub',
            'inove4us',
            'paneldx',
            'todos'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_cms_posts_sistema_destino
    ON cms_posts (sistema_destino);

CREATE INDEX IF NOT EXISTS idx_cms_posts_status
    ON cms_posts (status);

CREATE INDEX IF NOT EXISTS idx_cms_posts_status_publicado
    ON cms_posts (status, publicado_em DESC NULLS LAST);
