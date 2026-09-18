-- 150: mapeamento ENEM e regra de dominio (sem instituicao_id).
-- Catalogo da escola = JOIN com school_disciplinas.

BEGIN;

CREATE OR REPLACE FUNCTION public.enem_norm_disciplina(raw text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT trim(both ' ' FROM regexp_replace(
    lower(translate(
      coalesce(raw, ''),
      'ÁÀÂÃÄáàâãäÉÈÊËéèêëÍÌÎÏíìîïÓÒÔÕÖóòôõöÚÙÛÜúùûüÇç/-',
      'AAAAAaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUUuuuuCc   '
    )),
    '\s+', ' ', 'g'
  ));
$$;

CREATE TABLE IF NOT EXISTS public.enem_disciplina_mapeamento (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disciplina_canonica  TEXT NOT NULL,
    area_codigo          VARCHAR(8) NOT NULL,
    competencia_numero   INTEGER,
    nuance               TEXT,
    origem               VARCHAR(40) NOT NULL DEFAULT 'enem_oficial',
    dataset_versao       TEXT NOT NULL DEFAULT 'enem-oficial-2026.09.1',
    CONSTRAINT ck_enem_map_area
        CHECK (area_codigo IN ('LC', 'MT', 'CN', 'CH', 'RED'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_enem_map_disc_area_comp
    ON public.enem_disciplina_mapeamento (
        disciplina_canonica,
        area_codigo,
        COALESCE(competencia_numero, 0)
    );

CREATE TABLE IF NOT EXISTS public.enem_disciplina_alias (
    alias_norm           TEXT NOT NULL,
    disciplina_canonica  TEXT NOT NULL,
    PRIMARY KEY (alias_norm, disciplina_canonica)
);

CREATE INDEX IF NOT EXISTS idx_enem_map_disc
    ON public.enem_disciplina_mapeamento (disciplina_canonica, area_codigo);

COMMENT ON TABLE public.enem_disciplina_mapeamento IS
  'Regra de dominio: disciplina canonica do EM -> area/competencia oficial do ENEM. Sem escola.';
COMMENT ON TABLE public.enem_disciplina_alias IS
  'Nomes que a escola pode ter cadastrado (Portugues, Lingua Portuguesa, Portugues/Redacao).';

DROP VIEW IF EXISTS public.school_enem_habilidades_canonico;
DROP TABLE IF EXISTS public.school_enem_habilidades_canonico;

CREATE OR REPLACE VIEW public.school_enem_habilidades_canonico AS
SELECT
    d.instituicao_id,
    d.id AS disciplina_id,
    d.nome AS disciplina_nome,
    a.disciplina_canonica,
    m.area_codigo,
    h.codigo AS habilidade_codigo,
    NULL::text AS redacao_codigo,
    h.competencia_numero,
    h.texto AS rotulo,
    (m.area_codigo || '-C' || COALESCE(m.competencia_numero::text, 'all')) AS mapeamento_regra,
    m.nuance,
    'enem_oficial'::varchar(40) AS origem,
    'aprovado'::varchar(32) AS status,
    h.fonte_proveniencia,
    h.dataset_versao
  FROM public.school_disciplinas d
  JOIN public.enem_disciplina_alias a
    ON a.alias_norm = public.enem_norm_disciplina(d.nome)
  JOIN public.enem_disciplina_mapeamento m
    ON m.disciplina_canonica = a.disciplina_canonica
   AND m.area_codigo <> 'RED'
  JOIN public.enem_habilidades_oficial h
    ON h.area_codigo = m.area_codigo
   AND (m.competencia_numero IS NULL OR h.competencia_numero = m.competencia_numero)
 WHERE d.ativo IS TRUE
UNION ALL
SELECT
    d.instituicao_id,
    d.id AS disciplina_id,
    d.nome AS disciplina_nome,
    a.disciplina_canonica,
    'RED'::varchar(8) AS area_codigo,
    NULL::text AS habilidade_codigo,
    r.codigo AS redacao_codigo,
    r.competencia_numero,
    r.texto AS rotulo,
    'RED-cartilha-2025'::text AS mapeamento_regra,
    m.nuance,
    'enem_oficial'::varchar(40) AS origem,
    'aprovado'::varchar(32) AS status,
    r.fonte_proveniencia,
    r.dataset_versao
  FROM public.school_disciplinas d
  JOIN public.enem_disciplina_alias a
    ON a.alias_norm = public.enem_norm_disciplina(d.nome)
  JOIN public.enem_disciplina_mapeamento m
    ON m.disciplina_canonica = a.disciplina_canonica
   AND m.area_codigo = 'RED'
  JOIN public.enem_redacao_competencias_oficial r ON TRUE
 WHERE d.ativo IS TRUE;

COMMENT ON VIEW public.school_enem_habilidades_canonico IS
  'Intersecao ao vivo: disciplinas da escola x mapeamento generico x tabelas oficiais do 147.';

COMMIT;
