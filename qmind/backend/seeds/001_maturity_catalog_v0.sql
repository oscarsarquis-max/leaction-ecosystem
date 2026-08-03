-- Global catalog seed — Maturity model v0 (domain-docs-v0 / 003_Maturity_Model.md)
-- Idempotent on (model_code, model_version)

INSERT INTO maturity_models (id, model_code, model_version, status, rounding_mode, decimal_places)
VALUES (
  'a1000000-0000-4000-8000-000000000001',
  'qmind_maturity_iso9001',
  '0.1.0',
  'active',
  'half_up',
  2
)
ON CONFLICT (model_code, model_version) DO NOTHING;

WITH dims(code, title, sort_order) AS (
  VALUES
    ('D1_context_leadership', 'Contexto e liderança', 1),
    ('D2_process_risk', 'Processos e riscos', 2),
    ('D3_support', 'Suporte', 3),
    ('D4_operation', 'Operação', 4),
    ('D5_performance', 'Avaliação de desempenho', 5),
    ('D6_improvement', 'Melhoria', 6)
)
INSERT INTO maturity_dimensions (id, maturity_model_id, code, title, sort_order)
SELECT
  gen_random_uuid(),
  'a1000000-0000-4000-8000-000000000001',
  d.code,
  d.title,
  d.sort_order
FROM dims d
WHERE NOT EXISTS (
  SELECT 1 FROM maturity_dimensions md
  WHERE md.maturity_model_id = 'a1000000-0000-4000-8000-000000000001'
    AND md.code = d.code
);

WITH crit(dim_code, code, title, anchor_l3, sort_order) AS (
  VALUES
    ('D1_context_leadership', 'D1.C1', 'Contexto e partes interessadas', 'Registro atualizado usado no planejamento', 1),
    ('D1_context_leadership', 'D1.C2', 'Política e objetivos alinhados', 'Objetivos mensuráveis conhecidos', 2),
    ('D1_context_leadership', 'D1.C3', 'Papéis e autoridade da qualidade', 'Responsabilidades exercidas na prática', 3),
    ('D2_process_risk', 'D2.C1', 'Processos identificados e interativos', 'Mapa/lista vigente com donos', 1),
    ('D2_process_risk', 'D2.C2', 'Riscos e oportunidades tratados', 'Ações de risco rastreadas', 2),
    ('D2_process_risk', 'D2.C3', 'Critérios e controles de processo', 'Controles observados/registrados', 3),
    ('D3_support', 'D3.C1', 'Competência para funções críticas', 'Capacitação/qualificação demonstrada', 1),
    ('D3_support', 'D3.C2', 'Informação documentada controlada', 'Versão vigente disponível e usada', 2),
    ('D3_support', 'D3.C3', 'Comunicação interna eficaz', 'Canais e registros adequados ao risco', 3),
    ('D4_operation', 'D4.C1', 'Planejamento operacional do escopo', 'Planos coerentes com requisitos', 1),
    ('D4_operation', 'D4.C2', 'Controle de mudanças e NC de processo', 'Desvios tratados', 2),
    ('D4_operation', 'D4.C3', 'Controle de fornecedores/externos', 'Avaliação/monitoramento vigentes', 3),
    ('D5_performance', 'D5.C1', 'Indicadores e monitoramento', 'Dados coletados e revisados', 1),
    ('D5_performance', 'D5.C2', 'Auditoria interna / verificação', 'Ciclo planejado e executado', 2),
    ('D5_performance', 'D5.C3', 'Análise crítica pela direção', 'Entradas/saídas tratadas', 3),
    ('D6_improvement', 'D6.C1', 'Tratamento de não conformidades', 'Correção + registro', 1),
    ('D6_improvement', 'D6.C2', 'Ação corretiva com análise de causa', 'Ação proporcional ao impacto', 2),
    ('D6_improvement', 'D6.C3', 'Verificação de eficácia', 'Eficácia confirmada ou retrabalho', 3)
)
INSERT INTO maturity_criteria (id, maturity_dimension_id, code, title, anchor_l3, min_evidence_rule, sort_order)
SELECT
  gen_random_uuid(),
  md.id,
  c.code,
  c.title,
  c.anchor_l3,
  'see 003_Maturity_Model.md §7',
  c.sort_order
FROM crit c
JOIN maturity_dimensions md
  ON md.code = c.dim_code
 AND md.maturity_model_id = 'a1000000-0000-4000-8000-000000000001'
WHERE NOT EXISTS (
  SELECT 1 FROM maturity_criteria mc
  WHERE mc.maturity_dimension_id = md.id AND mc.code = c.code
);
