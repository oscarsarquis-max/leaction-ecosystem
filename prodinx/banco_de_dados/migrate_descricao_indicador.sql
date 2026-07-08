-- Migração: descricao_indicador sem FK física em indicadores.cod_indicador
-- Executar na base prodinx (psql -U postgres -d prodinx -f migrate_descricao_indicador.sql)

BEGIN;

-- 1) Remover FK(s) física(s) de descricao_indicador -> indicadores
DO $$
DECLARE
    fk_name TEXT;
BEGIN
    IF to_regclass('public.descricao_indicador') IS NULL THEN
        RETURN;
    END IF;

    FOR fk_name IN
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        WHERE rel.relname = 'descricao_indicador'
          AND con.contype = 'f'
    LOOP
        EXECUTE format(
            'ALTER TABLE descricao_indicador DROP CONSTRAINT %I',
            fk_name
        );
    END LOOP;
END $$;

-- 2) Remover UNIQUE isolado em indicadores.cod_indicador (se existir)
ALTER TABLE indicadores DROP CONSTRAINT IF EXISTS uq_indicadores_cod_indicador;
DROP INDEX IF EXISTS uq_indicadores_cod_indicador;

-- 3) Garantir índice composto único em indicadores
CREATE UNIQUE INDEX IF NOT EXISTS uq_indicadores_cod_grupo
    ON indicadores (cod_indicador, nome_grupo);

-- 4) Garantir índice de lookup em descricao_indicador
CREATE INDEX IF NOT EXISTS ix_descricao_indicador_cod_indicador
    ON descricao_indicador (cod_indicador);

COMMIT;

-- ---------------------------------------------------------------------------
-- Alternativa (recriar do zero — perde dados de descricao_indicador):
--
-- BEGIN;
-- DROP TABLE IF EXISTS descricao_indicador CASCADE;
-- ALTER TABLE indicadores DROP CONSTRAINT IF EXISTS uq_indicadores_cod_indicador;
-- DROP INDEX IF EXISTS uq_indicadores_cod_indicador;
-- CREATE TABLE descricao_indicador (
--     id SERIAL PRIMARY KEY,
--     cod_indicador VARCHAR(10) NOT NULL UNIQUE,
--     subpapel VARCHAR(50),
--     normalizacao VARCHAR(100),
--     explicacao TEXT,
--     importancia TEXT
-- );
-- CREATE INDEX ix_descricao_indicador_cod_indicador ON descricao_indicador (cod_indicador);
-- COMMIT;
