-- inove4us School — e-mail de convite no vínculo do professor (Equipe).
-- Numeração: 014 (013 = comunicações + licenças).
--
-- Convite é por e-mail; professor_b2c_id continua como ponte lógica ao B2C
-- (UUID provisório derivado do e-mail até o aceite real).

BEGIN;

ALTER TABLE public.school_professores_vinculo
    ADD COLUMN IF NOT EXISTS email_convite TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_school_prof_vinculo_inst_email
    ON public.school_professores_vinculo (instituicao_id, lower(email_convite))
    WHERE email_convite IS NOT NULL;

COMMENT ON COLUMN public.school_professores_vinculo.email_convite IS
  'E-mail usado no convite (Equipe). Obrigatório para novos convites.';

COMMIT;
