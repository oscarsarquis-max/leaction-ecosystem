-- Global catalog stub — Standard ISO 9001:2015 (authorized references only; no normative text)
-- + minimal AssessmentModel for FK targets in tests / MVP

INSERT INTO standards (id, code, title, status)
VALUES (
  'b1000000-0000-4000-8000-000000000001',
  'ISO9001',
  'ISO 9001 Quality management systems',
  'active'
)
ON CONFLICT (code) DO NOTHING;

INSERT INTO standard_versions (id, standard_id, version_label, status, effective_from)
VALUES (
  'b1000000-0000-4000-8000-000000000002',
  'b1000000-0000-4000-8000-000000000001',
  '2015',
  'active',
  '2015-09-15'
)
ON CONFLICT (standard_id, version_label) DO NOTHING;

INSERT INTO requirements (id, standard_version_id, code, title_authorized, sort_order, status)
VALUES
  ('b1000000-0000-4000-8000-000000000010', 'b1000000-0000-4000-8000-000000000002', '4', 'Context of the organization (ref)', 40, 'active'),
  ('b1000000-0000-4000-8000-000000000011', 'b1000000-0000-4000-8000-000000000002', '5', 'Leadership (ref)', 50, 'active'),
  ('b1000000-0000-4000-8000-000000000012', 'b1000000-0000-4000-8000-000000000002', '6', 'Planning (ref)', 60, 'active')
ON CONFLICT (standard_version_id, code) DO NOTHING;

INSERT INTO assessment_models (id, code, version_label, title, status)
VALUES (
  'c1000000-0000-4000-8000-000000000001',
  'qmind_iso9001_diag',
  '0.1.0',
  'QMind ISO 9001 diagnosis model (stub)',
  'active'
)
ON CONFLICT (code, version_label) DO NOTHING;

INSERT INTO assessment_model_requirements (assessment_model_id, requirement_id)
VALUES
  ('c1000000-0000-4000-8000-000000000001', 'b1000000-0000-4000-8000-000000000010'),
  ('c1000000-0000-4000-8000-000000000001', 'b1000000-0000-4000-8000-000000000011'),
  ('c1000000-0000-4000-8000-000000000001', 'b1000000-0000-4000-8000-000000000012')
ON CONFLICT DO NOTHING;
