'use strict';

/**
 * OAuth de recebedores (parceiros) — tokens na conta do parceiro.
 * Não usa mercadopago.js / MP_ACCESS_TOKEN.
 */

const crypto = require('crypto');
const axios = require('axios');
const { authenticateApp, extractCallerSecret } = require('./entitlements-api');
const { encryptSellerSecret, decryptSellerSecret } = require('../lib/seller-crypto');

const MP_AUTH_URL = 'https://auth.mercadopago.com.br/authorization';
const MP_OAUTH_TOKEN_URL = 'https://api.mercadopago.com/oauth/token';
const REFRESH_WINDOW_MS = 15 * 24 * 60 * 60 * 1000;
const STATE_TTL_MS = 15 * 60 * 1000;

function sellerPaymentsEnabled() {
  return String(process.env.SELLER_PAYMENTS_ENABLED || '').trim().toLowerCase() === 'true';
}

function sellerAppIds() {
  return String(process.env.SELLER_APP_IDS || '')
    .split(',')
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
}

function isSellerAppAllowed(appId) {
  const id = String(appId || '').trim().toLowerCase();
  const allowed = sellerAppIds();
  return Boolean(id) && allowed.includes(id);
}

function stateSecret() {
  const value = String(process.env.SELLER_STATE_SECRET || '').trim();
  if (!value || value.length < 16) {
    const err = new Error('SELLER_STATE_SECRET ausente ou curta');
    err.statusCode = 503;
    throw err;
  }
  return value;
}

function mpClientId() {
  return String(process.env.MP_CLIENT_ID || '').trim();
}

function mpClientSecret() {
  return String(process.env.MP_CLIENT_SECRET || '').trim();
}

function mpRedirectUri() {
  return String(
    process.env.MP_SELLER_REDIRECT_URI || 'https://api.actionhub.com.br/v1/sellers/oauth/callback'
  ).trim();
}

function originOf(url) {
  try {
    const u = new URL(String(url || '').trim());
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return null;
    return u.origin;
  } catch {
    return null;
  }
}

function returnToAllowed(returnTo, allowedOrigins) {
  const raw = String(returnTo || '').trim();
  if (!raw) return { ok: false, error: 'return_to obrigatório' };
  let parsed;
  try {
    parsed = new URL(raw);
  } catch {
    return { ok: false, error: 'return_to inválido' };
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return { ok: false, error: 'return_to inválido' };
  }
  const allowed = Array.isArray(allowedOrigins)
    ? allowedOrigins.map((item) => originOf(item)).filter(Boolean)
    : [];
  if (allowed.length === 0) {
    return { ok: false, error: 'app sem return_origins cadastradas' };
  }
  if (!allowed.includes(parsed.origin)) {
    return { ok: false, error: 'return_to não autorizado para este aplicativo' };
  }
  return { ok: true, url: parsed.toString() };
}

function b64url(buf) {
  return Buffer.from(buf)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');
}

function fromB64url(str) {
  const pad = str.length % 4 === 0 ? '' : '='.repeat(4 - (str.length % 4));
  const raw = String(str).replace(/-/g, '+').replace(/_/g, '/') + pad;
  return Buffer.from(raw, 'base64');
}

function signState(payload, secret = stateSecret()) {
  const body = b64url(JSON.stringify(payload));
  const sig = crypto.createHmac('sha256', secret).update(body).digest();
  return `${body}.${b64url(sig)}`;
}

function verifyState(token, secret = stateSecret()) {
  const parts = String(token || '').split('.');
  if (parts.length !== 2) return { ok: false, error: 'state inválido' };
  const [body, sig] = parts;
  const expected = crypto.createHmac('sha256', secret).update(body).digest();
  const given = fromB64url(sig);
  if (given.length !== expected.length || !crypto.timingSafeEqual(given, expected)) {
    return { ok: false, error: 'state inválido' };
  }
  let payload;
  try {
    payload = JSON.parse(fromB64url(body).toString('utf8'));
  } catch {
    return { ok: false, error: 'state inválido' };
  }
  const exp = Number(payload.exp);
  if (!Number.isFinite(exp) || exp < Date.now()) {
    return { ok: false, error: 'state expirado' };
  }
  return { ok: true, payload };
}

function signChargeToken(chargeId, secret = stateSecret()) {
  const body = b64url(String(chargeId));
  const sig = crypto.createHmac('sha256', secret).update(`charge:${body}`).digest();
  return `${body}.${b64url(sig)}`;
}

function verifyChargeToken(chargeId, token, secret = stateSecret()) {
  const expected = signChargeToken(chargeId, secret);
  const a = Buffer.from(String(token || ''), 'utf8');
  const b = Buffer.from(expected, 'utf8');
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
    return false;
  }
  return true;
}

async function authSellerApp(req, pool) {
  const secret = extractCallerSecret(req);
  if (!secret) {
    return {
      ok: false,
      status: 401,
      error: 'Credencial ausente. Envie Authorization: Bearer <secret> ou header X-App-Secret.',
    };
  }
  const claimedAppId = String(
    req.body?.app_id || req.query?.app_id || req.headers['x-app-id'] || ''
  )
    .trim()
    .toLowerCase();
  if (!claimedAppId) {
    return { ok: false, status: 400, error: 'Campo obrigatório: app_id' };
  }
  if (!isSellerAppAllowed(claimedAppId)) {
    return { ok: false, status: 403, error: 'aplicativo não autorizado para recebedores' };
  }
  const auth = await authenticateApp(pool, claimedAppId, secret);
  if (!auth.ok) return auth;
  const appId = String(auth.app.app_id).trim().toLowerCase();
  if (appId !== claimedAppId) {
    return { ok: false, status: 401, error: 'app_id não corresponde à credencial' };
  }
  return { ok: true, app: auth.app, appId };
}

async function exchangeAuthorizationCode(code, deps = {}) {
  const post = deps.postOauthToken || ((body) => axios.post(MP_OAUTH_TOKEN_URL, body));
  const clientId = mpClientId();
  const clientSecret = mpClientSecret();
  if (!clientId || !clientSecret) {
    const err = new Error('MP_CLIENT_ID/MP_CLIENT_SECRET ausentes');
    err.statusCode = 503;
    throw err;
  }
  const { data } = await post({
    client_id: clientId,
    client_secret: clientSecret,
    grant_type: 'authorization_code',
    code: String(code),
    redirect_uri: mpRedirectUri(),
  });
  return data;
}

async function refreshAccessToken(refreshToken, deps = {}) {
  const post = deps.postOauthToken || ((body) => axios.post(MP_OAUTH_TOKEN_URL, body));
  const clientId = mpClientId();
  const clientSecret = mpClientSecret();
  if (!clientId || !clientSecret) {
    const err = new Error('MP_CLIENT_ID/MP_CLIENT_SECRET ausentes');
    err.statusCode = 503;
    throw err;
  }
  const { data } = await post({
    client_id: clientId,
    client_secret: clientSecret,
    grant_type: 'refresh_token',
    refresh_token: String(refreshToken),
  });
  return data;
}

async function upsertSellerAccount(pool, {
  appId,
  sellerRef,
  tokenPayload,
}) {
  const access = String(tokenPayload.access_token || '');
  const refresh = String(tokenPayload.refresh_token || '');
  const publicKey = String(tokenPayload.public_key || '').trim();
  if (!access || !refresh || !publicKey) {
    const err = new Error('resposta OAuth incompleta');
    err.statusCode = 502;
    throw err;
  }
  const expiresIn = Number(tokenPayload.expires_in) || 21600;
  const expiresAt = new Date(Date.now() + expiresIn * 1000);
  const accessEnc = encryptSellerSecret(access);
  const refreshEnc = encryptSellerSecret(refresh);
  const mpUserId = tokenPayload.user_id != null ? Number(tokenPayload.user_id) : null;
  const nickname = tokenPayload.nickname != null ? String(tokenPayload.nickname) : null;

  const existing = await pool.query(
    `SELECT id FROM seller_accounts WHERE app_id = $1 AND seller_ref = $2 LIMIT 1`,
    [appId, sellerRef]
  );
  if (existing.rows[0]) {
    const r = await pool.query(
      `UPDATE seller_accounts SET
         mp_user_id = $2,
         mp_nickname = COALESCE($3, mp_nickname),
         access_token_enc = $4,
         refresh_token_enc = $5,
         public_key = $6,
         expires_at = $7,
         status = 'connected',
         last_error = NULL,
         connected_at = now(),
         updated_at = now()
       WHERE id = $1
       RETURNING *`,
      [
        existing.rows[0].id,
        mpUserId,
        nickname,
        accessEnc,
        refreshEnc,
        publicKey,
        expiresAt.toISOString(),
      ]
    );
    return r.rows[0];
  }

  const inserted = await pool.query(
    `INSERT INTO seller_accounts (
       app_id, seller_ref, mp_user_id, mp_nickname,
       access_token_enc, refresh_token_enc, public_key, expires_at, status
     ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'connected')
     RETURNING *`,
    [
      appId,
      sellerRef,
      mpUserId,
      nickname,
      accessEnc,
      refreshEnc,
      publicKey,
      expiresAt.toISOString(),
    ]
  );
  return inserted.rows[0];
}

async function getSellerAccount(pool, appId, sellerRef) {
  const r = await pool.query(
    `SELECT * FROM seller_accounts WHERE app_id = $1 AND seller_ref = $2 LIMIT 1`,
    [appId, sellerRef]
  );
  return r.rows[0] || null;
}

/**
 * Devolve access token em claro, renovando se faltar menos de 15 dias.
 */
async function ensureSellerAccessToken(pool, account, deps = {}) {
  if (!account || account.status === 'revoked') {
    const err = new Error('conta do recebedor indisponível');
    err.statusCode = 409;
    throw err;
  }
  const expiresAt = new Date(account.expires_at).getTime();
  const needsRefresh = !Number.isFinite(expiresAt) || expiresAt - Date.now() < REFRESH_WINDOW_MS;
  if (!needsRefresh) {
    return decryptSellerSecret(account.access_token_enc);
  }
  try {
    const refresh = decryptSellerSecret(account.refresh_token_enc);
    const data = await refreshAccessToken(refresh, deps);
    const updated = await upsertSellerAccount(pool, {
      appId: account.app_id,
      sellerRef: account.seller_ref,
      tokenPayload: {
        ...data,
        public_key: data.public_key || account.public_key,
        nickname: data.nickname || account.mp_nickname,
        user_id: data.user_id != null ? data.user_id : account.mp_user_id,
      },
    });
    return decryptSellerSecret(updated.access_token_enc);
  } catch (err) {
    await pool.query(
      `UPDATE seller_accounts SET status = 'error', last_error = $2, updated_at = now()
       WHERE id = $1`,
      [account.id, String(err.message || 'falha ao renovar').slice(0, 200)]
    );
    const out = new Error('Reconecte sua conta');
    out.statusCode = 409;
    throw out;
  }
}

function disabled404(res) {
  return res.status(404).json({ error: 'não encontrado' });
}

function registerSellerOAuthRoutes(app, pool, deps = {}) {
  app.post('/v1/sellers/connect-link', async (req, res) => {
    if (!sellerPaymentsEnabled()) return disabled404(res);
    try {
      const auth = await authSellerApp(req, pool);
      if (!auth.ok) return res.status(auth.status).json({ error: auth.error });
      const sellerRef = String(req.body?.seller_ref || '').trim();
      if (!sellerRef || sellerRef.length > 120) {
        return res.status(400).json({ error: 'seller_ref obrigatório (até 120)' });
      }
      const check = returnToAllowed(req.body?.return_to, auth.app.return_origins);
      if (!check.ok) return res.status(400).json({ error: check.error });
      const clientId = mpClientId();
      if (!clientId) return res.status(503).json({ error: 'MP_CLIENT_ID ausente' });
      const state = signState({
        app_id: auth.appId,
        seller_ref: sellerRef,
        return_to: check.url,
        exp: Date.now() + STATE_TTL_MS,
      });
      const url = new URL(MP_AUTH_URL);
      url.searchParams.set('client_id', clientId);
      url.searchParams.set('response_type', 'code');
      url.searchParams.set('platform_id', 'mp');
      url.searchParams.set('redirect_uri', mpRedirectUri());
      url.searchParams.set('state', state);
      return res.status(200).json({ url: url.toString() });
    } catch (err) {
      console.error('[sellers-oauth] connect-link', err.message);
      return res.status(err.statusCode || 500).json({ error: err.message });
    }
  });

  app.get('/v1/sellers/oauth/callback', async (req, res) => {
    if (!sellerPaymentsEnabled()) return disabled404(res);
    const failRedirect = (returnTo, motivo) => {
      try {
        const u = new URL(returnTo || 'https://actionhub.com.br/');
        u.searchParams.set('mp', 'erro');
        u.searchParams.set('motivo', String(motivo || 'falha').slice(0, 40));
        return res.redirect(302, u.toString());
      } catch {
        return res.status(400).send('retorno inválido');
      }
    };
    try {
      const stateCheck = verifyState(req.query.state);
      if (!stateCheck.ok) {
        return res.status(400).send(stateCheck.error);
      }
      const { app_id: appId, seller_ref: sellerRef, return_to: returnTo } = stateCheck.payload;
      const code = String(req.query.code || '').trim();
      if (!code) return failRedirect(returnTo, 'sem_codigo');
      const tokenPayload = await exchangeAuthorizationCode(code, deps);
      await upsertSellerAccount(pool, { appId, sellerRef, tokenPayload });
      const ok = new URL(returnTo);
      ok.searchParams.set('mp', 'ok');
      return res.redirect(302, ok.toString());
    } catch (err) {
      console.error('[sellers-oauth] callback', err.message);
      try {
        const stateCheck = verifyState(req.query.state);
        if (stateCheck.ok) return failRedirect(stateCheck.payload.return_to, 'oauth');
      } catch {
        /* ignore */
      }
      return res.status(502).send('falha na conexão');
    }
  });

  app.get('/v1/sellers/:ref', async (req, res) => {
    if (!sellerPaymentsEnabled()) return disabled404(res);
    try {
      const auth = await authSellerApp(req, pool);
      if (!auth.ok) return res.status(auth.status).json({ error: auth.error });
      const row = await getSellerAccount(pool, auth.appId, String(req.params.ref || '').trim());
      if (!row || row.status === 'revoked') {
        return res.status(200).json({
          connected: false,
          nickname: null,
          connected_at: null,
          status: row ? row.status : 'missing',
        });
      }
      return res.status(200).json({
        connected: row.status === 'connected',
        nickname: row.mp_nickname || null,
        connected_at: row.connected_at,
        status: row.status,
      });
    } catch (err) {
      return res.status(err.statusCode || 500).json({ error: err.message });
    }
  });

  app.delete('/v1/sellers/:ref', async (req, res) => {
    if (!sellerPaymentsEnabled()) return disabled404(res);
    try {
      const auth = await authSellerApp(req, pool);
      if (!auth.ok) return res.status(auth.status).json({ error: auth.error });
      const ref = String(req.params.ref || '').trim();
      const r = await pool.query(
        `UPDATE seller_accounts SET status = 'revoked', updated_at = now()
         WHERE app_id = $1 AND seller_ref = $2
         RETURNING id, status`,
        [auth.appId, ref]
      );
      if (!r.rows[0]) return res.status(404).json({ error: 'recebedor não encontrado' });
      return res.status(200).json({ status: 'revoked' });
    } catch (err) {
      return res.status(err.statusCode || 500).json({ error: err.message });
    }
  });
}

function registerSellerRoutes(app, pool, deps = {}) {
  registerSellerOAuthRoutes(app, pool, deps);
  // Lazy: evita dependência circular no require.
  require('./seller-charges').registerSellerChargeRoutes(app, pool, deps);
}

module.exports = {
  registerSellerRoutes,
  sellerPaymentsEnabled,
  isSellerAppAllowed,
  signState,
  verifyState,
  signChargeToken,
  verifyChargeToken,
  returnToAllowed,
  authSellerApp,
  upsertSellerAccount,
  getSellerAccount,
  ensureSellerAccessToken,
  exchangeAuthorizationCode,
  refreshAccessToken,
  STATE_TTL_MS,
  REFRESH_WINDOW_MS,
};
