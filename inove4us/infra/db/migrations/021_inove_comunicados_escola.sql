-- Mural de Comunicações da Escola (School → B2C).
-- Numeração: 021 (020 = PEI Kanban subcards).
--
-- Sem FK cross-DB com inove4us_school: origem_comunicado_school_id é só id lógico.
-- Reflexo na agenda: inove_agenda_eventos.origem = 'comunicado_escola' (+ tipo geral).
-- Grafo deve filtrar origem <> 'comunicado_escola' (não é trilha pedagógica).

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) Comunicados recebidos do School
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.inove_comunicados_escola (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    origem_comunicado_school_id UUID NOT NULL,
    instituicao_escola_id       UUID,
    titulo                      TEXT NOT NULL,
    descricao                   TEXT,
    tipo                        TEXT NOT NULL,
    data_hora_inicio            TIMESTAMPTZ,
    data_hora_fim               TIMESTAMPTZ,
    status                      TEXT NOT NULL DEFAULT 'ativo',
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inove_comunicados_origem_school
        UNIQUE (origem_comunicado_school_id),
    CONSTRAINT chk_inove_comunicados_tipo
        CHECK (tipo IN ('reuniao_pedagogica', 'evento_escolar')),
    CONSTRAINT chk_inove_comunicados_status
        CHECK (status IN ('ativo', 'cancelado'))
);

CREATE INDEX IF NOT EXISTS idx_inove_comunicados_inicio
    ON public.inove_comunicados_escola (data_hora_inicio DESC NULLS LAST);

COMMENT ON TABLE public.inove_comunicados_escola IS
  'Comunicados empurrados pelo inove4us School (S2S). Upsert por origem_comunicado_school_id.';
COMMENT ON COLUMN public.inove_comunicados_escola.origem_comunicado_school_id IS
  'UUID de school_comunicacoes_eventos.id — referência lógica, sem FK cross-DB.';

-- Destinatários (1 linha por professor) + ciência + vínculo com evento da agenda
CREATE TABLE IF NOT EXISTS public.inove_comunicados_escola_destinatarios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comunicado_id   UUID NOT NULL
        REFERENCES public.inove_comunicados_escola (id) ON DELETE CASCADE,
    id_clie         INTEGER NOT NULL
        REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
    agenda_evento_id INTEGER
        REFERENCES public.inove_agenda_eventos (id_evento) ON DELETE SET NULL,
    lido_em         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inove_comunicados_dest_prof
        UNIQUE (comunicado_id, id_clie)
);

CREATE INDEX IF NOT EXISTS idx_inove_comunicados_dest_clie
    ON public.inove_comunicados_escola_destinatarios (id_clie, comunicado_id);

COMMENT ON TABLE public.inove_comunicados_escola_destinatarios IS
  'Fan-out do comunicado por professor (id_clie). lido_em = ciência no mural.';

-- ---------------------------------------------------------------------------
-- 2) Agenda: origem comunicado_escola + FK lógica ao comunicado
-- ---------------------------------------------------------------------------
ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS comunicado_escola_id UUID
        REFERENCES public.inove_comunicados_escola (id) ON DELETE SET NULL;

ALTER TABLE public.inove_agenda_eventos
    DROP CONSTRAINT IF EXISTS chk_inove_agenda_eventos_origem;

ALTER TABLE public.inove_agenda_eventos
    ADD CONSTRAINT chk_inove_agenda_eventos_origem
        CHECK (origem IN ('manual', 'wizard_ia', 'importacao', 'comunicado_escola'));

CREATE INDEX IF NOT EXISTS idx_inove_agenda_comunicado_escola
    ON public.inove_agenda_eventos (comunicado_escola_id)
    WHERE comunicado_escola_id IS NOT NULL;

COMMENT ON COLUMN public.inove_agenda_eventos.origem IS
  'manual | wizard_ia | importacao | comunicado_escola (somente leitura no FE).';
COMMENT ON COLUMN public.inove_agenda_eventos.comunicado_escola_id IS
  'Quando origem=comunicado_escola, aponta para inove_comunicados_escola.';

COMMIT;
