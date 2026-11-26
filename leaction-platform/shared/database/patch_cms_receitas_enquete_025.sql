-- BLOG-025 — receitas dos leitores + campos de enquete lúdica.
-- Aditivo e idempotente. Banco: leaction_hub.

-- Seção e Right Now: receita
ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS chk_cms_posts_secao;
ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_secao CHECK (
    secao IS NULL OR secao IN ('insights', 'right_now', 'receita')
);

ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS chk_cms_posts_right_now_tipo;
ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_right_now_tipo CHECK (
    right_now_tipo IS NULL
    OR right_now_tipo IN ('promocao', 'evento', 'noticia', 'curiosidade', 'parceiro', 'receita')
);

ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS autor_nome TEXT;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS autor_cidade TEXT;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS autor_instagram TEXT;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS ingredientes TEXT;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS preparo TEXT;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS historia TEXT;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS dica TEXT;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS tempo TEXT;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS rendimento TEXT;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS nivel TEXT;

CREATE TABLE IF NOT EXISTS cms_receitas (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    cidade TEXT NOT NULL,
    instagram TEXT,
    telefone TEXT,
    titulo TEXT NOT NULL,
    historia TEXT NOT NULL,
    ingredientes TEXT NOT NULL,
    preparo TEXT NOT NULL,
    foto_url TEXT,
    idioma VARCHAR(2) NOT NULL DEFAULT 'pt',
    consentimento BOOLEAN NOT NULL DEFAULT false,
    consentimento_em TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'recebida',
    cliente_loja BOOLEAN NOT NULL DEFAULT false,
    ponto_creditado_em TIMESTAMPTZ,
    revisao JSONB,
    post_grupo_id INTEGER REFERENCES cms_posts (id) ON DELETE SET NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    decidido_em TIMESTAMPTZ,
    telefone_apagado_em TIMESTAMPTZ,
    CONSTRAINT chk_cms_receitas_status CHECK (status IN ('recebida', 'publicada', 'recusada')),
    CONSTRAINT chk_cms_receitas_idioma CHECK (idioma IN ('pt', 'en'))
);

CREATE INDEX IF NOT EXISTS ix_cms_receitas_status_criado
    ON cms_receitas (status, criado_em DESC);

CREATE INDEX IF NOT EXISTS ix_cms_receitas_telefone_purge
    ON cms_receitas (decidido_em)
    WHERE telefone IS NOT NULL AND status IN ('publicada', 'recusada');

-- Enquete: status sugerida/encerrada
ALTER TABLE cms_enquetes DROP CONSTRAINT IF EXISTS chk_cms_enquetes_status;
ALTER TABLE cms_enquetes ADD CONSTRAINT chk_cms_enquetes_status CHECK (
    status IN ('rascunho', 'publicada', 'sugerida', 'encerrada')
);

ALTER TABLE cms_enquetes ADD COLUMN IF NOT EXISTS fornada_post_id INTEGER REFERENCES cms_posts (id) ON DELETE SET NULL;
ALTER TABLE cms_enquetes ADD COLUMN IF NOT EXISTS encerrada_em TIMESTAMPTZ;
