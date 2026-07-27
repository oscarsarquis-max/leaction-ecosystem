'use strict';

const { createRequireAdminAuth } = require('../admin/auth');

const DESTINOS = new Set([
  'hub-publico',
  'actionhub',
  'inove4us',
  'paneldx',
  'todos',
]);
const STATUSES = new Set(['rascunho', 'publicado']);
const ACTIONS_WHITELIST = new Set(['open_upgrade']);

function serializeRow(row) {
  if (!row) return null;
  return {
    id: row.id,
    sistema_destino: row.sistema_destino,
    status: row.status,
    tree: row.tree,
    publicado_em: row.publicado_em,
    atualizado_em: row.atualizado_em,
    atualizado_por: row.atualizado_por,
    created_at: row.created_at,
  };
}

/**
 * Valida o JSONB `tree` para publicação.
 * @returns {string[]} lista de erros (vazia = ok)
 */
function validateTree(tree) {
  const errors = [];
  if (!tree || typeof tree !== 'object' || Array.isArray(tree)) {
    return ['tree deve ser um objeto JSON'];
  }

  const nodes = tree.nodes;
  if (!nodes || typeof nodes !== 'object' || Array.isArray(nodes)) {
    errors.push('tree.nodes deve ser um objeto');
    return errors;
  }

  const nodeIds = Object.keys(nodes);
  if (nodeIds.length === 0) {
    errors.push('tree.nodes não pode estar vazio');
  }

  const rootId = String(tree.root_id || '').trim();
  if (!rootId) {
    errors.push('tree.root_id é obrigatório');
  } else if (!(rootId in nodes)) {
    errors.push(`tree.root_id '${rootId}' não existe em nodes`);
  }

  const avatarName = String(tree.avatar_name || '').trim();
  if (!avatarName) {
    errors.push('tree.avatar_name é obrigatório');
  }

  for (const nid of nodeIds) {
    const node = nodes[nid];
    if (!node || typeof node !== 'object' || Array.isArray(node)) {
      errors.push(`nodes['${nid}'] deve ser um objeto`);
      continue;
    }

    const message = node.message;
    if (typeof message !== 'string' || !message.trim()) {
      errors.push(`nodes['${nid}'].message deve ser string não vazia`);
    } else if (message.length > 2000) {
      errors.push(`nodes['${nid}'].message excede 2000 caracteres`);
    }

    if (!Array.isArray(node.options)) {
      errors.push(`nodes['${nid}'].options deve ser um array`);
      continue;
    }

    node.options.forEach((opt, idx) => {
      const prefix = `nodes['${nid}'].options[${idx}]`;
      if (!opt || typeof opt !== 'object' || Array.isArray(opt)) {
        errors.push(`${prefix} deve ser um objeto`);
        return;
      }
      const label = String(opt.label || '').trim();
      if (!label) {
        errors.push(`${prefix}.label é obrigatório`);
      }

      if (opt.next != null && String(opt.next).trim() !== '') {
        const next = String(opt.next).trim();
        if (!(next in nodes)) {
          errors.push(`${prefix}.next '${next}' não existe em nodes`);
        }
      }

      if (opt.href != null && String(opt.href).trim() !== '') {
        const href = String(opt.href).trim();
        if (!href.startsWith('/')) {
          errors.push(`${prefix}.href deve ser rota interna começando com '/' (recebido: '${href}')`);
        }
      }

      if (opt.action != null && String(opt.action).trim() !== '') {
        const action = String(opt.action).trim();
        if (!ACTIONS_WHITELIST.has(action)) {
          errors.push(
            `${prefix}.action '${action}' inválida (permitidas: ${[...ACTIONS_WHITELIST].join(', ')})`
          );
        }
      }
    });
  }

  return errors;
}

function parseBody(body = {}) {
  const sistema_destino = String(body.sistema_destino || '').trim().toLowerCase();
  const status = String(body.status || 'rascunho').trim().toLowerCase();
  const tree = body.tree;
  return { sistema_destino, status, tree };
}

function adminActor(req) {
  if (!req.admin) return null;
  if (req.admin.email) return String(req.admin.email);
  if (req.admin.userId) return String(req.admin.userId);
  if (req.admin.via === 'api_key') return 'api_key';
  return null;
}

/**
 * Headless CMS — árvore do assistente (Nina).
 * Público: GET /api/cms/assistente-chat?sistema_destino=
 * Admin: GET /api/cms/assistente-chat/admin , PUT /api/cms/assistente-chat
 *
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {{ jwtSecret?: string }} [options]
 */
function registerCmsAssistenteChatRoutes(app, pool, options = {}) {
  const requireAdmin = createRequireAdminAuth(options.jwtSecret || process.env.JWT_SECRET);

  // —— Leitura pública (satélites) ——
  app.get('/api/cms/assistente-chat', async (req, res) => {
    try {
      const sistema = String(req.query.sistema_destino || '').trim().toLowerCase();
      if (!sistema) {
        return res.status(400).json({ error: 'sistema_destino é obrigatório' });
      }
      if (!DESTINOS.has(sistema)) {
        return res.status(400).json({
          error: `sistema_destino inválido (use: ${[...DESTINOS].join(', ')})`,
        });
      }

      const result = await pool.query(
        `SELECT tree
         FROM cms_assistente_chat
         WHERE status = 'publicado'
           AND sistema_destino = $1
         LIMIT 1`,
        [sistema]
      );

      if (!result.rows[0]) {
        return res.status(404).json({
          error: 'Nenhuma árvore publicada para este sistema_destino',
        });
      }

      return res.status(200).json({ tree: result.rows[0].tree });
    } catch (err) {
      console.error('[cms] GET /api/cms/assistente-chat', err.message);
      return res.status(500).json({ error: 'Falha ao obter árvore do assistente' });
    }
  });

  // —— Admin: rascunho + publicado ——
  app.get('/api/cms/assistente-chat/admin', requireAdmin, async (req, res) => {
    try {
      const sistema = String(req.query.sistema_destino || '').trim().toLowerCase();
      if (!sistema) {
        return res.status(400).json({ error: 'sistema_destino é obrigatório' });
      }
      if (!DESTINOS.has(sistema)) {
        return res.status(400).json({
          error: `sistema_destino inválido (use: ${[...DESTINOS].join(', ')})`,
        });
      }

      const result = await pool.query(
        `SELECT id, sistema_destino, status, tree, publicado_em,
                atualizado_em, atualizado_por, created_at
         FROM cms_assistente_chat
         WHERE sistema_destino = $1
           AND status IN ('rascunho', 'publicado')`,
        [sistema]
      );

      let rascunho = null;
      let publicado = null;
      for (const row of result.rows) {
        const item = serializeRow(row);
        if (row.status === 'rascunho') rascunho = item;
        if (row.status === 'publicado') publicado = item;
      }

      return res.status(200).json({ rascunho, publicado });
    } catch (err) {
      console.error('[cms] GET /api/cms/assistente-chat/admin', err.message);
      return res.status(500).json({ error: 'Falha ao listar árvore do assistente' });
    }
  });

  // —— Admin: salvar rascunho ou publicar ——
  app.put('/api/cms/assistente-chat', requireAdmin, async (req, res) => {
    try {
      const payload = parseBody(req.body);

      if (!payload.sistema_destino) {
        return res.status(400).json({ error: 'sistema_destino é obrigatório' });
      }
      if (!DESTINOS.has(payload.sistema_destino)) {
        return res.status(400).json({
          error: `sistema_destino inválido (use: ${[...DESTINOS].join(', ')})`,
        });
      }
      if (!STATUSES.has(payload.status)) {
        return res.status(400).json({
          error: `status inválido (use: ${[...STATUSES].join(', ')})`,
        });
      }
      if (payload.tree == null || typeof payload.tree !== 'object' || Array.isArray(payload.tree)) {
        return res.status(400).json({ error: 'tree é obrigatório e deve ser um objeto' });
      }

      if (payload.status === 'publicado') {
        const treeErrors = validateTree(payload.tree);
        if (treeErrors.length) {
          return res.status(400).json({
            error: 'Árvore inválida',
            errors: treeErrors,
          });
        }
      }

      const actor = adminActor(req);
      const publicadoEm =
        payload.status === 'publicado' ? new Date().toISOString() : null;

      // UPSERT por (sistema_destino, status): 1 rascunho + 1 publicado por destino
      const result = await pool.query(
        `INSERT INTO cms_assistente_chat
           (sistema_destino, status, tree, publicado_em, atualizado_em, atualizado_por)
         VALUES ($1, $2, $3::jsonb, $4, CURRENT_TIMESTAMP, $5)
         ON CONFLICT (sistema_destino, status) DO UPDATE SET
           tree = EXCLUDED.tree,
           publicado_em = CASE
             WHEN EXCLUDED.status = 'publicado' THEN EXCLUDED.publicado_em
             ELSE cms_assistente_chat.publicado_em
           END,
           atualizado_em = CURRENT_TIMESTAMP,
           atualizado_por = EXCLUDED.atualizado_por
         RETURNING *`,
        [
          payload.sistema_destino,
          payload.status,
          JSON.stringify(payload.tree),
          publicadoEm,
          actor,
        ]
      );

      return res.status(200).json({ assistente_chat: serializeRow(result.rows[0]) });
    } catch (err) {
      console.error('[cms] PUT /api/cms/assistente-chat', err.message);
      return res.status(500).json({ error: 'Falha ao salvar árvore do assistente' });
    }
  });

  console.log(
    '🧭 [cms] rotas /api/cms/assistente-chat (GET público + GET/PUT admin) registradas'
  );
}

module.exports = {
  registerCmsAssistenteChatRoutes,
  validateTree,
};
