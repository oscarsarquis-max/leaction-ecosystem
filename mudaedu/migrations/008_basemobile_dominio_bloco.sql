-- Base Mobile: vínculo Framework LeAction (domínio + bloco CTDI) para consumo Kanban
-- Executar uma vez após 007_basemobile_telemetry.sql

ALTER TABLE public.basemobile_eventos
    ADD COLUMN IF NOT EXISTS dominio_associado VARCHAR(255);

ALTER TABLE public.basemobile_eventos
    ADD COLUMN IF NOT EXISTS bloco_associado VARCHAR(255);

ALTER TABLE public.basemobile_mesa_backlog
    ADD COLUMN IF NOT EXISTS dominio_associado VARCHAR(255);

ALTER TABLE public.basemobile_mesa_backlog
    ADD COLUMN IF NOT EXISTS bloco_associado VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_basemobile_eventos_bloco
    ON public.basemobile_eventos (bloco_associado)
    WHERE bloco_associado IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_basemobile_mesa_backlog_bloco
    ON public.basemobile_mesa_backlog (id_clie, bloco_associado)
    WHERE bloco_associado IS NOT NULL;
