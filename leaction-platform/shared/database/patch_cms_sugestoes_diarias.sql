-- BLOG-024 — Sugestões diárias Right Now. Aditivo e idempotente.
-- Banco: leaction_hub. Não apaga linha.

ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS trecho_base TEXT;
ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS data_materia DATE;

ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS chk_cms_posts_trecho_base;
ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_trecho_base CHECK (
    trecho_base IS NULL OR char_length(trecho_base) <= 200
);
