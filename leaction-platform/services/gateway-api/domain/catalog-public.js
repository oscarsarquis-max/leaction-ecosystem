'use strict';

/**
 * Catálogo público (vitrine) para apps satélite — espelho leve da vitrine PanelDX.
 *
 * GET  /v1/catalog/:app_id          — planos ativos
 * POST /v1/checkout/catalog         — inicia sessão Brick sem secret no browser
 *                                    (app deve estar ativo em app_registry)
 */

const {
  ensureCatalogBridgeProduct,
  resolveCreditsFromPlan,
  buildHubBrickCheckoutUrl,
} = require('./checkout-sessions');
const { isMercadoPagoConfigured } = require('../mercadopago');

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

function serializePublicPlan(row) {
  const meta = normalizeMeta(row.meta_json);
  const credits = resolveCreditsFromPlan(row);
  return {
    id: row.id,
    app_id: row.app_id,
    sku: row.sku,
    name: row.name,
    type: row.type,
    price: row.price != null ? Number(row.price) : 0,
    currency: row.currency || 'BRL',
    features: Array.isArray(row.features) ? row.features : [],
    credits: credits > 0 ? credits : null,
    meta_json: {
      credits: meta.credits ?? meta.entitlements?.credits ?? undefined,
      period_months: meta.period_months ?? meta.meses ?? undefined,
    },
  };
}

function resolveAppFrontendBase(appId) {
  const id = String(appId || '').trim().toLowerCase();
  const envKey = `APP_FRONTEND_URL_${id.replace(/[^a-z0-9]+/g, '_').toUpperCase()}`;
  let base = String(process.env[envKey] || '').trim().replace(/\/$/, '');
  if (!base && id === 'inove4us') {
    base = String(process.env.INOVE4US_FRONTEND_URL || 'http://localhost:5174')
      .trim()
      .replace(/\/$/, '');
  }
  return base || '';
}

/**
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 */
function registerCatalogPublicRoutes(app, pool) {
  app.get('/v1/catalog/:app_id', async (req, res) => {
    try {
      const appId = String(req.params.app_id || '').trim().toLowerCase();
      if (!appId) {
        return res.status(400).json({ error: 'app_id obrigatório' });
      }

      const appRow = await pool.query(
        `SELECT app_id, name, active FROM app_registry WHERE app_id = $1 LIMIT 1`,
        [appId]
      );
      if (!appRow.rows[0] || !appRow.rows[0].active) {
        return res.status(404).json({ error: 'App não encontrado ou inativo', app_id: appId });
      }

      const result = await pool.query(
        `SELECT id, app_id, name, type, sku, price, currency, features, meta_json, active
         FROM catalog_plans
         WHERE app_id = $1 AND active = TRUE
         ORDER BY price ASC NULLS LAST, name ASC`,
        [appId]
      );

      return res.status(200).json({
        app_id: appId,
        app_name: appRow.rows[0].name,
        plans: result.rows.map(serializePublicPlan),
      });
    } catch (err) {
      console.error('❌ [catalog GET]', err.message);
      return res.status(500).json({ error: 'Erro ao listar catálogo' });
    }
  });

  /**
   * Checkout a partir da vitrine Hub (browser) — sem X-App-Secret.
   * Body: { app_id, subject_id|email, sku, return_origin?, return_to?, hub_public_url? }
   */
  app.post('/v1/checkout/catalog', async (req, res) => {
    try {
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const appId = String(body.app_id || '').trim().toLowerCase();
      const sku = String(body.sku || '').trim();
      const subjectId = String(body.subject_id || body.email || '').trim();

      if (!appId || !sku || !subjectId) {
        return res.status(400).json({
          error: 'Campos obrigatórios: app_id, sku, subject_id (ou email)',
        });
      }

      const appRow = await pool.query(
        `SELECT app_id, active FROM app_registry WHERE app_id = $1 LIMIT 1`,
        [appId]
      );
      if (!appRow.rows[0] || !appRow.rows[0].active) {
        return res.status(404).json({ error: 'App não encontrado ou inativo', app_id: appId });
      }

      if (!isMercadoPagoConfigured()) {
        return res.status(503).json({
          error: 'Mercado Pago não configurado (MP_ACCESS_TOKEN)',
        });
      }

      const planResult = await pool.query(
        `SELECT id, app_id, name, type, sku, price, currency, features, meta_json, active
         FROM catalog_plans
         WHERE app_id = $1 AND sku = $2 AND active = TRUE
         LIMIT 1`,
        [appId, sku]
      );

      if (planResult.rows.length === 0) {
        return res.status(404).json({
          error: 'Plano não encontrado ou inativo no catálogo',
          app_id: appId,
          sku,
        });
      }

      const plan = planResult.rows[0];
      const price = Math.round(Number(plan.price) * 100) / 100;
      if (!Number.isFinite(price) || price <= 0) {
        return res.status(422).json({
          error: 'Plano sem preço válido para checkout',
          sku: plan.sku,
        });
      }

      const meta = normalizeMeta(plan.meta_json);
      const credits = resolveCreditsFromPlan(plan);
      const planType = String(plan.type || 'plan').toLowerCase();
      if (planType === 'credit_pack' && credits <= 0) {
        return res.status(422).json({
          error:
            'Pacote de créditos sem quantidade em meta_json.credits (ou entitlements.credits)',
          sku: plan.sku,
        });
      }

      const subjectLooksLikeEmail = subjectId.includes('@');
      const payerEmail = subjectLooksLikeEmail
        ? subjectId.toLowerCase()
        : String(body.payer_email || body.email || '').trim().toLowerCase();

      const userEmail =
        payerEmail && payerEmail.includes('@')
          ? payerEmail
          : `${appId}.${Buffer.from(subjectId).toString('base64url').slice(0, 24)}@hub.local`;

      const userResult = await pool.query(
        `INSERT INTO users (email, full_name)
         VALUES ($1, $2)
         ON CONFLICT (email)
         DO UPDATE SET full_name = COALESCE(NULLIF(EXCLUDED.full_name, ''), users.full_name)
         RETURNING id, email`,
        [userEmail, subjectLooksLikeEmail ? subjectId.split('@')[0] : subjectId]
      );
      const user = userResult.rows[0];

      const bridgeProduct = await ensureCatalogBridgeProduct(pool);

      const hubPayload = {
        app_id: appId,
        subject_id: subjectId,
        subject_type: subjectLooksLikeEmail ? 'email' : String(body.subject_type || 'email'),
        sku: plan.sku,
        catalog_plan_id: plan.id,
        catalog_type: planType,
        item_type: planType,
        plano_nome: plan.name,
        valor_negociado: price,
        currency: plan.currency || 'BRL',
        credits: credits > 0 ? credits : undefined,
        period_months: Number(meta.period_months || meta.meses || 0) || undefined,
        source: 'catalog_vitrine',
      };
      Object.keys(hubPayload).forEach((k) => {
        if (hubPayload[k] === undefined) delete hubPayload[k];
      });

      const orderResult = await pool.query(
        `INSERT INTO orders (user_id, product_id, status, payment_url, external_resource_id)
         VALUES ($1, $2, 'PENDING', $3, $4)
         RETURNING id, status, created_at`,
        [
          user.id,
          bridgeProduct.id,
          body.webhook_url ? String(body.webhook_url).trim() : null,
          JSON.stringify(hubPayload),
        ]
      );
      const order = orderResult.rows[0];

      await pool.query(`UPDATE orders SET gateway_ref = $1 WHERE id = $2`, [
        `hub:${appId}:${order.id}`,
        order.id,
      ]);

      const appFrontend = resolveAppFrontendBase(appId);
      const returnOrigin =
        String(body.return_origin || appFrontend || '').trim() || undefined;
      const returnTo =
        String(body.return_to || '/mesa-do-inovador?paid=1').trim() ||
        '/mesa-do-inovador?paid=1';

      const checkoutUrl = buildHubBrickCheckoutUrl({
        orderId: order.id,
        customerEmail: userEmail,
        appId,
        hubPublicBase: body.hub_public_url,
        returnTo,
        returnOrigin,
      });

      console.log(
        `📥 [CHECKOUT CATALOG] app=${appId} sku=${plan.sku} order=${order.id} brick=${checkoutUrl}`
      );

      return res.status(200).json({
        checkout_url: checkoutUrl,
        order_id: order.id,
        amount: price,
        currency: plan.currency || 'BRL',
        sku: plan.sku,
        plan_name: plan.name,
        checkout_mode: 'hub_brick',
      });
    } catch (err) {
      console.error('❌ [checkout/catalog]', err.message);
      return res.status(500).json({ error: 'Erro ao iniciar checkout do catálogo' });
    }
  });
}

module.exports = {
  registerCatalogPublicRoutes,
};
