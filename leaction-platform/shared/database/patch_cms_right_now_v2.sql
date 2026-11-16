-- BLOG-022 — Right Now v2. Aditivo e idempotente.
-- Banco: leaction_hub. Não apaga linha nem reação.

ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS chk_cms_posts_right_now_tipo;
ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_right_now_tipo CHECK (
    right_now_tipo IS NULL
    OR right_now_tipo IN ('promocao', 'evento', 'noticia', 'curiosidade', 'parceiro')
);

ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS chk_cms_posts_status;
ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_status CHECK (
    status IN ('rascunho', 'publicado', 'sugestao', 'descartado')
);

ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS link_url TEXT;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS fonte TEXT;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS origem TEXT;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS sugestao_expira_em TIMESTAMPTZ;

UPDATE cms_posts SET origem = 'manual' WHERE origem IS NULL;
ALTER TABLE cms_posts ALTER COLUMN origem SET DEFAULT 'manual';
ALTER TABLE cms_posts ALTER COLUMN origem SET NOT NULL;

ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS chk_cms_posts_origem;
ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_origem CHECK (
    origem IN ('manual', 'auto')
);

ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS chk_cms_posts_link_url;
ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_link_url CHECK (
    link_url IS NULL OR link_url ~ '^https?://[^[:space:]]+$'
);

ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS chk_cms_posts_fonte;
ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_fonte CHECK (
    fonte IS NULL OR char_length(fonte) <= 80
);

CREATE TABLE IF NOT EXISTS cms_reacoes (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES cms_posts (id) ON DELETE CASCADE,
    visitante CHAR(64) NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_cms_reacoes_post_visitante UNIQUE (post_id, visitante)
);

CREATE TABLE IF NOT EXISTS cms_enquetes (
    id SERIAL PRIMARY KEY,
    pergunta_pt TEXT NOT NULL,
    pergunta_en TEXT NOT NULL,
    opcoes JSONB NOT NULL,
    abre_em TIMESTAMPTZ NOT NULL,
    fecha_em TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'rascunho',
    CONSTRAINT chk_cms_enquetes_status CHECK (status IN ('rascunho', 'publicada'))
);

CREATE TABLE IF NOT EXISTS cms_votos (
    id SERIAL PRIMARY KEY,
    enquete_id INTEGER NOT NULL REFERENCES cms_enquetes (id) ON DELETE CASCADE,
    opcao_id TEXT NOT NULL,
    visitante CHAR(64) NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_cms_votos_enquete_visitante UNIQUE (enquete_id, visitante)
);
