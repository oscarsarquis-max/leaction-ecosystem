-- Crystal Ball — integridade de versão corpus / aplicação / prompt origem
-- Aditivo sobre 05_crystal_ball_corpora.sql

ALTER TABLE crystal_corpora
  ADD COLUMN IF NOT EXISTS versao_atual VARCHAR;

ALTER TABLE crystal_corpora
  ADD COLUMN IF NOT EXISTS aplicacao_origem VARCHAR;

UPDATE crystal_corpora
SET aplicacao_origem = 'Mativas'
WHERE aplicacao_origem IS NULL OR btrim(aplicacao_origem) = '';

ALTER TABLE crystal_corpora
  ALTER COLUMN aplicacao_origem SET DEFAULT 'Mativas';

ALTER TABLE crystal_corpora
  ALTER COLUMN aplicacao_origem SET NOT NULL;

ALTER TABLE crystal_resultados_reais
  ADD COLUMN IF NOT EXISTS versao_corpus VARCHAR;

ALTER TABLE crystal_resultados_reais
  ADD COLUMN IF NOT EXISTS versao_prompt_origem VARCHAR;

UPDATE crystal_resultados_reais
SET versao_prompt_origem = 'legado-nao-declarado'
WHERE versao_prompt_origem IS NULL OR btrim(versao_prompt_origem) = '';

ALTER TABLE crystal_resultados_reais
  ALTER COLUMN versao_prompt_origem SET NOT NULL;

COMMENT ON COLUMN crystal_corpora.versao_atual IS
  'Hash (sha256) do conteúdo da fonte do corpus no momento do cadastro/refresh.';
COMMENT ON COLUMN crystal_corpora.aplicacao_origem IS
  'Aplicação que o corpus representa (ex.: Mativas).';
COMMENT ON COLUMN crystal_resultados_reais.versao_corpus IS
  'versao_atual do corpus no momento da colagem do resultado real.';
COMMENT ON COLUMN crystal_resultados_reais.versao_prompt_origem IS
  'Identificador declarado pelo usuário da versão do prompt que gerou o resultado.';
