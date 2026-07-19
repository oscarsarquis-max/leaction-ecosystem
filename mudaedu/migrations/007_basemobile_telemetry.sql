-- Backlog separado: telemetria Base Mobile (eSIM) → alertas preditivos para Mesa Org
-- Executar uma vez no PostgreSQL de produção/staging.

CREATE TABLE IF NOT EXISTS public.basemobile_eventos (
    id_evento       SERIAL PRIMARY KEY,
    id_clie         INTEGER NOT NULL REFERENCES public.ctdi_clie(id_clie) ON DELETE CASCADE,
    grupo_acesso    VARCHAR(120),
    dominio_acessado VARCHAR(255),
    trafego_mb_7dias NUMERIC(12, 2),
    status_anomalia VARCHAR(64) NOT NULL,
    payload_bruto   JSONB,
    recebido_em     TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_basemobile_eventos_clie
    ON public.basemobile_eventos (id_clie, recebido_em DESC);

CREATE INDEX IF NOT EXISTS idx_basemobile_eventos_anomalia
    ON public.basemobile_eventos (status_anomalia);

CREATE TABLE IF NOT EXISTS public.basemobile_mesa_backlog (
    id_item             SERIAL PRIMARY KEY,
    id_evento           INTEGER NOT NULL REFERENCES public.basemobile_eventos(id_evento) ON DELETE CASCADE,
    id_clie             INTEGER NOT NULL REFERENCES public.ctdi_clie(id_clie) ON DELETE CASCADE,
    id_matu             INTEGER,
    origem              VARCHAR(32) NOT NULL DEFAULT 'telemetria',
    is_alerta           BOOLEAN NOT NULL DEFAULT TRUE,
    status              VARCHAR(32) NOT NULL DEFAULT 'pendente',
    hipotese_negocio    TEXT,
    subtasks            JSONB,
    ia_resposta         JSONB,
    id_nota_mesa        INTEGER REFERENCES public.inov_agenda_notas(id_nota) ON DELETE SET NULL,
    criado_em           TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    consumido_em        TIMESTAMP WITHOUT TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_basemobile_mesa_backlog_clie
    ON public.basemobile_mesa_backlog (id_clie, status, criado_em DESC);

CREATE INDEX IF NOT EXISTS idx_basemobile_mesa_backlog_pendentes
    ON public.basemobile_mesa_backlog (id_clie, id_matu)
    WHERE status = 'pendente';
