'use strict';

/**
 * GET  /admin/apps
 * PUT  /admin/apps/:id
 *
 * webhook_secret nunca é exposto em texto plano — só has_secret / secret_hint.
 */

function maskSecret(secret) {
  const s = String(secret || '').trim();
  if (!s) {
    return { has_secret: false, secret_hint: null };
  }
  const hint = s.length <= 4 ? '****' : `••••${s.slice(-4)}`;
  return { has_secret: true, secret_hint: hint };
}

function serializeApp(row) {
  const masked = maskSecret(row.webhook_secret);
  return {
    app_id: row.app_id,
    name: row.name,
    webhook_url: row.webhook_url || null,
    return_origins: Array.isArray(row.return_origins) ? row.return_origins : [],
    active: Boolean(row.active),
    created_at: row.created_at,
    has_secret: masked.has_secret,
    secret_hint: masked.secret_hint,
  };
}

function parseReturnOrigins(value) {
  if (value == null) return undefined;
  if (Array.isArray(value)) {
    return value.map((v) => String(v).trim()).filter(Boolean);
  }
  if (typeof value === 'string') {
    return value
      .split(',')
      .map((v) => v.trim())
      .filter(Boolean);
  }
  return undefined;
}

/**
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {{ requireAdmin: import('express').RequestHandler }} deps
 */
function registerAdminAppsRoutes(app, pool, { requireAdmin }) {
  app.get('/admin/apps', requireAdmin, async (_req, res) => {
    try {
      const result = await pool.query(
        `SELECT app_id, name, webhook_url, webhook_secret, return_origins, active, created_at
         FROM app_registry
         ORDER BY name ASC, app_id ASC`
      );
      return res.status(200).json({
        apps: result.rows.map(serializeApp),
      });
    } catch (err) {
      console.error('❌ [admin/apps GET]', err.message);
      return res.status(500).json({ error: 'Erro ao listar aplicações' });
    }
  });

  app.put('/admin/apps/:id', requireAdmin, async (req, res) => {
    try {
      const appId = String(req.params.id || '').trim();
      if (!appId) {
        return res.status(400).json({ error: 'id (app_id) obrigatório' });
      }

      const existing = await pool.query(
        `SELECT app_id, name, webhook_url, webhook_secret, return_origins, active, created_at
         FROM app_registry
         WHERE app_id = $1
         LIMIT 1`,
        [appId]
      );
      if (existing.rows.length === 0) {
        return res.status(404).json({ error: 'Aplicação não encontrada' });
      }

      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const current = existing.rows[0];

      const name =
        body.name !== undefined ? String(body.name || '').trim() : current.name;
      if (!name) {
        return res.status(400).json({ error: 'name não pode ser vazio' });
      }

      let active = current.active;
      if (body.active !== undefined) {
        active = Boolean(body.active);
      } else if (body.status !== undefined) {
        const status = String(body.status).trim().toLowerCase();
        if (status === 'active' || status === 'ativo') active = true;
        else if (status === 'inactive' || status === 'inativo') active = false;
        else {
          return res.status(400).json({
            error: 'status inválido (use active/inactive ou active boolean)',
          });
        }
      }

      const webhookUrl =
        body.webhook_url !== undefined
          ? String(body.webhook_url || '').trim() || null
          : current.webhook_url;

      let returnOrigins = current.return_origins;
      if (body.return_origins !== undefined) {
        const parsed = parseReturnOrigins(body.return_origins);
        if (!parsed) {
          return res.status(400).json({ error: 'return_origins inválido' });
        }
        returnOrigins = parsed;
      }

      // webhook_secret: só atualiza se enviado explicitamente (não é retornado depois)
      let webhookSecret = current.webhook_secret;
      if (Object.prototype.hasOwnProperty.call(body, 'webhook_secret')) {
        const next = String(body.webhook_secret || '').trim();
        webhookSecret = next || null;
      }

      const updated = await pool.query(
        `UPDATE app_registry
         SET name = $2,
             active = $3,
             webhook_url = $4,
             return_origins = $5::text[],
             webhook_secret = $6
         WHERE app_id = $1
         RETURNING app_id, name, webhook_url, webhook_secret, return_origins, active, created_at`,
        [appId, name, active, webhookUrl, returnOrigins, webhookSecret]
      );

      return res.status(200).json({ app: serializeApp(updated.rows[0]) });
    } catch (err) {
      console.error('❌ [admin/apps PUT]', err.message);
      return res.status(500).json({ error: 'Erro ao atualizar aplicação' });
    }
  });
}

module.exports = {
  registerAdminAppsRoutes,
  serializeApp,
  maskSecret,
};
