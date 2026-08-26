-- Identidade aditiva (Hub) — não quebra auth legado
-- role permanece para admin / restricted_tester; novos usuários usam nivel/funcao.

ALTER TABLE users ALTER COLUMN role DROP NOT NULL;

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check
    CHECK (role IS NULL OR role IN ('admin', 'restricted_tester'));

ALTER TABLE users ADD COLUMN IF NOT EXISTS nome TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS nivel TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS funcao TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS sync_pendente BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_nivel;
ALTER TABLE users ADD CONSTRAINT chk_users_nivel
    CHECK (
        nivel IS NULL
        OR nivel IN ('admin', 'gestor_produtivo', 'usuario_executor')
    );

CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email
    ON users (email)
    WHERE email IS NOT NULL;

CREATE TABLE IF NOT EXISTS codigos_acesso (
    codigo TEXT PRIMARY KEY,
    nivel TEXT NOT NULL,
    funcao TEXT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    usado_por TEXT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    usado_em TIMESTAMP NULL,
    CONSTRAINT chk_codigos_acesso_nivel CHECK (
        nivel IN ('admin', 'gestor_produtivo', 'usuario_executor')
    )
);

CREATE INDEX IF NOT EXISTS idx_codigos_acesso_ativo
    ON codigos_acesso (ativo);
