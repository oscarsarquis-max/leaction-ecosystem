'use strict';

/**
 * API de leitura de entitlements para apps satélites (Fase 2 — Contract Service).
 *
 * GET /v1/entitlements?app_id=&subject_id=
 * Auth: Bearer <secret> ou header X-App-Secret / X-Hub-App-Secret
 *       (secret = app_registry.webhook_secret do app_id informado)
 */

const crypto = require('crypto');
const { viewCredits } = require('./credits-ops');

function secretsEqual(a, b) {
  const aa = Buffer.from(String(a || ''), 'utf8');
  const bb = Buffer.from(String(b || ''), 'utf8');
  if (aa.length === 0 || aa.length !== bb.length) return false;
  return crypto.timingSafeEqual(aa, bb);
}

function extractCallerSecret(req) {
  const headerSecret = String(
    req.headers['x-app-secret'] || req.headers['x-hub-app-secret'] || ''
  ).trim();
  if (headerSecret) return headerSecret;

  const auth = String(req.headers.authorization || '').trim();
  const m = /^Bearer\s+(.+)$/i.exec(auth);
  return m ? String(m[1] || '').trim() : '';
}

function emptyEntitlementResponse(appId, subjectId, reason) {
  const messages = {
    no_entitlement: 'Nenhum plano ativo ou saldo disponível para este subject.',
    expired: 'Plano ou saldo expirado.',
  };
  return {
    active: false,
    app_id: appId,
    subject_id: subjectId,
    reason,
    message: messages[reason] || messages.no_entitlement,
    entitlement: {
      credits: 0,
      premium: false,
      plan: null,
    },
    valid_until: null,
  };
}

function isSnapshotValid(validUntil) {
  if (validUntil == null) return true;
  const t = new Date(validUntil).getTime();
  if (Number.isNaN(t)) return false;
  return t > Date.now();
}

async function authenticateApp(pool, appId, secret) {
  const r = await pool.query(
    `SELECT app_id, name, active, webhook_secret, webhook_url, return_origins
     FROM app_registry
     WHERE app_id = $1
     LIMIT 1`,
    [appId]
  );
  if (r.rows.length === 0) {
    return { ok: false, status: 401, error: 'app_id desconhecido' };
  }
  const app = r.rows[0];
  if (!app.active) {
    return { ok: false, status: 403, error: 'app_id inativo' };
  }
  const expected = String(app.webhook_secret || '').trim();
  if (!expected) {
    return {
      ok: false,
      status: 503,
      error: 'app_id sem secret configurado no Hub (app_registry.webhook_secret)',
    };
  }
  if (!secretsEqual(secret, expected)) {
    return { ok: false, status: 401, error: 'credencial inválida para este app_id' };
  }
  return { ok: true, app };
}

/**
 * @param {import('pg').Pool} pool
 * @param {{ appId: string, subjectId: string }} params
 */
async function getEntitlementForSubject(pool, { appId, subjectId }) {
  const r = await pool.query(
    `SELECT app_id, subject_id, payload_json, valid_until, updated_at
     FROM entitlement_snapshots
     WHERE app_id = $1 AND subject_id = $2
     LIMIT 1`,
    [appId, subjectId]
  );

  if (r.rows.length === 0) {
    return emptyEntitlementResponse(appId, subjectId, 'no_entitlement');
  }

  const row = r.rows[0];
  const payload =
    row.payload_json && typeof row.payload_json === 'object'
      ? row.payload_json
      : {};
  const view = viewCredits(payload, Date.now(), row.valid_until);
  const packOnly = !view.principalActive && view.packCredits > 0;
  if (!view.principalActive && view.packCredits <= 0 && view.available <= 0) {
    return {
      ...emptyEntitlementResponse(appId, subjectId, payload.plan ? 'expired' : 'no_entitlement'),
      entitlement: {
        credits: 0,
        premium: false,
        plan: payload.plan || null,
        pack_credits: 0,
      },
      valid_until: view.principalUntil || row.valid_until,
    };
  }

  return {
    active: Boolean(payload.plan || payload.premium) && view.principalActive,
    app_id: row.app_id,
    subject_id: row.subject_id,
    reason: packOnly ? 'pack_only' : undefined,
    valid_until: view.principalUntil || row.valid_until,
    updated_at: row.updated_at,
    entitlement: {
      ...payload,
      credits: view.available,
      principal_credits: view.principalCredits,
      complementary_credits: view.complementaryCredits,
      pack_credits: view.packCredits,
      premium: view.principalActive,
      complementary: view.complementaryActive ? payload.complementary : payload.complementary,
    },
  };
}

function registerEntitlementsRoutes(app, pool) {
  app.get('/v1/entitlements', async (req, res) => {
    try {
      const appId = String(req.query.app_id || '').trim();
      const subjectId = String(req.query.subject_id || '').trim();

      if (!appId || !subjectId) {
        return res.status(400).json({
          error: 'Parâmetros obrigatórios: app_id e subject_id',
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

      const body = await getEntitlementForSubject(pool, { appId, subjectId });
      return res.status(200).json(body);
    } catch (err) {
      console.error('❌ Erro em GET /v1/entitlements:', err.message);
      return res.status(500).json({ error: 'Erro interno no servidor' });
    }
  });
}

module.exports = {
  registerEntitlementsRoutes,
  getEntitlementForSubject,
  authenticateApp,
  extractCallerSecret,
  isSnapshotValid,
  emptyEntitlementResponse,
};
