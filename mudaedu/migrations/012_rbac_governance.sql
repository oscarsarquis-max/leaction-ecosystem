-- RBAC PanelDX v2 — identidade global (paneldx_usuarios), notificações, executor em tarefas
-- system_role vive APENAS em paneldx_usuarios (não em ctdi_team / ctdi_clie).
-- ctdi_team mantém position (papel dentro da squad).
-- Executar após migrations anteriores.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Tabela global de usuários (auth + papel de sistema)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.paneldx_usuarios (
    id_usuario      SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    password_hash   TEXT,
    nome            VARCHAR(255) NOT NULL,
    system_role     VARCHAR(32) NOT NULL DEFAULT 'executor',
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    id_clie         INTEGER REFERENCES public.ctdi_clie(id_clie) ON DELETE SET NULL,
    criado_em       TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT paneldx_usuarios_system_role_chk
        CHECK (system_role IN ('sysadmin', 'led', 'consultor', 'executor'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_paneldx_usuarios_email_lower
    ON public.paneldx_usuarios (LOWER(TRIM(email)));

CREATE INDEX IF NOT EXISTS idx_paneldx_usuarios_role
    ON public.paneldx_usuarios (system_role)
    WHERE ativo = TRUE;

COMMENT ON TABLE public.paneldx_usuarios IS
    'Identidade global de autenticação RBAC — sysadmin/consultor podem existir sem squad';

COMMENT ON COLUMN public.paneldx_usuarios.system_role IS
    'sysadmin | led | consultor | executor — papel de sistema (fonte única)';

-- ---------------------------------------------------------------------------
-- 2. Remover system_role de tabelas legadas (se migration anterior foi aplicada)
-- ---------------------------------------------------------------------------
ALTER TABLE public.ctdi_team DROP COLUMN IF EXISTS system_role;
ALTER TABLE public.ctdi_clie DROP COLUMN IF EXISTS system_role;

-- Vínculo opcional squad → usuário global
ALTER TABLE public.ctdi_team
    ADD COLUMN IF NOT EXISTS id_usuario INTEGER REFERENCES public.paneldx_usuarios(id_usuario) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_ctdi_team_id_usuario
    ON public.ctdi_team (id_usuario);

-- ---------------------------------------------------------------------------
-- 3. Seed paneldx_usuarios a partir de ctdi_team (e-mails distintos)
-- ---------------------------------------------------------------------------
INSERT INTO public.paneldx_usuarios (email, nome, password_hash, system_role)
SELECT DISTINCT ON (LOWER(TRIM(t.email)))
    LOWER(TRIM(t.email)),
    t.nome,
    t.password_hash,
    CASE
        WHEN UPPER(COALESCE(t.role, '')) IN ('ADMIN', 'SYSADMIN') THEN 'sysadmin'
        WHEN UPPER(COALESCE(t.role, '')) = 'CONSULTOR'
             OR t.position ILIKE '%Consultor Estratégico%' THEN 'consultor'
        WHEN UPPER(COALESCE(t.role, '')) = 'LEAD' THEN 'led'
        WHEN t.position ILIKE '%Analista%' THEN 'executor'
        ELSE 'executor'
    END
FROM public.ctdi_team t
WHERE t.email IS NOT NULL AND TRIM(t.email) <> ''
ORDER BY LOWER(TRIM(t.email)), t.id_member DESC
ON CONFLICT DO NOTHING;

-- Leads (ctdi_clie) — papel led, sem senha obrigatória (auth via LA-*)
INSERT INTO public.paneldx_usuarios (email, nome, system_role, id_clie, password_hash)
SELECT
    LOWER(TRIM(c.mail_clie)),
    c.nome_clie,
    'led',
    c.id_clie,
    NULL
FROM public.ctdi_clie c
WHERE c.mail_clie IS NOT NULL AND TRIM(c.mail_clie) <> ''
  AND NOT EXISTS (
      SELECT 1 FROM public.paneldx_usuarios u
      WHERE LOWER(TRIM(u.email)) = LOWER(TRIM(c.mail_clie))
  );

-- Backfill id_usuario em ctdi_team
UPDATE public.ctdi_team t
SET id_usuario = u.id_usuario
FROM public.paneldx_usuarios u
WHERE t.id_usuario IS NULL
  AND LOWER(TRIM(t.email)) = LOWER(TRIM(u.email));

-- ---------------------------------------------------------------------------
-- 4. Associações de consultores (carteira — FK usuário global)
-- ---------------------------------------------------------------------------
-- DEPRECATED: consultor_associacoes substituída por dx_consultores + dx_contratos (migration 024).
-- Mantida apenas para compatibilidade de schema legado; não usar em código novo.
CREATE TABLE IF NOT EXISTS public.consultor_associacoes (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES public.paneldx_usuarios(id_usuario) ON DELETE CASCADE,
    client_id   INTEGER REFERENCES public.ctdi_clie(id_clie) ON DELETE CASCADE,
    project_id  INTEGER REFERENCES public.ctdi_projetos(id_proj) ON DELETE CASCADE,
    criado_em   TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT consultor_assoc_escopo_chk CHECK (client_id IS NOT NULL OR project_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_consultor_assoc_user
    ON public.consultor_associacoes (user_id);

CREATE INDEX IF NOT EXISTS idx_consultor_assoc_client
    ON public.consultor_associacoes (client_id);

CREATE INDEX IF NOT EXISTS idx_consultor_assoc_project
    ON public.consultor_associacoes (project_id);

-- ---------------------------------------------------------------------------
-- 5. Notificações in-app (FK usuário global)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.notificacoes (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES public.paneldx_usuarios(id_usuario) ON DELETE CASCADE,
    tipo          VARCHAR(64) NOT NULL,
    mensagem      TEXT NOT NULL,
    lida_status   BOOLEAN NOT NULL DEFAULT FALSE,
    data_criacao  TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    metadata      JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_notificacoes_user_pendentes
    ON public.notificacoes (user_id, lida_status, data_criacao DESC);

-- ---------------------------------------------------------------------------
-- 6. executor_id em tarefas operacionais
-- ---------------------------------------------------------------------------
ALTER TABLE public.ctdi_okr_atividades
    ADD COLUMN IF NOT EXISTS executor_id INTEGER REFERENCES public.ctdi_team(id_member) ON DELETE RESTRICT;

UPDATE public.ctdi_okr_atividades
SET executor_id = id_team
WHERE executor_id IS NULL AND id_team IS NOT NULL;

UPDATE public.ctdi_okr_atividades
SET id_team = executor_id
WHERE id_team IS NULL AND executor_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_okr_atividades_executor
    ON public.ctdi_okr_atividades (executor_id)
    WHERE executor_id IS NOT NULL;

COMMENT ON COLUMN public.ctdi_okr_atividades.executor_id IS
    'Executor designado (FK ctdi_team.id_member) — obrigatório em novas atribuições';

COMMIT;
