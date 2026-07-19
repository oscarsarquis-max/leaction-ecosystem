-- eSIM agnóstico a fornecedores: provedores, catálogo em banco, renomeação de tabelas
-- Executar após 007/008_basemobile_*.sql (ou em base já migrada).

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Provedores eSIM
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.esim_provedores (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(120) NOT NULL UNIQUE,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em   TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 2. Catálogo de eventos (mapeamento operadora → Framework LeAction)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.esim_eventos_catalog (
    id                SERIAL PRIMARY KEY,
    codigo_evento     VARCHAR(64) NOT NULL UNIQUE,
    descricao_tecnica TEXT NOT NULL,
    dimensao_fixada   VARCHAR(255) NOT NULL,
    dominio_fixado    VARCHAR(255) NOT NULL,
    blocos_candidatos JSONB NOT NULL DEFAULT '[]'::jsonb,
    provedor_id       INTEGER NOT NULL REFERENCES public.esim_provedores(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_esim_eventos_catalog_provedor
    ON public.esim_eventos_catalog (provedor_id);

-- Provedor padrão (migração do contrato Base Mobile)
INSERT INTO public.esim_provedores (id, nome, config_json)
VALUES (
    1,
    'Base Mobile',
    '{"webhook_path": "/api/webhooks/basemobile", "slug": "basemobile"}'::jsonb
)
ON CONFLICT (nome) DO UPDATE
SET config_json = EXCLUDED.config_json;

SELECT setval(
    pg_get_serial_sequence('public.esim_provedores', 'id'),
    GREATEST((SELECT COALESCE(MAX(id), 1) FROM public.esim_provedores), 1)
);

-- Catálogo inicial (equivalente ao EVENT_LEACTION_CATALOG legado)
INSERT INTO public.esim_eventos_catalog
    (codigo_evento, descricao_tecnica, dimensao_fixada, dominio_fixado, blocos_candidatos, provedor_id)
VALUES
(
    'QDA_ACESSO_PEDAG',
    'Queda de conectividade ou tráfego no acesso a plataformas de aprendizagem (LMS/LXP). Impacto direto na dimensão LA — risco de interrupção da jornada do aprendiz e perda de engajamento digital.',
    'Aprendizagem em Ação (LA)',
    'Plataformas Digitais (dp)',
    '["Portal de Integração dos Aprendizes", "Ambientes AVA/LMS", "Programas Híbridos"]'::jsonb,
    1
),
(
    'GARGALO_ADMN_SEC',
    'Anomalia associada a autenticação, governança de acesso ou políticas de segurança. Impacto na dimensão DA — risco operacional, conformidade (LGPD) e continuidade dos serviços críticos.',
    'Arquitetura Digital (DA)',
    'Governança Digital (dg)',
    '["Segurança e Redundância", "Identidade e Autenticação", "Privacidade"]'::jsonb,
    1
),
(
    'LENTIDAO_TI_SIST',
    'Degradação de performance ou latência em sistemas corporativos. Impacto na dimensão DA — dívida técnica, conectividade e arquitetura de plataformas digitais.',
    'Arquitetura Digital (DA)',
    'Plataformas Digitais (dp)',
    '["Conectividade e Nuvem", "Mapa de Tecnologia", "Interoperabilidade"]'::jsonb,
    1
)
ON CONFLICT (codigo_evento) DO UPDATE
SET descricao_tecnica = EXCLUDED.descricao_tecnica,
    dimensao_fixada = EXCLUDED.dimensao_fixada,
    dominio_fixado = EXCLUDED.dominio_fixado,
    blocos_candidatos = EXCLUDED.blocos_candidatos,
    provedor_id = EXCLUDED.provedor_id;

-- ---------------------------------------------------------------------------
-- 3. Renomear tabelas legadas (preserva dados)
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'basemobile_eventos'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'esim_eventos'
    ) THEN
        ALTER TABLE public.basemobile_eventos RENAME TO esim_eventos;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'basemobile_mesa_backlog'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'esim_mesa_backlog'
    ) THEN
        ALTER TABLE public.basemobile_mesa_backlog RENAME TO esim_mesa_backlog;
    END IF;
END $$;

-- Instalação limpa (sem tabelas basemobile_*)
CREATE TABLE IF NOT EXISTS public.esim_eventos (
    id_evento          SERIAL PRIMARY KEY,
    id_clie            INTEGER NOT NULL REFERENCES public.ctdi_clie(id_clie) ON DELETE CASCADE,
    catalog_id         INTEGER REFERENCES public.esim_eventos_catalog(id) ON DELETE RESTRICT,
    grupo_acesso       VARCHAR(120),
    dominio_acessado   VARCHAR(255),
    trafego_mb_7dias  NUMERIC(12, 2),
    status_anomalia    VARCHAR(64) NOT NULL,
    dominio_associado  VARCHAR(255),
    bloco_associado    VARCHAR(255),
    payload_bruto      JSONB,
    recebido_em        TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.esim_mesa_backlog (
    id_item             SERIAL PRIMARY KEY,
    id_evento           INTEGER NOT NULL REFERENCES public.esim_eventos(id_evento) ON DELETE CASCADE,
    id_clie             INTEGER NOT NULL REFERENCES public.ctdi_clie(id_clie) ON DELETE CASCADE,
    id_matu             INTEGER,
    origem              VARCHAR(32) NOT NULL DEFAULT 'telemetria',
    is_alerta           BOOLEAN NOT NULL DEFAULT TRUE,
    status              VARCHAR(32) NOT NULL DEFAULT 'pendente',
    hipotese_negocio    TEXT,
    subtasks            JSONB,
    ia_resposta         JSONB,
    dominio_associado   VARCHAR(255),
    bloco_associado     VARCHAR(255),
    id_nota_mesa        INTEGER REFERENCES public.inov_agenda_notas(id_nota) ON DELETE SET NULL,
    criado_em           TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    consumido_em        TIMESTAMP WITHOUT TIME ZONE
);

-- FK catalog_id em bases renomeadas ou já existentes
ALTER TABLE public.esim_eventos
    ADD COLUMN IF NOT EXISTS catalog_id INTEGER REFERENCES public.esim_eventos_catalog(id) ON DELETE RESTRICT;

-- Backfill catalog_id a partir do payload bruto
UPDATE public.esim_eventos e
SET catalog_id = c.id
FROM public.esim_eventos_catalog c
WHERE e.catalog_id IS NULL
  AND UPPER(
        COALESCE(
            e.payload_bruto->>'codigo_evento',
            e.payload_bruto->>'codigo_evento_padrao',
            ''
        )
      ) = c.codigo_evento;

-- Índices (nomes novos; legados basemobile_* permanecem se já existirem)
CREATE INDEX IF NOT EXISTS idx_esim_eventos_clie
    ON public.esim_eventos (id_clie, recebido_em DESC);

CREATE INDEX IF NOT EXISTS idx_esim_eventos_anomalia
    ON public.esim_eventos (status_anomalia);

CREATE INDEX IF NOT EXISTS idx_esim_eventos_catalog
    ON public.esim_eventos (catalog_id)
    WHERE catalog_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_esim_eventos_bloco
    ON public.esim_eventos (bloco_associado)
    WHERE bloco_associado IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_esim_mesa_backlog_clie
    ON public.esim_mesa_backlog (id_clie, status, criado_em DESC);

CREATE INDEX IF NOT EXISTS idx_esim_mesa_backlog_pendentes
    ON public.esim_mesa_backlog (id_clie, id_matu)
    WHERE status = 'pendente';

CREATE INDEX IF NOT EXISTS idx_esim_mesa_backlog_bloco
    ON public.esim_mesa_backlog (id_clie, bloco_associado)
    WHERE bloco_associado IS NOT NULL;

COMMIT;
