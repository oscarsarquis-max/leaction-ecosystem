-- inove4us School — Etapa 11: zonas de acesso (RBAC).
-- Numeração: 012 (011 = plano geral de PEI).
--
-- Modelo: 1 login, N zonas por gestor via school_gestor_perfis.
-- Zonas: administrativo | operacional | pedagogico.
-- cargo em school_gestores vira título de exibição (CHECK ampliado);
-- o controle de acesso passa a ser school_gestor_perfis (Etapa 12 liga o login).
--
-- Escolha de cargo: CHECK ampliado (Diretor, Coordenador, Secretaria,
-- Neuropedagoga, Outro) — mantém domínio fechado sem exigir taxonomia
-- de autorização no título; zonas ficam só em school_gestor_perfis.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) cargo: título de exibição (CHECK ampliado, sem quebrar Diretor/Coordenador)
-- ---------------------------------------------------------------------------
ALTER TABLE public.school_gestores
    DROP CONSTRAINT IF EXISTS chk_school_gestores_cargo;

ALTER TABLE public.school_gestores
    ADD CONSTRAINT chk_school_gestores_cargo
        CHECK (cargo IN (
            'Diretor',
            'Coordenador',
            'Secretaria',
            'Neuropedagoga',
            'Outro'
        ));

COMMENT ON TABLE public.school_gestores IS
  'Usuários B2B da Torre de Controle. cargo = título de exibição; zonas de acesso em school_gestor_perfis.';
COMMENT ON COLUMN public.school_gestores.cargo IS
  'Título de exibição (Diretor, Coordenador, Secretaria, Neuropedagoga, Outro). Não autoriza sozinho — use school_gestor_perfis.';

-- ---------------------------------------------------------------------------
-- 2) Zonas de acesso (RBAC) — um gestor pode acumular várias zonas
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_gestor_perfis (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gestor_id   UUID NOT NULL
        REFERENCES public.school_gestores (id) ON DELETE CASCADE,
    zona        TEXT NOT NULL,
    ativo       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_school_gestor_perfis_zona
        CHECK (zona IN ('administrativo', 'operacional', 'pedagogico')),
    CONSTRAINT uq_school_gestor_perfis_gestor_zona
        UNIQUE (gestor_id, zona)
);

CREATE INDEX IF NOT EXISTS idx_school_gestor_perfis_gestor
    ON public.school_gestor_perfis (gestor_id);

CREATE INDEX IF NOT EXISTS idx_school_gestor_perfis_zona
    ON public.school_gestor_perfis (zona)
    WHERE ativo = TRUE;

COMMENT ON TABLE public.school_gestor_perfis IS
  'Zonas RBAC do gestor (1 login, N zonas). Zero linhas = sem zona (sem acesso na Etapa 12).';
COMMENT ON COLUMN public.school_gestor_perfis.zona IS
  'administrativo (licenças/equipe) | operacional (secretaria) | pedagogico (Editor/dashboard).';

COMMIT;
