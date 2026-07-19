-- PanelDX — Agenda executiva (widget Dashboard + bloco de notas)
-- Idempotente.

CREATE TABLE IF NOT EXISTS public.agenda_eventos (
    id_evento    SERIAL PRIMARY KEY,
    id_matu      INTEGER NOT NULL,
    data_evento  TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    titulo       VARCHAR(200) NOT NULL,
    nota_texto   TEXT,
    criado_em    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_agenda_eventos_matu
        FOREIGN KEY (id_matu) REFERENCES public.ctdi_matu (id_matu) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agenda_eventos_matu_data
    ON public.agenda_eventos (id_matu, data_evento);

COMMENT ON TABLE public.agenda_eventos IS
    'Eventos e notas da agenda executiva do Dashboard (por maturidade/id_matu).';
