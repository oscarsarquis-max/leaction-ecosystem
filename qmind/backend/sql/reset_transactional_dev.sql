-- =============================================================================
-- QMind — reset de dados TRANSACIONAIS (dev / local)
-- =============================================================================
-- APAGA: avaliações, respostas, evidências, constatações, planos, relatórios,
--         maturidade (pacotes), wizard guiado (se existir), jobs e auditoria.
-- MANTÉM: users, memberships, organizations, units, org_processes,
--         standards/requirements (ISO), assessment_models, questions,
--         maturity_models/dimensions/criteria e demais catálogos/seeds.
--
-- Uso (admin no Docker leaction_db):
--   Get-Content sql\reset_transactional_dev.sql -Raw |
--     docker exec -i leaction_db psql -U admin -d qmind_dev -v ON_ERROR_STOP=1
--
-- Ou:
--   .\scripts\reset-transactional-dev.ps1
-- =============================================================================

BEGIN;

DO $$
DECLARE
  candidates text[] := ARRAY[
    'guided_answers',
    'guided_sessions',
    'ai_suggestions',
    'jobs',
    'reports',
    'action_items',
    'action_plans',
    'maturity_score_evidence_links',
    'maturity_dimension_scores',
    'maturity_scores',
    'maturity_assessments',
    'finding_evidences',
    'finding_requirements',
    'findings',
    'evidence_links',
    'evidences',
    'answers',
    'interviews',
    'assessment_team_members',
    'assessment_scopes',
    'assessments',
    'platform_audit_events',
    'break_glass_sessions'
  ];
  existing text[];
  sql text;
BEGIN
  SELECT coalesce(array_agg(format('%I', t) ORDER BY t), ARRAY[]::text[])
  INTO existing
  FROM unnest(candidates) AS t
  WHERE to_regclass(format('public.%I', t)) IS NOT NULL;

  IF coalesce(array_length(existing, 1), 0) = 0 THEN
    RAISE NOTICE 'Nenhuma tabela transacional encontrada — nada a truncar.';
    RETURN;
  END IF;

  -- CASCADE só remove filhas que referenciam as tabelas listadas (não catálogos).
  sql := format(
    'TRUNCATE TABLE %s RESTART IDENTITY CASCADE',
    array_to_string(existing, ', ')
  );
  RAISE NOTICE 'Executando: %', sql;
  EXECUTE sql;
END $$;

COMMIT;

-- Sanity check (transacionais = 0; catálogos/cadastros preservados)
SELECT
  (SELECT count(*) FROM assessments) AS assessments,
  (SELECT count(*) FROM evidences) AS evidences,
  (SELECT count(*) FROM findings) AS findings,
  (SELECT count(*) FROM action_plans) AS action_plans,
  (SELECT count(*) FROM reports) AS reports,
  (SELECT count(*) FROM interviews) AS interviews,
  (SELECT count(*) FROM answers) AS answers,
  (SELECT count(*) FROM platform_audit_events) AS audit_events,
  (SELECT count(*) FROM users) AS users_kept,
  (SELECT count(*) FROM organizations) AS orgs_kept,
  (SELECT count(*) FROM memberships) AS memberships_kept,
  (SELECT count(*) FROM requirements) AS requirements_kept,
  (SELECT count(*) FROM assessment_models) AS assessment_models_kept,
  (SELECT count(*) FROM maturity_criteria) AS maturity_criteria_kept;
