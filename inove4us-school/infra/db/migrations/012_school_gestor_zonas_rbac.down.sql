BEGIN;

DROP TABLE IF EXISTS public.school_gestor_perfis CASCADE;

ALTER TABLE public.school_gestores
    DROP CONSTRAINT IF EXISTS chk_school_gestores_cargo;

ALTER TABLE public.school_gestores
    ADD CONSTRAINT chk_school_gestores_cargo
        CHECK (cargo IN ('Diretor', 'Coordenador'));

COMMENT ON TABLE public.school_gestores IS
  'Usuários B2B (Diretor/Coordenador). Autenticação própria — não compartilha sessão com o app dos professores.';
COMMENT ON COLUMN public.school_gestores.cargo IS NULL;

COMMIT;
