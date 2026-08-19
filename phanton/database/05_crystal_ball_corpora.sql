-- Crystal Ball — corpora genéricos + ciclos de melhoria (aditivo)
-- Não altera pipeline_runs / phase_executions.

CREATE TABLE IF NOT EXISTS crystal_corpora (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR NOT NULL UNIQUE,
    nome VARCHAR NOT NULL,
    tipo_fonte VARCHAR NOT NULL
        CHECK (tipo_fonte IN ('upload_json', 'conexao_db_readonly')),
    schema_config JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crystal_sugestao_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES crystal_corpora (id) ON DELETE CASCADE,
    markdown TEXT NOT NULL,
    meta JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crystal_ciclos_melhoria (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES crystal_corpora (id) ON DELETE CASCADE,
    numero_ciclo INTEGER NOT NULL,
    data TIMESTAMP NOT NULL DEFAULT NOW(),
    nota_agregada DOUBLE PRECISION,
    nota_por_campo JSONB,
    sugestao_artifact_id UUID REFERENCES crystal_sugestao_artifacts (id) ON DELETE SET NULL,
    shadow_run_ids JSONB,
    UNIQUE (corpus_id, numero_ciclo)
);

CREATE INDEX IF NOT EXISTS idx_crystal_ciclos_corpus
    ON crystal_ciclos_melhoria (corpus_id, numero_ciclo DESC);

CREATE TABLE IF NOT EXISTS crystal_resultados_reais (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES crystal_corpora (id) ON DELETE CASCADE,
    chave_valor VARCHAR NOT NULL,
    desafio_texto TEXT,
    payload JSONB NOT NULL,
    comparison JSONB NOT NULL,
    numero_ciclo INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crystal_resultados_reais_corpus
    ON crystal_resultados_reais (corpus_id, created_at DESC);

COMMENT ON TABLE crystal_corpora IS
    'Crystal Ball — registro genérico de corpora (lookup parametrizado).';
COMMENT ON TABLE crystal_ciclos_melhoria IS
    'Crystal Ball — ciclos de sugestão de prompt geral com notas agregadas.';
COMMENT ON TABLE crystal_sugestao_artifacts IS
    'Crystal Ball — texto de recomendação (somente cópia manual; nunca aplica em sistema externo).';
COMMENT ON TABLE crystal_resultados_reais IS
    'Crystal Ball — resultado real colado manualmente + comparação campo-a-campo.';
