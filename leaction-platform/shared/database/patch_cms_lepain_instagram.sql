-- BLOG-008 — link do post no Instagram (aditivo e idempotente).
-- Banco: leaction_hub. Uma coluna, nullable. Não reescreve linhas existentes.
-- O valor só entra no destino lepain e só com host do Instagram; isso fica na API.

ALTER TABLE cms_posts ADD COLUMN IF NOT EXISTS instagram_url TEXT;
