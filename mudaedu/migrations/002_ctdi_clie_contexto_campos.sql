-- Migração: campos de contexto institucional para experiência de boas-vindas (PanelDX)
-- Nenhuma coluna existente é alterada ou removida.

ALTER TABLE public.ctdi_clie
    ADD COLUMN IF NOT EXISTS bairro_clie       VARCHAR(120),
    ADD COLUMN IF NOT EXISTS cidade_clie       VARCHAR(120),
    ADD COLUMN IF NOT EXISTS estado_clie       VARCHAR(2),
    ADD COLUMN IF NOT EXISTS dados_etnograficos TEXT,
    ADD COLUMN IF NOT EXISTS dados_mercado     TEXT;
