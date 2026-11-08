-- BLOG-003 — destino LePain no CMS (aditivo e idempotente).
-- Banco: leaction_hub. Não reescreve linhas existentes.
-- atualizado_em entra sem DEFAULT na mesma sentença de ADD COLUMN:
-- now() é volátil e, num único ADD, preencheria as linhas antigas.
-- O DEFAULT vale só para INSERT novo; o que já existe fica NULL até um PUT.

ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS chk_cms_posts_destino;
ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_destino CHECK (
    sistema_destino IN (
        'hub-publico',
        'actionhub',
        'inove4us',
        'paneldx',
        'todos',
        'lepain'
    )
);

ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS secao VARCHAR(20);
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS idioma VARCHAR(2);
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS grupo_id INTEGER;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS sentidos TEXT[];
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS resumo_instagram TEXT;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS right_now_tipo VARCHAR(20);
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS data_evento DATE;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS valido_ate DATE;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ;
ALTER TABLE cms_posts ALTER COLUMN atualizado_em SET DEFAULT now();

ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS chk_cms_posts_secao;
ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_secao CHECK (
    secao IS NULL OR secao IN ('insights', 'right_now')
);

ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS chk_cms_posts_idioma;
ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_idioma CHECK (
    idioma IS NULL OR idioma IN ('pt', 'en')
);

ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS chk_cms_posts_right_now_tipo;
ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_right_now_tipo CHECK (
    right_now_tipo IS NULL OR right_now_tipo IN ('promocao', 'evento', 'noticia')
);

ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS chk_cms_posts_sentidos;
ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_sentidos CHECK (
    sentidos IS NULL OR (
        cardinality(sentidos) > 0
        AND sentidos <@ ARRAY['olhar', 'toque', 'aroma', 'sabor', 'som', 'memoria']::text[]
    )
);

ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS fk_cms_posts_grupo;
ALTER TABLE cms_posts
    ADD CONSTRAINT fk_cms_posts_grupo
    FOREIGN KEY (grupo_id) REFERENCES cms_posts (id) ON DELETE SET NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_cms_posts_grupo_idioma
    ON cms_posts (grupo_id, idioma)
    WHERE grupo_id IS NOT NULL;
