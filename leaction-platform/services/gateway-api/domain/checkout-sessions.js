'use strict';

/**
 * POST /v1/checkout/sessions
 * Ponte satélite → catalog_plans → order PENDING → checkout Brick no Action Hub
 * (mesmo padrão white-label do PanelDX — NÃO usa Checkout Pro / Preference redirect).
 *
 * Body: { app_id, subject_id, sku, return_origin?, return_to?, hub_public_url? }
 * Auth: Bearer / X-App-Secret
 * Resposta: { checkout_url }  → Hub /dashboard?checkout=…&client=…
 */

const { isMercadoPagoConfigured } = require('../mercadopago');
const { authenticateApp, extractCallerSecret } = require('./entitlements-api');

const BRIDGE_PRODUCT_SKU = 'HUB_CATALOG';

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

/** URL do Brick no Action Hub (white-label via ?client=). */
function buildHubBrickCheckoutUrl({
  orderId,
  customerEmail,
  appId,
  hubPublicBase,
  returnTo,
  returnOrigin,
}) {
  const hubBase = String(
    hubPublicBase || process.env.ACTION_HUB_PUBLIC_URL || 'http://localhost:4000'
  )
    .trim()
    .replace(/\/$/, '');
  const params = new URLSearchParams();
  params.set('checkout', String(orderId));
  if (customerEmail) params.set('email', String(customerEmail).trim());
  if (appId) params.set('client', String(appId).trim().toLowerCase());
  const path = String(returnTo || '').trim();
  if (path.startsWith('/') && !path.startsWith('//')) {
    params.set('return_to', path);
  }
  const originRaw = String(returnOrigin || '').trim();
  if (originRaw) {
    try {
      const parsed = new URL(originRaw.includes('://') ? originRaw : `https://${originRaw}`);
      if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
        params.set('return_origin', parsed.origin);
      }
    } catch {
      /* ignore */
    }
  }
  return `${hubBase}/dashboard?${params.toString()}`;
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

/** Créditos do plano: meta_json → entitlements → features → nome. */
function resolveCreditsFromPlan(plan) {
  const meta = normalizeMeta(plan.meta_json);
  const entitlements =
    meta.entitlements && typeof meta.entitlements === 'object' ? meta.entitlements : {};
  const fromMeta = Number(
    meta.credits ??
      entitlements.credits ??
      meta.credit_quantity ??
      meta.quantidade_creditos ??
      meta.quantidade ??
      0
  );
  if (Number.isFinite(fromMeta) && fromMeta > 0) {
    return Math.floor(fromMeta);
  }

  const features = Array.isArray(plan.features) ? plan.features : [];
  for (const f of features) {
    const m = String(f || '').match(/(\d+)\s*cr[eé]dito/i);
    if (m) return Number(m[1]);
  }

  const nameMatch = String(plan.name || '').match(/(\d+)\s*$/);
  if (nameMatch && String(plan.type || '').toLowerCase() === 'credit_pack') {
    return Number(nameMatch[1]);
  }

  return 0;
}

async function ensureCatalogBridgeProduct(pool) {
  const existing = await pool.query(
    `SELECT id, sku, name, type FROM products WHERE sku = $1 LIMIT 1`,
    [BRIDGE_PRODUCT_SKU]
  );
  if (existing.rows[0]) return existing.rows[0];

  const inserted = await pool.query(
    `INSERT INTO products (sku, name, type, external_resource_id)
     VALUES ($1, $2, $3, $4)
     ON CONFLICT (sku) DO UPDATE SET
       name = EXCLUDED.name,
       type = EXCLUDED.type,
       external_resource_id = EXCLUDED.external_resource_id
     RETURNING id, sku, name, type`,
    [BRIDGE_PRODUCT_SKU, 'Catálogo Hub (bridge)', 'HUB_CATALOG', 'catalog_plans']
  );
  return inserted.rows[0];
}

/**
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 */
function registerCheckoutSessionsRoutes(app, pool) {
  app.post('/v1/checkout/sessions', async (req, res) => {
    try {
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const appId = String(body.app_id || '').trim().toLowerCase();
      const subjectId = String(body.subject_id || '').trim();
      const sku = String(body.sku || '').trim();

      if (!appId || !subjectId || !sku) {
        return res.status(400).json({
          error: 'Campos obrigatórios: app_id, subject_id, sku',
        });
      }

      const secret = extractCallerSecret(req);
      if (!secret) {
        return res.status(401).json({
          error:
            'Credencial ausente. Envie Authorization: Bearer <secret> ou header X-App-Secret.',
        });
      }

      const auth = await authenticateApp(pool, appId, secret);
      if (!auth.ok) {
        return res.status(auth.status).json({ error: auth.error });
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
            'Pacote de créditos sem quantidade em meta_json.credits (ou features/nome com número)',
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
        source: 'catalog_checkout',
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
        `📥 [CHECKOUT SESSION] app=${appId} sku=${plan.sku} order=${order.id} brick=${checkoutUrl}`
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
      console.error('❌ Erro em POST /v1/checkout/sessions:', err.message);
      const status = err.statusCode && err.statusCode >= 400 && err.statusCode < 600 ? err.statusCode : 500;
      return res.status(status).json({
        error: status >= 500 ? 'Erro interno no servidor' : err.message,
        detail: err.mpResponse || undefined,
      });
    }
  });
}

module.exports = {
  registerCheckoutSessionsRoutes,
  ensureCatalogBridgeProduct,
  resolveCreditsFromPlan,
  buildHubBrickCheckoutUrl,
  BRIDGE_PRODUCT_SKU,
};
