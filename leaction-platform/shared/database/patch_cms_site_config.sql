-- Micro-CMS PanelDX migrado para o Action Hub (leaction_hub)
-- Estrutura equivalente a PanelDX public.ctdi_cms_config

CREATE TABLE IF NOT EXISTS cms_site_config (
    id_cms              SERIAL PRIMARY KEY,
    config_key          VARCHAR(50) NOT NULL DEFAULT 'default',
    landing_page_data   JSONB NOT NULL DEFAULT '{}'::jsonb,
    instructions_data   TEXT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cms_site_config_key UNIQUE (config_key)
);

-- Posts: URLs S3 podem ultrapassar 255 chars
ALTER TABLE cms_posts
  ALTER COLUMN imagem_capa TYPE TEXT;
