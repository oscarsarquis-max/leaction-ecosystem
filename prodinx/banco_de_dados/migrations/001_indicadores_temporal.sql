-- Migração: colunas temporais e índices para histórico de 1 ano
-- Executada automaticamente por servicos/db_migrations.py no arranque da aplicação

ALTER TABLE indicadores ADD COLUMN IF NOT EXISTS data_importacao TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE indicadores ADD COLUMN IF NOT EXISTS data_referencia_inicio DATE;
ALTER TABLE indicadores ADD COLUMN IF NOT EXISTS data_referencia_fim DATE;

CREATE INDEX IF NOT EXISTS ix_indicadores_data_referencia_inicio
    ON indicadores (data_referencia_inicio);

CREATE INDEX IF NOT EXISTS ix_indicadores_data_importacao
    ON indicadores (data_importacao);
