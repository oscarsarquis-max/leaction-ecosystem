'use strict';

/**
 * GET  /admin/plans?app_id=
 * POST /admin/plans
 * PUT  /admin/plans/:id
 */

const PLAN_TYPES = new Set(['plan', 'credit_pack', 'addon', 'seat']);

function serializePlan(row) {
  return {
    id: row.id,
    app_id: row.app_id,
    name: row.name,
    type: row.type,
    sku: row.sku,
    price: row.price != null ? Number(row.price) : 0,
    currency: row.currency || 'BRL',
    features: row.features ?? [],
    meta_json: row.meta_json ?? {},
    active: Boolean(row.active),
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

function normalizeFeatures(value) {
  if (value == null) return [];
  if (Array.isArray(value)) return value;
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [value];
    } catch {
      return [value];
    }
  }
  return [];
}

function normalizeMeta(value) {
  if (value == null) return {};
  if (typeof value === 'object' && !Array.isArray(value)) return value;
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed;
    } catch {
      /* ignore */
    }
  }
  return {};
}

function parsePrice(value) {
  if (value === undefined || value === null || value === '') return null;
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) return NaN;
  return n;
}

/**
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {{ requireAdmin: import('express').RequestHandler }} deps
 */
function registerAdminPlansRoutes(app, pool, { requireAdmin }) {
  app.get('/admin/plans', requireAdmin, async (req, res) => {
    try {
      const appId = String(req.query.app_id || '').trim();
      if (!appId) {
        return res.status(400).json({ error: 'Query obrigatória: app_id' });
      }

      const result = await pool.query(
        `SELECT id, app_id, name, type, sku, price, currency, features, meta_json,
                active, created_at, updated_at
         FROM catalog_plans
         WHERE app_id = $1
         ORDER BY active DESC, name ASC, sku ASC`,
        [appId]
      );

      return res.status(200).json({
        app_id: appId,
        plans: result.rows.map(serializePlan),
      });
    } catch (err) {
      console.error('❌ [admin/plans GET]', err.message);
      return res.status(500).json({ error: 'Erro ao listar planos' });
    }
  });

  app.post('/admin/plans', requireAdmin, async (req, res) => {
    try {
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const appId = String(body.app_id || '').trim();
      const name = String(body.name || '').trim();
      const type = String(body.type || '').trim();
      const sku = String(body.sku || '').trim();
      const price = parsePrice(body.price != null ? body.price : 0);
      const currency = String(body.currency || 'BRL').trim() || 'BRL';
      const features = normalizeFeatures(body.features);
      const metaJson = normalizeMeta(body.meta_json);
      const active = body.active === undefined ? true : Boolean(body.active);

      if (!appId || !name || !type || !sku) {
        return res.status(400).json({
          error: 'Campos obrigatórios: app_id, name, type, sku',
        });
      }
      if (!PLAN_TYPES.has(type)) {
        return res.status(400).json({
          error: `type inválido (use: ${[...PLAN_TYPES].join(', ')})`,
        });
      }
      if (Number.isNaN(price)) {
        return res.status(400).json({ error: 'price inválido' });
      }

      const appExists = await pool.query(
        `SELECT app_id FROM app_registry WHERE app_id = $1 LIMIT 1`,
        [appId]
      );
      if (appExists.rows.length === 0) {
        return res.status(404).json({ error: 'app_id não encontrado em app_registry' });
      }

      const inserted = await pool.query(
        `INSERT INTO catalog_plans (
           app_id, name, type, sku, price, currency, features, meta_json, active
         ) VALUES (
           $1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9
         )
         RETURNING id, app_id, name, type, sku, price, currency, features, meta_json,
                   active, created_at, updated_at`,
        [
          appId,
          name,
          type,
          sku,
          price,
          currency,
          JSON.stringify(features),
          JSON.stringify(metaJson),
          active,
        ]
      );

      return res.status(201).json({ plan: serializePlan(inserted.rows[0]) });
    } catch (err) {
      if (err.code === '23505') {
        return res.status(409).json({ error: 'SKU já existe para este app_id' });
      }
      console.error('❌ [admin/plans POST]', err.message);
      return res.status(500).json({ error: 'Erro ao criar plano' });
    }
  });

  app.put('/admin/plans/:id', requireAdmin, async (req, res) => {
    try {
      const planId = String(req.params.id || '').trim();
      if (!planId) {
        return res.status(400).json({ error: 'id obrigatório' });
      }

      const existing = await pool.query(
        `SELECT id, app_id, name, type, sku, price, currency, features, meta_json,
                active, created_at, updated_at
         FROM catalog_plans
         WHERE id = $1
         LIMIT 1`,
        [planId]
      );
      if (existing.rows.length === 0) {
        return res.status(404).json({ error: 'Plano não encontrado' });
      }

      const current = existing.rows[0];
      const body = req.body && typeof req.body === 'object' ? req.body : {};

      const name =
        body.name !== undefined ? String(body.name || '').trim() : current.name;
      if (!name) {
        return res.status(400).json({ error: 'name não pode ser vazio' });
      }

      let type = current.type;
      if (body.type !== undefined) {
        type = String(body.type || '').trim();
        if (!PLAN_TYPES.has(type)) {
          return res.status(400).json({
            error: `type inválido (use: ${[...PLAN_TYPES].join(', ')})`,
          });
        }
      }

      const sku =
        body.sku !== undefined ? String(body.sku || '').trim() : current.sku;
      if (!sku) {
        return res.status(400).json({ error: 'sku não pode ser vazio' });
      }

      let price = Number(current.price);
      if (body.price !== undefined) {
        price = parsePrice(body.price);
        if (Number.isNaN(price) || price === null) {
          return res.status(400).json({ error: 'price inválido' });
        }
      }

      const currency =
        body.currency !== undefined
          ? String(body.currency || '').trim() || 'BRL'
          : current.currency || 'BRL';

      const features =
        body.features !== undefined
          ? normalizeFeatures(body.features)
          : current.features ?? [];

      const metaJson =
        body.meta_json !== undefined
          ? normalizeMeta(body.meta_json)
          : current.meta_json ?? {};

      const active =
        body.active !== undefined ? Boolean(body.active) : Boolean(current.active);

      const updated = await pool.query(
        `UPDATE catalog_plans
         SET name = $2,
             type = $3,
             sku = $4,
             price = $5,
             currency = $6,
             features = $7::jsonb,
             meta_json = $8::jsonb,
             active = $9,
             updated_at = CURRENT_TIMESTAMP
         WHERE id = $1
         RETURNING id, app_id, name, type, sku, price, currency, features, meta_json,
                   active, created_at, updated_at`,
        [
          planId,
          name,
          type,
          sku,
          price,
          currency,
          JSON.stringify(features),
          JSON.stringify(metaJson),
          active,
        ]
      );

      return res.status(200).json({ plan: serializePlan(updated.rows[0]) });
    } catch (err) {
      if (err.code === '23505') {
        return res.status(409).json({ error: 'SKU já existe para este app_id' });
      }
      console.error('❌ [admin/plans PUT]', err.message);
      return res.status(500).json({ error: 'Erro ao atualizar plano' });
    }
  });
}

module.exports = {
  registerAdminPlansRoutes,
  serializePlan,
  PLAN_TYPES,
};
