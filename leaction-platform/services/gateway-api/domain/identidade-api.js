'use strict';

/**
 * Gestão de Identidade — catálogo de nível/função/permissões para satélites.
 * Não autentica usuário final: login permanece no satélite.
 *
 * S2S (mesmo mecanismo de entitlements/checkout):
 *   POST /api/identidade/usuarios
 *   GET  /api/identidade/usuarios/:email?sistema=
 *
 * Admin (JWT admin do Hub, mesmo middleware do CMS):
 *   PUT  /api/identidade/usuarios/:id
 *   GET  /api/identidade/usuarios?sistema=
 *   GET  /api/identidade/funcoes?sistema=
 *   POST /api/identidade/funcoes
 *   GET  /api/identidade/permissoes?sistema=
 *   POST /api/identidade/permissoes
 */

const { createRequireAdminAuth } = require('../admin/auth');
const { authenticateApp, extractCallerSecret } = require('./entitlements-api');

const NIVEIS = new Set(['admin', 'gestor_produtivo', 'usuario_executor']);
const STATUSES = new Set(['ativo', 'inativo']);

function normalizeSistema(value) {
  return String(value || '').trim().toLowerCase();
}

function normalizeEmail(value) {
  return String(value || '').trim().toLowerCase();
}

function normalizeNome(value) {
  return String(value || '').trim();
}

function normalizeFuncao(value) {
  if (value == null) return null;
  const nome = String(value).trim();
  return nome || null;
}

function asStringArray(value) {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => String(item || '').trim())
    .filter(Boolean);
}

function serializeUsuario(row) {
  if (!row) return null;
  return {
    id: row.id,
    nome: row.nome,
    email: row.email,
    sistema: row.sistema,
    nivel: row.nivel,
    funcao: row.funcao,
    status: row.status,
    criado_em: row.criado_em,
    atualizado_em: row.atualizado_em,
  };
}

function serializeFuncao(row) {
  if (!row) return null;
  return {
    id: row.id,
    sistema: row.sistema,
    nome: row.nome,
    nivel_associado: row.nivel_associado,
    permissoes: asStringArray(row.permissoes),
  };
}

function serializePermissao(row) {
  if (!row) return null;
  return {
    id: row.id,
    sistema: row.sistema,
    chave: row.chave,
    descricao: row.descricao,
  };
}

async function authenticateSistema(pool, req, sistema) {
  if (!sistema) {
    return { ok: false, status: 400, error: 'sistema é obrigatório' };
  }

  const secret = extractCallerSecret(req);
  if (!secret) {
    return {
      ok: false,
      status: 401,
      error:
        'Credencial ausente. Envie Authorization: Bearer <secret> ou header X-App-Secret.',
    };
  }

  return authenticateApp(pool, sistema, secret);
}

async function assertFuncaoExists(pool, sistema, funcao) {
  if (!funcao) return null;
  const result = await pool.query(
    `SELECT 1 FROM identidade_funcoes
     WHERE sistema = $1 AND nome = $2
     LIMIT 1`,
    [sistema, funcao]
  );
  if (result.rows.length === 0) {
    return `função '${funcao}' não existe no catálogo de identidade_funcoes para o sistema '${sistema}'`;
  }
  return null;
}

async function resolvePermissoes(pool, { sistema, nivel, funcao }) {
  const set = new Set();

  if (nivel === 'admin') {
    const catalog = await pool.query(
      `SELECT chave FROM identidade_permissoes WHERE sistema = $1`,
      [sistema]
    );
    for (const row of catalog.rows) {
      const chave = String(row.chave || '').trim();
      if (chave) set.add(chave);
    }
  }

  if (funcao) {
    const fn = await pool.query(
      `SELECT permissoes FROM identidade_funcoes
       WHERE sistema = $1 AND nome = $2
       LIMIT 1`,
      [sistema, funcao]
    );
    for (const chave of asStringArray(fn.rows[0]?.permissoes)) {
      set.add(chave);
    }
  }

  return [...set];
}

async function upsertUsuario(pool, payload) {
  const sistema = normalizeSistema(payload.sistema);
  const email = normalizeEmail(payload.email);
  const nome = normalizeNome(payload.nome);
  const nivel = String(payload.nivel || '').trim().toLowerCase();
  const funcao = normalizeFuncao(payload.funcao);

  if (!sistema || !email || !nome || !nivel) {
    return {
      ok: false,
      status: 400,
      error: 'Campos obrigatórios: sistema, email, nome, nivel',
    };
  }
  if (!NIVEIS.has(nivel)) {
    return {
      ok: false,
      status: 400,
      error: `nivel inválido (use: ${[...NIVEIS].join(', ')})`,
    };
  }

  const funcaoErr = await assertFuncaoExists(pool, sistema, funcao);
  if (funcaoErr) {
    return { ok: false, status: 400, error: funcaoErr };
  }

  const result = await pool.query(
    `INSERT INTO identidade_usuarios (nome, email, sistema, nivel, funcao)
     VALUES ($1, $2, $3, $4, $5)
     ON CONFLICT (sistema, email) DO UPDATE SET
       nome = EXCLUDED.nome,
       nivel = EXCLUDED.nivel,
       funcao = EXCLUDED.funcao,
       atualizado_em = CURRENT_TIMESTAMP
     RETURNING *`,
    [nome, email, sistema, nivel, funcao]
  );

  return { ok: true, usuario: serializeUsuario(result.rows[0]) };
}

async function getUsuarioPerfil(pool, { sistema, email }) {
  const result = await pool.query(
    `SELECT nivel, funcao, status
     FROM identidade_usuarios
     WHERE sistema = $1 AND email = $2
     LIMIT 1`,
    [sistema, email]
  );
  if (!result.rows[0]) {
    return { ok: false, status: 404, error: 'Usuário não encontrado para este sistema' };
  }

  const row = result.rows[0];
  const permissoes = await resolvePermissoes(pool, {
    sistema,
    nivel: row.nivel,
    funcao: row.funcao,
  });

  return {
    ok: true,
    perfil: {
      nivel: row.nivel,
      funcao: row.funcao,
      permissoes,
      status: row.status,
    },
  };
}

async function updateUsuarioAdmin(pool, id, body = {}) {
  if (!Number.isFinite(id)) {
    return { ok: false, status: 400, error: 'id inválido' };
  }

  const existing = await pool.query(
    `SELECT * FROM identidade_usuarios WHERE id = $1 LIMIT 1`,
    [id]
  );
  if (!existing.rows[0]) {
    return { ok: false, status: 404, error: 'Usuário não encontrado' };
  }

  const prev = existing.rows[0];
  const nivel =
    body.nivel !== undefined
      ? String(body.nivel || '').trim().toLowerCase()
      : prev.nivel;
  const status =
    body.status !== undefined
      ? String(body.status || '').trim().toLowerCase()
      : prev.status;
  const funcao =
    body.funcao !== undefined ? normalizeFuncao(body.funcao) : prev.funcao;

  if (!NIVEIS.has(nivel)) {
    return {
      ok: false,
      status: 400,
      error: `nivel inválido (use: ${[...NIVEIS].join(', ')})`,
    };
  }
  if (!STATUSES.has(status)) {
    return {
      ok: false,
      status: 400,
      error: `status inválido (use: ${[...STATUSES].join(', ')})`,
    };
  }

  const funcaoErr = await assertFuncaoExists(pool, prev.sistema, funcao);
  if (funcaoErr) {
    return { ok: false, status: 400, error: funcaoErr };
  }

  const result = await pool.query(
    `UPDATE identidade_usuarios
     SET nivel = $1,
         funcao = $2,
         status = $3,
         atualizado_em = CURRENT_TIMESTAMP
     WHERE id = $4
     RETURNING *`,
    [nivel, funcao, status, id]
  );

  return { ok: true, usuario: serializeUsuario(result.rows[0]) };
}

async function upsertFuncao(pool, body = {}) {
  const sistema = normalizeSistema(body.sistema);
  const nome = normalizeNome(body.nome);
  const nivelAssociado = String(body.nivel_associado || '').trim().toLowerCase();
  const permissoes = asStringArray(body.permissoes);

  if (!sistema || !nome || !nivelAssociado) {
    return {
      ok: false,
      status: 400,
      error: 'Campos obrigatórios: sistema, nome, nivel_associado',
    };
  }
  if (!NIVEIS.has(nivelAssociado)) {
    return {
      ok: false,
      status: 400,
      error: `nivel_associado inválido (use: ${[...NIVEIS].join(', ')})`,
    };
  }

  const result = await pool.query(
    `INSERT INTO identidade_funcoes (sistema, nome, nivel_associado, permissoes)
     VALUES ($1, $2, $3, $4::jsonb)
     ON CONFLICT (sistema, nome) DO UPDATE SET
       nivel_associado = EXCLUDED.nivel_associado,
       permissoes = EXCLUDED.permissoes
     RETURNING *`,
    [sistema, nome, nivelAssociado, JSON.stringify(permissoes)]
  );

  return { ok: true, funcao: serializeFuncao(result.rows[0]) };
}

async function createPermissao(pool, body = {}) {
  const sistema = normalizeSistema(body.sistema);
  const chave = String(body.chave || '').trim();
  const descricao = body.descricao != null ? String(body.descricao) : '';

  if (!sistema || !chave) {
    return {
      ok: false,
      status: 400,
      error: 'Campos obrigatórios: sistema, chave',
    };
  }

  try {
    const result = await pool.query(
      `INSERT INTO identidade_permissoes (sistema, chave, descricao)
       VALUES ($1, $2, $3)
       RETURNING *`,
      [sistema, chave, descricao]
    );
    return { ok: true, permissao: serializePermissao(result.rows[0]) };
  } catch (err) {
    if (err && err.code === '23505') {
      return { ok: false, status: 409, error: 'chave já existe neste sistema' };
    }
    throw err;
  }
}

/**
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {{ jwtSecret?: string }} [options]
 */
function registerIdentidadeRoutes(app, pool, options = {}) {
  const requireAdmin = createRequireAdminAuth(options.jwtSecret || process.env.JWT_SECRET);

  app.post('/api/identidade/usuarios', async (req, res) => {
    try {
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const sistema = normalizeSistema(body.sistema);
      const auth = await authenticateSistema(pool, req, sistema);
      if (!auth.ok) {
        return res.status(auth.status).json({ error: auth.error });
      }

      const result = await upsertUsuario(pool, body);
      if (!result.ok) {
        return res.status(result.status).json({ error: result.error });
      }
      return res.status(200).json({ usuario: result.usuario });
    } catch (err) {
      console.error('[identidade] POST /api/identidade/usuarios', err.message);
      return res.status(500).json({ error: 'Falha ao gravar usuário de identidade' });
    }
  });

  app.get('/api/identidade/usuarios/:email', async (req, res) => {
    try {
      const sistema = normalizeSistema(req.query.sistema);
      const email = normalizeEmail(decodeURIComponent(String(req.params.email || '')));
      if (!email) {
        return res.status(400).json({ error: 'email é obrigatório' });
      }

      const auth = await authenticateSistema(pool, req, sistema);
      if (!auth.ok) {
        return res.status(auth.status).json({ error: auth.error });
      }

      const result = await getUsuarioPerfil(pool, { sistema, email });
      if (!result.ok) {
        return res.status(result.status).json({ error: result.error });
      }
      return res.status(200).json(result.perfil);
    } catch (err) {
      console.error('[identidade] GET /api/identidade/usuarios/:email', err.message);
      return res.status(500).json({ error: 'Falha ao consultar usuário de identidade' });
    }
  });

  app.put('/api/identidade/usuarios/:id', requireAdmin, async (req, res) => {
    try {
      const id = parseInt(String(req.params.id), 10);
      const result = await updateUsuarioAdmin(pool, id, req.body || {});
      if (!result.ok) {
        return res.status(result.status).json({ error: result.error });
      }
      return res.status(200).json({ usuario: result.usuario });
    } catch (err) {
      console.error('[identidade] PUT /api/identidade/usuarios/:id', err.message);
      return res.status(500).json({ error: 'Falha ao atualizar usuário de identidade' });
    }
  });

  app.get('/api/identidade/usuarios', requireAdmin, async (req, res) => {
    try {
      const sistema = normalizeSistema(req.query.sistema);
      if (!sistema) {
        return res.status(400).json({ error: 'sistema é obrigatório' });
      }

      const result = await pool.query(
        `SELECT id, nome, email, sistema, nivel, funcao, status, criado_em, atualizado_em
         FROM identidade_usuarios
         WHERE sistema = $1
         ORDER BY nome ASC, email ASC
         LIMIT 500`,
        [sistema]
      );
      return res.status(200).json({ usuarios: result.rows.map(serializeUsuario) });
    } catch (err) {
      console.error('[identidade] GET /api/identidade/usuarios', err.message);
      return res.status(500).json({ error: 'Falha ao listar usuários de identidade' });
    }
  });

  app.get('/api/identidade/funcoes', requireAdmin, async (req, res) => {
    try {
      const sistema = normalizeSistema(req.query.sistema);
      if (!sistema) {
        return res.status(400).json({ error: 'sistema é obrigatório' });
      }

      const result = await pool.query(
        `SELECT id, sistema, nome, nivel_associado, permissoes
         FROM identidade_funcoes
         WHERE sistema = $1
         ORDER BY nome ASC`,
        [sistema]
      );
      return res.status(200).json({ funcoes: result.rows.map(serializeFuncao) });
    } catch (err) {
      console.error('[identidade] GET /api/identidade/funcoes', err.message);
      return res.status(500).json({ error: 'Falha ao listar funções de identidade' });
    }
  });

  app.post('/api/identidade/funcoes', requireAdmin, async (req, res) => {
    try {
      const result = await upsertFuncao(pool, req.body || {});
      if (!result.ok) {
        return res.status(result.status).json({ error: result.error });
      }
      return res.status(200).json({ funcao: result.funcao });
    } catch (err) {
      console.error('[identidade] POST /api/identidade/funcoes', err.message);
      return res.status(500).json({ error: 'Falha ao gravar função de identidade' });
    }
  });

  app.get('/api/identidade/permissoes', requireAdmin, async (req, res) => {
    try {
      const sistema = normalizeSistema(req.query.sistema);
      if (!sistema) {
        return res.status(400).json({ error: 'sistema é obrigatório' });
      }

      const result = await pool.query(
        `SELECT id, sistema, chave, descricao
         FROM identidade_permissoes
         WHERE sistema = $1
         ORDER BY chave ASC`,
        [sistema]
      );
      return res.status(200).json({ permissoes: result.rows.map(serializePermissao) });
    } catch (err) {
      console.error('[identidade] GET /api/identidade/permissoes', err.message);
      return res.status(500).json({ error: 'Falha ao listar permissões de identidade' });
    }
  });

  app.post('/api/identidade/permissoes', requireAdmin, async (req, res) => {
    try {
      const result = await createPermissao(pool, req.body || {});
      if (!result.ok) {
        return res.status(result.status).json({ error: result.error });
      }
      return res.status(201).json({ permissao: result.permissao });
    } catch (err) {
      console.error('[identidade] POST /api/identidade/permissoes', err.message);
      return res.status(500).json({ error: 'Falha ao criar permissão de identidade' });
    }
  });

  console.log(
    '🪪 [identidade] rotas /api/identidade (S2S usuários + admin catálogo) registradas'
  );
}

module.exports = {
  registerIdentidadeRoutes,
  upsertUsuario,
  getUsuarioPerfil,
  updateUsuarioAdmin,
  upsertFuncao,
  createPermissao,
  resolvePermissoes,
  assertFuncaoExists,
  NIVEIS,
  STATUSES,
};
