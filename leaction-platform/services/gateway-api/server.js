const express = require('express');
const { randomUUID } = require('crypto');
const { Pool } = require('pg');
const cors = require('cors'); // Importa o porteiro
const axios = require('axios');
const jwt = require('jsonwebtoken');
require('dotenv').config({ path: '../../.env', override: true }); // Busca o .env na raiz

const {
  createPreapprovalSubscription,
  createCardPayment,
  createCardPaymentWithSandboxFallback,
  createSandboxCardTokenServerSide,
  validateBrickCredentialPair,
  getSubscriptionConfig,
  getCheckoutMode,
  getPanelDxPaymentAmount,
  resolveOrderPaymentAmount,
  isMercadoPagoConfigured,
  isPreapprovalSuccess,
  isCardPaymentSuccess,
  getMercadoPagoPublicKey,
  getMercadoPagoAccessToken,
  getSandboxPayerEmail,
  resolveSandboxPayerEmail,
  isServerTokenizeFallbackEnabled,
  mapMpStatusDetailHint,
} = require('./mercadopago');
const { fulfillOrderPayment, parsePanelDxIdMatu } = require('./payment-fulfillment');
const { loginOrRegister, ensurePasswordColumn } = require('./hub-auth');
const { registerCrmTrackingRoutes } = require('./crm-tracking');
const { registerEntitlementsRoutes } = require('./domain/entitlements-api');
const { startOutboxWorker } = require('./domain/outbox-worker');
const { registerAdminRoutes } = require('./admin');

const JWT_SECRET = process.env.JWT_SECRET || 'super-secret-hub-key-2026';
const ACTION_HUB_PUBLIC_URL = (process.env.ACTION_HUB_PUBLIC_URL || 'http://localhost:4000').replace(/\/$/, '');
const PANELDX_FLASK_URL = (process.env.PANELDX_API_INTERNAL_URL || 'http://127.0.0.1:5002').replace(/\/$/, '');

async function fetchPanelDxLiveVitrine() {
  try {
    const response = await axios.get(`${PANELDX_FLASK_URL}/api/public/vitrine/planos`, {
      timeout: 8000,
      validateStatus: (status) => status < 500,
    });
    if (response.status !== 200 || !Array.isArray(response.data?.planos)) {
      return null;
    }
    const planos = response.data.planos.filter((p) => p && p.ativo !== false);
    if (!planos.length) return null;
    return {
      planos,
      addons: Array.isArray(response.data.addons) ? response.data.addons : [],
    };
  } catch (err) {
    console.warn('⚠️ [vitrine/live] PanelDX indisponível:', err.message);
    return null;
  }
}

const app = express();

// CONFIGURAÇÃO: Libera o acesso para o seu Frontend
app.use(cors());
app.use(express.json());

function stripSslModeFromDatabaseUrl(url) {
  if (!url) return '';
  let out = url.replace(/([?&])sslmode=[^&]*/gi, '$1');
  return out.replace(/\?&/, '?').replace(/[?&]$/, '');
}

function buildPoolConfig() {
  const raw = process.env.DATABASE_URL || '';
  if (!raw) return { connectionString: raw };
  if (/localhost|127\.0\.0\.1/i.test(raw)) {
    return { connectionString: raw };
  }
  return {
    connectionString: stripSslModeFromDatabaseUrl(raw),
    ssl: { rejectUnauthorized: false },
  };
}

const pool = new Pool(buildPoolConfig());

const VITRINE_SYNC_SECRET = (process.env.VITRINE_SYNC_SECRET || '').trim();

function vitrineSyncAuthorized(req) {
  if (!VITRINE_SYNC_SECRET) return true;
  return String(req.headers['x-paneldx-vitrine-sync'] || '').trim() === VITRINE_SYNC_SECRET;
}

/** Recebe catálogo PanelDX em lote (push) e confirma recebimento. */
app.post('/v1/vitrine/paneldx/sync', async (req, res) => {
  if (!vitrineSyncAuthorized(req)) {
    return res.status(401).json({ received: false, error: 'Sync não autorizado' });
  }

  const planos = req.body?.planos;
  const addons = Array.isArray(req.body?.addons) ? req.body.addons : [];
  if (!Array.isArray(planos) || planos.length === 0) {
    return res.status(400).json({ received: false, error: 'planos[] obrigatório' });
  }

  const syncId = isUuid(req.body?.sync_id) ? req.body.sync_id : randomUUID();
  const receivedAt = new Date().toISOString();

  try {
    await pool.query(
      `INSERT INTO paneldx_vitrine_snapshots
         (sync_id, payload, planos_count, source, published_at, received_at)
       VALUES ($1, $2::jsonb, $3, $4, $5, $6::timestamptz)`,
      [
        syncId,
        JSON.stringify({ planos, addons }),
        planos.length,
        req.body?.source || 'paneldx',
        req.body?.published_at || receivedAt,
        receivedAt,
      ]
    );

    return res.status(200).json({
      received: true,
      sync_id: syncId,
      planos_count: planos.length,
      received_at: receivedAt,
    });
  } catch (err) {
    console.error('❌ [vitrine/sync]', err.message);
    return res.status(500).json({ received: false, error: 'Falha ao gravar snapshot da vitrine' });
  }
});

/** Catálogo PanelDX — prioriza CRM ao vivo; cache Hub como fallback. */
app.get('/v1/vitrine/paneldx', async (req, res) => {
  try {
    const live = await fetchPanelDxLiveVitrine();
    if (live) {
      res.set('Cache-Control', 'no-store, no-cache, must-revalidate');
      return res.json({
        status: 'success',
        source: 'paneldx_live',
        planos: live.planos,
        addons: live.addons,
        received_at: new Date().toISOString(),
      });
    }

    const result = await pool.query(
      `SELECT sync_id, payload, planos_count, received_at, published_at
       FROM paneldx_vitrine_snapshots
       ORDER BY received_at DESC
       LIMIT 1`
    );

    if (!result.rows.length) {
      return res.status(404).json({
        status: 'error',
        error: 'Vitrine ainda não publicada pelo PanelDX',
        planos: [],
      });
    }

    const row = result.rows[0];
    const payload = row.payload || {};
    const planos = Array.isArray(payload.planos) ? payload.planos : [];
    const addons = Array.isArray(payload.addons) ? payload.addons : [];

    return res.json({
      status: 'success',
      source: 'hub_cache',
      sync_id: row.sync_id,
      planos_count: row.planos_count,
      received_at: row.received_at,
      published_at: row.published_at,
      planos,
      addons,
    });
  } catch (err) {
    console.error('❌ [vitrine/get]', err.message);
    return res.status(500).json({ status: 'error', error: err.message, planos: [], addons: [] });
  }
});

/** Pacote add-on publicado (cache Hub — sem chamada runtime ao PanelDX). */
app.get('/v1/vitrine/paneldx/addons/:addonId', async (req, res) => {
  const addonId = parsePanelDxIdPlano(req.params.addonId);
  if (!addonId) {
    return res.status(400).json({ status: 'error', error: 'addon_id inválido' });
  }

  try {
    const result = await pool.query(
      `SELECT payload FROM paneldx_vitrine_snapshots ORDER BY received_at DESC LIMIT 1`
    );
    if (!result.rows.length) {
      return res.status(404).json({ status: 'error', error: 'Vitrine ainda não publicada pelo PanelDX' });
    }

    const payload = result.rows[0].payload || {};
    const addons = Array.isArray(payload.addons) ? payload.addons : [];
    const match = addons.find((a) => String(a?.id) === addonId);
    if (!match) {
      return res.status(404).json({ status: 'error', error: 'Pacote add-on não encontrado no cache do Hub' });
    }

    return res.json({
      status: 'success',
      addon: {
        id: match.id,
        nome: match.nome,
        valor_mensal: Number(match.valor_mensal) || 0,
        periodicidade: match.periodicidade || 'Mensal',
        max_usuarios: Number(match.max_usuarios) || 0,
        tipo_plano: 'addon',
      },
    });
  } catch (err) {
    console.error('❌ [vitrine/addon]', err.message);
    return res.status(500).json({ status: 'error', error: err.message });
  }
});

function isUuid(value) {
  return (
    typeof value === 'string' &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
  );
}

/** Monta a URL de checkout do Action Hub com o UUID real do pedido. */
function resolveHubPublicUrl(clientUrl) {
  const raw = String(clientUrl || '').trim();
  if (!raw) return ACTION_HUB_PUBLIC_URL;
  try {
    const parsed = new URL(raw);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return ACTION_HUB_PUBLIC_URL;
    }
    return parsed.origin;
  } catch {
    return ACTION_HUB_PUBLIC_URL;
  }
}

function buildCheckoutUrl(orderId, customerEmail, hubPublicBase, returnTo, clientId, returnOrigin) {
  const orderIdStr = String(orderId || '').trim();
  const emailStr = String(customerEmail || '').trim();
  if (!orderIdStr) {
    throw new Error('buildCheckoutUrl: orderId obrigatorio');
  }
  const base = resolveHubPublicUrl(hubPublicBase);
  const params = new URLSearchParams();
  params.set('checkout', orderIdStr);
  if (emailStr) {
    params.set('email', emailStr);
  }
  const returnPath = String(returnTo || '').trim();
  if (returnPath && returnPath.startsWith('/') && !returnPath.startsWith('//')) {
    params.set('return_to', returnPath);
  }
  const originRaw = String(returnOrigin || '').trim();
  if (originRaw) {
    try {
      const parsed = new URL(originRaw.includes('://') ? originRaw : `https://${originRaw}`);
      if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
        params.set('return_origin', parsed.origin);
      }
    } catch {
      /* ignora origem invalida */
    }
  }
  const clientStr = String(clientId || '').trim();
  if (clientStr) {
    params.set('client', clientStr);
  }
  return `${base}/dashboard?${params.toString()}`;
}

function parsePanelDxIdClie(raw) {
  const n = parseInt(String(raw ?? ''), 10);
  return Number.isFinite(n) && n > 0 ? String(n) : '';
}

function parsePanelDxIdPlano(raw) {
  const n = parseInt(String(raw ?? ''), 10);
  return Number.isFinite(n) && n > 0 ? String(n) : '';
}

function validateV1PaymentBody(body) {
  const missing = [];
  if (body == null || typeof body !== 'object') {
    return ['client_id', 'sku', 'amount', 'customer.email', 'webhook_url', 'id_matu'];
  }
  const sku = String(body.sku || '').trim();
  const isSubscription = sku === 'PANELDX_SUBSCRIPTION';
  const isAddon = sku === 'PANELDX_ADDON';
  if (!body.client_id || String(body.client_id).trim() === '') missing.push('client_id');
  if (!sku) missing.push('sku');
  if (body.amount === undefined || body.amount === null || body.amount === '') missing.push('amount');
  if (!body.customer?.email || String(body.customer.email).trim() === '') missing.push('customer.email');
  if (!body.webhook_url || String(body.webhook_url).trim() === '') missing.push('webhook_url');
  if (!parsePanelDxIdMatu(body.id_matu) && !isSubscription && !isAddon) missing.push('id_matu');
  if (isSubscription) {
    if (!parsePanelDxIdClie(body.id_clie)) missing.push('id_clie');
    if (!parsePanelDxIdPlano(body.id_plano)) missing.push('id_plano');
  }
  if (isAddon) {
    if (!parsePanelDxIdClie(body.id_clie)) missing.push('id_clie');
    if (!parsePanelDxIdPlano(body.id_plano)) missing.push('id_plano');
  }
  return missing;
}

function buildPanelDxDirectCheckoutUrl(
  orderId,
  customerEmail,
  hubPublicBase,
  returnTo,
  clientId,
  returnOrigin,
  addonId
) {
  const orderIdStr = String(orderId || '').trim();
  const emailStr = String(customerEmail || '').trim();
  if (!orderIdStr) {
    throw new Error('buildPanelDxDirectCheckoutUrl: orderId obrigatorio');
  }
  const base = resolveHubPublicUrl(hubPublicBase);
  const params = new URLSearchParams();
  params.set('checkout', orderIdStr);
  if (emailStr) params.set('email', emailStr);
  const clie = parsePanelDxIdClie(clientId);
  if (clie) params.set('client_id', clie);
  const addon = parsePanelDxIdPlano(addonId);
  if (addon) params.set('addon_id', addon);
  const returnPath = String(returnTo || '').trim();
  if (returnPath && returnPath.startsWith('/') && !returnPath.startsWith('//')) {
    params.set('return_to', returnPath);
  }
  const originRaw = String(returnOrigin || '').trim();
  if (originRaw) {
    try {
      const parsed = new URL(originRaw.includes('://') ? originRaw : `https://${originRaw}`);
      if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
        params.set('return_origin', parsed.origin);
      }
    } catch {
      /* ignora */
    }
  }
  params.set('client', 'paneldx');
  return `${base}/checkout/direct?${params.toString()}`;
}

app.post('/v1/payments', async (req, res) => {
  const missingFields = validateV1PaymentBody(req.body);
  if (missingFields.length > 0) {
    return res.status(400).json({
      error: 'Campos obrigatórios ausentes',
      missing: missingFields,
    });
  }

  const {
    client_id,
    sku,
    amount,
    customer,
    webhook_url,
    id_matu,
    id_clie,
    id_plano,
    plano_nome,
    periodicidade,
    hub_public_url,
    return_to,
    return_origin,
  } = req.body;
  const email = String(customer.email).trim();
  const customerName =
    customer.name && String(customer.name).trim() ? String(customer.name).trim() : 'LeActioner';
  const paneldxIdMatu = parsePanelDxIdMatu(id_matu);
  const paneldxIdClie = parsePanelDxIdClie(id_clie);
  const paneldxIdPlano = parsePanelDxIdPlano(id_plano);

  try {
    const product = await pool.query('SELECT * FROM products WHERE sku = $1', [String(sku).trim()]);
    if (product.rows.length === 0) {
      return res.status(404).json({ error: 'Produto não cadastrado' });
    }

    const item = product.rows[0];
    if (item.type === 'PANELDX_ASSESSMENT' && !paneldxIdMatu) {
      return res.status(400).json({ error: 'id_matu inválido para produto PanelDX' });
    }
    if (item.type === 'PANELDX_SUBSCRIPTION' && (!paneldxIdClie || !paneldxIdPlano)) {
      return res.status(400).json({ error: 'id_clie e id_plano obrigatórios para assinatura PanelDX' });
    }
    if (item.type === 'PANELDX_ADDON' && (!paneldxIdClie || !paneldxIdPlano)) {
      return res.status(400).json({ error: 'id_clie e id_plano (addon) obrigatórios para pacote PanelDX' });
    }

    const userResult = await pool.query(
      `INSERT INTO users (email, full_name)
       VALUES ($1, $2)
       ON CONFLICT (email)
       DO UPDATE SET full_name = COALESCE(NULLIF(EXCLUDED.full_name, ''), users.full_name)
       RETURNING id, email, full_name`,
      [email, customerName]
    );
    const user = userResult.rows[0];

    let externalResourceId = paneldxIdMatu;
    const amountNum = amount != null ? Number(amount) : NaN;
    const valorNegociado =
      Number.isFinite(amountNum) && amountNum > 0 ? Math.round(amountNum * 100) / 100 : null;

    if (
      (item.type === 'PANELDX_SUBSCRIPTION' || item.type === 'PANELDX_ADDON') &&
      (valorNegociado == null || valorNegociado <= 0)
    ) {
      return res.status(400).json({
        error:
          'amount (valor do plano/add-on) é obrigatório e deve ser > 0. Não use valor fixo do .env.',
      });
    }

    if (item.type === 'PANELDX_SUBSCRIPTION') {
      externalResourceId = JSON.stringify({
        id_clie: Number(paneldxIdClie),
        id_plano: Number(paneldxIdPlano),
        id_matu: paneldxIdMatu ? Number(paneldxIdMatu) : null,
        plano_nome: String(plano_nome || '').trim(),
        periodicidade: String(periodicidade || '').trim(),
        valor_negociado: valorNegociado,
      });
    } else if (item.type === 'PANELDX_ADDON') {
      externalResourceId = JSON.stringify({
        id_clie: Number(paneldxIdClie),
        id_plano_addon: Number(paneldxIdPlano),
        quantidade: Number(req.body.quantidade || 1),
        plano_nome: String(plano_nome || '').trim(),
        valor_negociado: valorNegociado,
      });
    }

    const orderResult = await pool.query(
      `INSERT INTO orders (user_id, product_id, status, payment_url, external_resource_id)
       VALUES ($1, $2, 'PENDING', $3, $4)
       RETURNING id, status, created_at`,
      [user.id, item.id, String(webhook_url).trim(), externalResourceId]
    );
    const order = orderResult.rows[0];

    await pool.query(
      `UPDATE orders SET gateway_ref = $1 WHERE id = $2`,
      [`hub:${String(client_id).trim()}:${order.id}`, order.id]
    );

    console.log(`📥 [HUB PLATFORMA] Novo pedido de pagamento recebido do cliente: ${client_id}`);
    console.log(
      `   SKU: ${sku} | Valor: ${amount} | Pedido: ${order.id} | recurso: ${externalResourceId} | Callback: ${webhook_url}`
    );

    const checkoutUrl =
      item.type === 'PANELDX_ADDON'
        ? buildPanelDxDirectCheckoutUrl(
            order.id,
            email,
            hub_public_url,
            return_to,
            paneldxIdClie,
            return_origin,
            paneldxIdPlano
          )
        : buildCheckoutUrl(order.id, email, hub_public_url, return_to, client_id, return_origin);
    console.log(`   checkout_url: ${checkoutUrl}`);

    return res.status(201).json({
      success: true,
      payment_id: order.id,
      checkout_url: checkoutUrl,
    });
  } catch (err) {
    console.error('❌ Erro em POST /v1/payments:', err.message);
    return res.status(500).json({ error: 'Erro interno no servidor' });
  }
});

app.post('/webhook', async (req, res) => {
  const { email, name, sku, document_id, phone, company, address, city, state } = req.body;

  if (!email || !name || !sku) {
    return res.status(400).json({ error: 'Campos obrigatórios: email, name, sku' });
  }

  try {
    // 1. Busca o produto no Postgres
    const product = await pool.query('SELECT * FROM products WHERE sku = $1', [sku]);
    
    if (product.rows.length === 0) {
        console.log(`⚠️ Alerta: Tentativa de compra de SKU inexistente: ${sku}`);
        return res.status(404).json({ error: 'Produto não cadastrado' });
    }

    const item = product.rows[0];
    // 2. Busca ou cria o LeActioner centralizado por e-mail
    const userResult = await pool.query(
      `INSERT INTO users (email, full_name, document_id, phone, company, address, city, state)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
       ON CONFLICT (email)
       DO UPDATE SET
         full_name = EXCLUDED.full_name,
         document_id = COALESCE(EXCLUDED.document_id, users.document_id),
         phone = COALESCE(EXCLUDED.phone, users.phone),
         company = COALESCE(EXCLUDED.company, users.company),
         address = COALESCE(EXCLUDED.address, users.address),
         city = COALESCE(EXCLUDED.city, users.city),
         state = COALESCE(EXCLUDED.state, users.state)
       RETURNING id, email, full_name, document_id, phone, company, address, city, state`,
      [email, name, document_id ?? null, phone ?? null, company ?? null, address ?? null, city ?? null, state ?? null]
    );
    const user = userResult.rows[0];

    // 3. Cria o pedido inicial como PENDING, vinculando LeActioner e produto
    const orderResult = await pool.query(
      `INSERT INTO orders (user_id, product_id, status)
       VALUES ($1, $2, 'PENDING')
       RETURNING id, status, created_at`,
      [user.id, item.id]
    );
    const order = orderResult.rows[0];

    console.log(`✅ Processando: ${item.name} para o LeActioner ${email}`);
    console.log(`🧾 Pedido ${order.id} criado com status ${order.status}`);

    // Lógica de Direcionamento
    if (item.type === 'MOODLE_COURSE') {
      console.log(`🎓 [Moodle] Preparando matrícula no Curso ID: ${item.external_resource_id}`);
    } else if (item.type === 'PANELDX_ASSESSMENT') {
      console.log(`📊 [PanelDX] Gerando token de Assessment: ${item.external_resource_id}`);
    }

    res.status(200).json({
      message: 'Sucesso!',
      produto: item.name,
      user: {
        id: user.id,
        email: user.email,
        name: user.full_name,
        document_id: user.document_id,
        phone: user.phone,
        company: user.company,
        address: user.address,
        city: user.city,
        state: user.state
      },
      order: { id: order.id, status: order.status }
    });
  } catch (err) {
    console.error('❌ Erro no Orquestrador:', err.message);
    res.status(500).json({ error: 'Erro interno no servidor' });
  }
});

app.post('/simular-pagamento', async (req, res) => {
  const { order_id } = req.body;

  if (!order_id) {
    return res.status(400).json({ error: 'Campo obrigatório: order_id' });
  }

  try {
    const orderCheck = await pool.query(
      `SELECT o.id, o.status, o.external_resource_id AS id_matu, p.type AS product_type
       FROM orders o
       JOIN products p ON p.id = o.product_id
       WHERE o.id = $1`,
      [order_id]
    );

    if (orderCheck.rows.length === 0) {
      return res.status(404).json({ error: 'Pedido não encontrado' });
    }

    const orderMeta = orderCheck.rows[0];

    if (orderMeta.status === 'PAID') {
      return res.status(200).json({
        success: true,
        already_paid: true,
        message: 'Pedido já estava pago',
        order: { id: orderMeta.id, status: orderMeta.status },
        webhook_delivered: false,
      });
    }

    const { id_matu, product_type } = orderMeta;
    const idMatuForJwt = id_matu != null ? String(id_matu).trim() : '';

    if (product_type === 'PANELDX_ASSESSMENT' && !parsePanelDxIdMatu(idMatuForJwt)) {
      return res.status(422).json({
        error: 'Pedido PanelDX sem id_matu vinculado; pagamento não confirmado',
      });
    }

    const result = await fulfillOrderPayment(pool, order_id, JWT_SECRET, {
      paymentProvider: 'simulado',
    });

    return res.status(200).json({
      success: true,
      message: 'Pagamento simulado com sucesso',
      order: result.order,
      webhook_delivered: result.webhookDelivered,
    });
  } catch (err) {
    const status = err.statusCode || 500;
    if (status !== 500) {
      return res.status(status).json({ error: err.message });
    }
    console.error('❌ Erro ao simular pagamento:', err.message);
    return res.status(500).json({ error: 'Erro interno no servidor' });
  }
});

/** Configuração pública de pagamentos (Brick + assinatura) para o front-end. */
app.get('/config/payments', async (_req, res) => {
  const sub = getSubscriptionConfig();
  const checkoutMode = getCheckoutMode();
  const publicKey = getMercadoPagoPublicKey();
  const accessToken = getMercadoPagoAccessToken();
  const brickPair = await validateBrickCredentialPair();
  const pairHint =
    publicKey.startsWith('TEST-') && accessToken.startsWith('TEST-')
      ? 'ok_test_pair_prefix'
      : publicKey.startsWith('APP_USR-') && accessToken.startsWith('APP_USR-')
        ? 'ok_prod_pair_prefix'
        : 'check_pair';
  return res.status(200).json({
    mercadopago_enabled: isMercadoPagoConfigured(),
    checkout_mode: checkoutMode,
    public_key: publicKey,
    paneldx_payment_amount: getPanelDxPaymentAmount(),
    credentials_pair_hint: pairHint,
    brick_pair_valid: brickPair.valid,
    brick_pair_hint: brickPair.hint || brickPair.reason || null,
    server_tokenize_fallback: isServerTokenizeFallbackEnabled(),
    sandbox_mode: accessToken.startsWith('TEST-'),
    sandbox_payer_email: accessToken.startsWith('TEST-') ? getSandboxPayerEmail() : '',
    subscription: {
      reason: sub.reason,
      amount: sub.amount,
      currency_id: sub.currency_id,
      frequency: sub.frequency,
      frequency_type: sub.frequency_type,
    },
  });
});

/**
 * Pagamento único com Card Payment Brick (recomendado para sandbox TEST).
 * Body: { card_token_id, payment_method_id, payer_email, order_id, installments? }
 */
app.post('/payments/card', async (req, res) => {
  const { card_token_id, payment_method_id, payer_email, order_id, installments } = req.body || {};

  if (!card_token_id || !payment_method_id || !payer_email || !order_id) {
    return res.status(400).json({
      error: 'Campos obrigatórios: card_token_id, payment_method_id, payer_email, order_id',
    });
  }

  const email = resolveSandboxPayerEmail(payer_email);
  const orderId = String(order_id).trim();

  if (!email.includes('@')) {
    return res.status(400).json({ error: 'payer_email inválido' });
  }
  if (!isUuid(orderId)) {
    return res.status(400).json({ error: 'order_id inválido' });
  }

  try {
    const orderResult = await pool.query(
      `SELECT o.id, o.status, o.user_id,
              o.external_resource_id AS id_matu,
              o.external_resource_id,
              p.type AS product_type,
              p.name AS product_name
       FROM orders o
       JOIN products p ON p.id = o.product_id
       WHERE o.id = $1`,
      [orderId]
    );

    if (orderResult.rows.length === 0) {
      return res.status(404).json({ error: 'Pedido não encontrado' });
    }

    const orderRow = orderResult.rows[0];

    if (orderRow.status === 'PAID') {
      return res.status(200).json({
        success: true,
        already_paid: true,
        message: 'Pedido já estava pago',
        order: { id: orderRow.id, status: orderRow.status },
      });
    }

    const idMatu = orderRow.id_matu != null ? String(orderRow.id_matu).trim() : '';
    if (orderRow.product_type === 'PANELDX_ASSESSMENT' && !parsePanelDxIdMatu(idMatu)) {
      return res.status(422).json({ error: 'Pedido PanelDX sem id_matu vinculado' });
    }

    const { payment: mpPayment, usedServerTokenize } = await createCardPaymentWithSandboxFallback({
      payerEmail: email,
      cardTokenId: card_token_id,
      paymentMethodId: payment_method_id,
      amount: resolveOrderPaymentAmount(orderRow),
      externalReference: orderId,
      description: orderRow.product_name || 'PanelDX',
      installments: installments || 1,
    });

    if (usedServerTokenize) {
      console.log('✅ [Mercado Pago] Pagamento sandbox via fallback server-side (MP real aprovado).');
    }

    if (!isCardPaymentSuccess(mpPayment)) {
      const hint = mapMpStatusDetailHint(mpPayment.status_detail);
      console.warn(
        `⚠️ [Mercado Pago] Pagamento rejeitado: ${mpPayment.status} / ${mpPayment.status_detail}`,
        hint ? `| ${hint}` : ''
      );
      return res.status(402).json({
        error: 'Pagamento não aprovado pelo Mercado Pago',
        mp_status: mpPayment.status,
        mp_status_detail: mpPayment.status_detail,
        hint,
        mp_response: mpPayment,
      });
    }

    const fulfillment = await fulfillOrderPayment(pool, orderId, JWT_SECRET, {
      gatewayReference: mpPayment.id != null ? String(mpPayment.id) : null,
      paymentProvider: 'mercadopago',
    });

    return res.status(201).json({
      success: true,
      message: usedServerTokenize
        ? 'Pagamento aprovado (sandbox server-side — atualize a Public Key no painel MP)'
        : 'Pagamento aprovado',
      server_tokenize_fallback: usedServerTokenize,
      mercadopago: {
        id: mpPayment.id,
        status: mpPayment.status,
        status_detail: mpPayment.status_detail,
      },
      order: fulfillment.order,
      webhook_delivered: fulfillment.webhookDelivered,
    });
  } catch (err) {
    const status = err.statusCode || 500;
    console.error('❌ Erro em POST /payments/card:', err.message);
    if (err.mpResponse) {
      console.error('   MP response:', JSON.stringify(err.mpResponse));
    }
    if (status !== 500) {
      return res.status(status).json({
        error: err.message,
        mp_response: err.mpResponse || undefined,
      });
    }
    return res.status(500).json({ error: 'Erro interno no servidor' });
  }
});

/**
 * Sandbox sem Brick — tokeniza no servidor (cartão APRO) quando Secure Fields / Public Key falham.
 * Body: { payer_email, order_id }
 */
app.post('/payments/sandbox-card', async (req, res) => {
  if (!isSandboxAccessToken() || !isServerTokenizeFallbackEnabled()) {
    return res.status(403).json({
      error: 'Pagamento sandbox sem Brick disponível apenas com MP_ACCESS_TOKEN TEST e MP_SERVER_TOKENIZE_FALLBACK=1',
    });
  }

  const { payer_email, order_id } = req.body || {};
  if (!payer_email || !order_id) {
    return res.status(400).json({ error: 'Campos obrigatórios: payer_email, order_id' });
  }

  const email = resolveSandboxPayerEmail(payer_email);
  const orderId = String(order_id).trim();

  if (!email.includes('@')) {
    return res.status(400).json({ error: 'payer_email inválido' });
  }
  if (!isUuid(orderId)) {
    return res.status(400).json({ error: 'order_id inválido' });
  }

  try {
    const orderResult = await pool.query(
      `SELECT o.id, o.status, o.user_id,
              o.external_resource_id AS id_matu,
              o.external_resource_id,
              p.type AS product_type,
              p.name AS product_name
       FROM orders o
       JOIN products p ON p.id = o.product_id
       WHERE o.id = $1`,
      [orderId]
    );

    if (orderResult.rows.length === 0) {
      return res.status(404).json({ error: 'Pedido não encontrado' });
    }

    const orderRow = orderResult.rows[0];

    if (orderRow.status === 'PAID') {
      return res.status(200).json({
        success: true,
        already_paid: true,
        message: 'Pedido já estava pago',
        order: { id: orderRow.id, status: orderRow.status },
      });
    }

    const idMatu = orderRow.id_matu != null ? String(orderRow.id_matu).trim() : '';
    if (orderRow.product_type === 'PANELDX_ASSESSMENT' && !parsePanelDxIdMatu(idMatu)) {
      return res.status(422).json({ error: 'Pedido PanelDX sem id_matu vinculado' });
    }

    const card = await createSandboxCardTokenServerSide();
    const mpPayment = await createCardPayment({
      payerEmail: email,
      cardTokenId: card.id,
      paymentMethodId: card.payment_method_id || 'master',
      amount: resolveOrderPaymentAmount(orderRow),
      externalReference: orderId,
      description: orderRow.product_name || 'PanelDX',
      installments: 1,
    });

    if (!isCardPaymentSuccess(mpPayment)) {
      const hint = mapMpStatusDetailHint(mpPayment.status_detail);
      return res.status(402).json({
        error: 'Pagamento não aprovado pelo Mercado Pago',
        mp_status: mpPayment.status,
        mp_status_detail: mpPayment.status_detail,
        hint,
      });
    }

    console.log('✅ [Mercado Pago] Pagamento sandbox sem Brick (tokenização server-side).');

    const fulfillment = await fulfillOrderPayment(pool, orderId, JWT_SECRET, {
      gatewayReference: mpPayment.id != null ? String(mpPayment.id) : null,
      paymentProvider: 'mercadopago',
    });

    return res.status(201).json({
      success: true,
      message: 'Pagamento sandbox aprovado (sem Brick)',
      server_tokenize_fallback: true,
      mercadopago: {
        id: mpPayment.id,
        status: mpPayment.status,
        status_detail: mpPayment.status_detail,
      },
      order: fulfillment.order,
      webhook_delivered: fulfillment.webhookDelivered,
    });
  } catch (err) {
    const status = err.statusCode || 500;
    console.error('❌ Erro em POST /payments/sandbox-card:', err.message);
    if (status !== 500) {
      return res.status(status).json({ error: err.message, mp_response: err.mpResponse || undefined });
    }
    return res.status(500).json({ error: 'Erro interno no servidor' });
  }
});

/**
 * Checkout Transparente — assinatura recorrente Mercado Pago (preapproval).
 * Body: { card_token_id, payer_email, order_id? }
 */
app.post('/subscriptions/preapproval', async (req, res) => {
  const { card_token_id, payer_email, order_id } = req.body || {};

  if (!card_token_id || !payer_email) {
    return res.status(400).json({
      error: 'Campos obrigatórios: card_token_id, payer_email',
    });
  }

  const email = resolveSandboxPayerEmail(payer_email);
  const orderId = order_id ? String(order_id).trim() : '';

  if (!email.includes('@')) {
    return res.status(400).json({ error: 'payer_email inválido' });
  }

  if (orderId && !isUuid(orderId)) {
    return res.status(400).json({ error: 'order_id inválido' });
  }

  try {
    let orderRow = null;
    let userId = null;

    if (orderId) {
      const orderResult = await pool.query(
        `SELECT o.id, o.status, o.user_id, o.external_resource_id AS id_matu,
                o.external_resource_id, p.type AS product_type, p.name AS product_name
         FROM orders o
         JOIN products p ON p.id = o.product_id
         WHERE o.id = $1`,
        [orderId]
      );

      if (orderResult.rows.length === 0) {
        return res.status(404).json({ error: 'Pedido não encontrado' });
      }

      orderRow = orderResult.rows[0];
      userId = orderRow.user_id;

      if (orderRow.status === 'PAID') {
        return res.status(200).json({
          success: true,
          already_paid: true,
          message: 'Pedido já estava pago',
          order: { id: orderRow.id, status: orderRow.status },
        });
      }

      const idMatu = orderRow.id_matu != null ? String(orderRow.id_matu).trim() : '';
      if (orderRow.product_type === 'PANELDX_ASSESSMENT' && !parsePanelDxIdMatu(idMatu)) {
        return res.status(422).json({
          error: 'Pedido PanelDX sem id_matu vinculado',
        });
      }
    } else {
      return res.status(400).json({
        error: 'order_id obrigatório: a cobrança usa o valor dinâmico do pedido (plano/add-on).',
      });
    }

    const orderPaymentAmount = resolveOrderPaymentAmount(orderRow);
    const mpResponse = await createPreapprovalSubscription({
      payerEmail: email,
      cardTokenId: card_token_id,
      externalReference: orderId || undefined,
      amount: orderPaymentAmount,
      reason: orderRow?.product_name || undefined,
    });

    if (!isPreapprovalSuccess(mpResponse)) {
      return res.status(402).json({
        error: 'Assinatura não autorizada pelo Mercado Pago',
        mp_status: mpResponse.status,
        mp_response: mpResponse,
      });
    }

    const subCfg = getSubscriptionConfig();
    const mpId = mpResponse.id ? String(mpResponse.id) : null;

    const subInsert = await pool.query(
      `INSERT INTO subscriptions (
         user_id, order_id, mp_preapproval_id, status, amount, currency_id,
         frequency, frequency_type, reason, payer_email, raw_response, updated_at
       )
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, CURRENT_TIMESTAMP)
       ON CONFLICT (mp_preapproval_id)
       DO UPDATE SET
         status = EXCLUDED.status,
         raw_response = EXCLUDED.raw_response,
         updated_at = CURRENT_TIMESTAMP
       RETURNING id, mp_preapproval_id, status`,
      [
        userId,
        orderId || null,
        mpId,
        mpResponse.status,
        orderPaymentAmount,
        subCfg.currency_id,
        subCfg.frequency,
        subCfg.frequency_type,
        orderRow?.product_name || subCfg.reason,
        email,
        JSON.stringify(mpResponse),
      ]
    );

    let fulfillment = null;

    if (orderId) {
      fulfillment = await fulfillOrderPayment(pool, orderId, JWT_SECRET, {
        gatewayReference: mpId,
        paymentProvider: 'mercadopago',
        mpPreapprovalId: mpId,
      });
    }

    console.log(
      `✅ [Mercado Pago] Assinatura ${mpId} | status=${mpResponse.status} | pedido=${orderId || 'N/A'}`
    );

    return res.status(201).json({
      success: true,
      message: 'Assinatura criada com sucesso',
      subscription: {
        id: subInsert.rows[0].id,
        mp_preapproval_id: subInsert.rows[0].mp_preapproval_id,
        status: subInsert.rows[0].status,
      },
      mercadopago: {
        id: mpResponse.id,
        status: mpResponse.status,
      },
      order: fulfillment?.order || (orderRow ? { id: orderRow.id, status: orderRow.status } : null),
      webhook_delivered: fulfillment?.webhookDelivered ?? false,
    });
  } catch (err) {
    const status = err.statusCode || 500;
    console.error('❌ Erro em POST /subscriptions/preapproval:', err.message);
    if (err.mpResponse) {
      console.error('   MP response:', JSON.stringify(err.mpResponse));
    }
    if (status !== 500) {
      return res.status(status).json({
        error: err.message,
        mp_response: err.mpResponse || undefined,
      });
    }
    return res.status(500).json({ error: 'Erro interno no servidor' });
  }
});

/** Status público de um pedido (checkout PanelDX no dashboard). */
app.get('/orders/:orderId/checkout', async (req, res) => {
  const orderId = String(req.params.orderId || '').trim();
  if (!isUuid(orderId)) {
    return res.status(400).json({ error: 'order_id inválido' });
  }

  try {
    const result = await pool.query(
      `SELECT
         o.id,
         o.status,
         o.created_at,
         o.external_resource_id,
         p.name AS product_name,
         p.type AS product_type,
         p.external_resource_id AS product_external_resource_id
       FROM orders o
       JOIN products p ON p.id = o.product_id
       WHERE o.id = $1`,
      [orderId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Pedido não encontrado' });
    }

    const orderRow = result.rows[0];
    return res.status(200).json({
      order: orderRow,
      payment_amount: resolveOrderPaymentAmount(orderRow),
    });
  } catch (err) {
    console.error('❌ Erro em GET /orders/:orderId/checkout:', err.message);
    return res.status(500).json({ error: 'Erro interno no servidor' });
  }
});

/**
 * Login / primeiro acesso do LeActioner (e-mail + senha).
 * Body: { email, password, name? }
 */
app.post('/auth/login', async (req, res) => {
  try {
    const result = await loginOrRegister(pool, {
      email: req.body?.email,
      password: req.body?.password,
      name: req.body?.name,
    });
    const token = jwt.sign(
      { sub: result.user.id, email: result.user.email },
      JWT_SECRET,
      { expiresIn: '12h' }
    );
    return res.status(200).json({
      authenticated: true,
      created: Boolean(result.created),
      password_set: Boolean(result.passwordSet),
      user: result.user,
      token,
    });
  } catch (err) {
    const status = err.status || 500;
    if (status >= 500) {
      console.error('❌ Erro em POST /auth/login:', err.message);
    }
    return res.status(status).json({
      authenticated: false,
      error: status >= 500 ? 'Erro interno no servidor' : err.message,
    });
  }
});

app.get('/my-orders/:email', async (req, res) => {
  const { email } = req.params;

  if (!email) {
    return res.status(400).json({ error: 'Parâmetro obrigatório: email' });
  }

  try {
    const userResult = await pool.query(
      `SELECT id, email, full_name, document_id, phone, company, address, city, state
       FROM users
       WHERE email = $1`,
      [email]
    );

    if (userResult.rows.length === 0) {
      return res.status(404).json({ error: 'LeActioner não encontrado' });
    }

    const user = userResult.rows[0];

    const ordersResult = await pool.query(
      `SELECT
         o.id,
         o.status,
         o.created_at,
         o.external_resource_id,
         p.name AS product_name,
         p.type AS product_type,
         p.external_resource_id AS product_external_resource_id
       FROM orders o
       JOIN products p ON p.id = o.product_id
       WHERE o.user_id = $1
       ORDER BY o.created_at DESC`,
      [user.id]
    );

    return res.status(200).json({
      user: {
        id: user.id,
        email: user.email,
        name: user.full_name,
        document_id: user.document_id,
        phone: user.phone,
        company: user.company,
        address: user.address,
        city: user.city,
        state: user.state
      },
      orders: ordersResult.rows
    });
  } catch (err) {
    console.error('❌ Erro ao buscar pedidos do LeActioner:', err.message);
    return res.status(500).json({ error: 'Erro interno no servidor' });
  }
});

const USER_PATCHABLE = ['full_name', 'document_id', 'phone', 'company', 'address', 'city', 'state'];

app.patch('/users/:email', async (req, res) => {
  const email = decodeURIComponent(req.params.email || '');

  if (!email || !email.includes('@')) {
    return res.status(400).json({ error: 'E-mail inválido' });
  }

  const updates = {};
  for (const key of USER_PATCHABLE) {
    if (Object.prototype.hasOwnProperty.call(req.body, key)) {
      const v = req.body[key];
      updates[key] = v === undefined ? null : v;
    }
  }

  if (Object.keys(updates).length === 0) {
    return res.status(400).json({ error: 'Nenhum campo para atualizar' });
  }

  if (updates.full_name !== undefined && String(updates.full_name).trim() === '') {
    return res.status(400).json({ error: 'full_name não pode ser vazio' });
  }

  const cols = Object.keys(updates);
  const values = Object.values(updates);
  const setClause = cols.map((c, i) => `${c} = $${i + 2}`).join(', ');

  try {
    const result = await pool.query(
      `UPDATE users SET ${setClause}
       WHERE email = $1
       RETURNING id, email, full_name, document_id, phone, company, address, city, state`,
      [email, ...values]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'LeActioner não encontrado' });
    }

    const u = result.rows[0];
    return res.status(200).json({
      user: {
        id: u.id,
        email: u.email,
        name: u.full_name,
        document_id: u.document_id,
        phone: u.phone,
        company: u.company,
        address: u.address,
        city: u.city,
        state: u.state
      }
    });
  } catch (err) {
    console.error('❌ Erro ao atualizar usuário:', err.message);
    return res.status(500).json({ error: 'Erro interno no servidor' });
  }
});

app.patch('/orders/:id', async (req, res) => {
  const { id } = req.params;

  if (!isUuid(id)) {
    return res.status(400).json({ error: 'ID de pedido inválido' });
  }

  if (!Object.prototype.hasOwnProperty.call(req.body, 'external_resource_id')) {
    return res.status(400).json({ error: 'Campo obrigatório: external_resource_id' });
  }

  const external_resource_id =
    req.body.external_resource_id === null || req.body.external_resource_id === ''
      ? null
      : String(req.body.external_resource_id);

  try {
    const result = await pool.query(
      `UPDATE orders
       SET external_resource_id = $1
       WHERE id = $2
       RETURNING id, status, external_resource_id, created_at`,
      [external_resource_id, id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Pedido não encontrado' });
    }

    return res.status(200).json({ order: result.rows[0] });
  } catch (err) {
    console.error('❌ Erro ao atualizar pedido:', err.message);
    return res.status(500).json({ error: 'Erro interno no servidor' });
  }
});

app.post('/sync-cart', async (req, res) => {
  const { email, items } = req.body;

  if (!email || !Array.isArray(items)) {
    return res.status(400).json({ error: 'Campos obrigatórios: email, items (array de SKUs)' });
  }

  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    const userResult = await client.query(
      `INSERT INTO users (email, full_name)
       VALUES ($1, 'LeActioner')
       ON CONFLICT (email)
       DO UPDATE SET full_name = users.full_name
       RETURNING id`,
      [email]
    );
    const userId = userResult.rows[0].id;

    const orderIds = [];
    for (const sku of items) {
      if (sku == null || String(sku).trim() === '') {
        await client.query('ROLLBACK');
        return res.status(400).json({ error: 'Itens inválidos: SKUs não podem ser vazios' });
      }

      const product = await client.query('SELECT id FROM products WHERE sku = $1', [String(sku).trim()]);
      if (product.rows.length === 0) {
        await client.query('ROLLBACK');
        return res.status(404).json({ error: `Produto não cadastrado: ${sku}` });
      }

      const orderResult = await client.query(
        `INSERT INTO orders (user_id, product_id, status)
         VALUES ($1, $2, 'PENDING')
         RETURNING id`,
        [userId, product.rows[0].id]
      );
      orderIds.push(orderResult.rows[0].id);
    }

    await client.query('COMMIT');

    return res.status(200).json({
      success: true,
      message: 'Carrinho sincronizado',
      user_id: userId,
      order_ids: orderIds,
    });
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    console.error('❌ Erro em /sync-cart:', err.message);
    return res.status(500).json({ error: 'Erro interno no servidor' });
  } finally {
    client.release();
  }
});

registerCrmTrackingRoutes(app, pool);
registerEntitlementsRoutes(app, pool);
registerAdminRoutes(app, pool, { jwtSecret: JWT_SECRET });
startOutboxWorker(pool);

// API na 4001; Action Hub (Next.js) na 4000
const PORT = process.env.GATEWAY_PORT || 4001;
app.listen(PORT, () => console.log(`🚀 Orquestrador ActionHub Online na porta ${PORT}`));