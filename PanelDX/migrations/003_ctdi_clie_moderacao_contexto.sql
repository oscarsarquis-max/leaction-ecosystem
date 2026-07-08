-- Sugestões do Agente Moderador por campo de contexto (consumo posterior pela IA)
ALTER TABLE public.ctdi_clie
    ADD COLUMN IF NOT EXISTS moderacao_dados_mercado          TEXT,
    ADD COLUMN IF NOT EXISTS moderacao_dados_etnograficos     TEXT,
    ADD COLUMN IF NOT EXISTS moderacao_clima_organizacional   TEXT;
