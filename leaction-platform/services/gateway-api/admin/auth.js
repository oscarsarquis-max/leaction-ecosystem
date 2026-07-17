'use strict';

/**
 * Autenticação das rotas /admin/* .
 *
 * Aceita:
 * 1) Authorization: Bearer <JWT> de usuário cujo e-mail está em HUB_ADMIN_EMAILS
 *    (default: admin@actionhub.com.br; também aceita HUB_SYSADMIN_EMAIL legado)
 * 2) Header X-Admin-Api-Key igual a HUB_ADMIN_API_KEY (quando configurado)
 */

const crypto = require('crypto');
const jwt = require('jsonwebtoken');

const DEFAULT_ADMIN_EMAILS = 'admin@actionhub.com.br,sysadmin@inove4us.com.br';

function secretsEqual(a, b) {
  const aa = Buffer.from(String(a || ''), 'utf8');
  const bb = Buffer.from(String(b || ''), 'utf8');
  if (aa.length === 0 || aa.length !== bb.length) return false;
  return crypto.timingSafeEqual(aa, bb);
}

function getAdminEmails() {
  const raw =
    process.env.HUB_ADMIN_EMAILS ||
    process.env.HUB_SYSADMIN_EMAIL ||
    DEFAULT_ADMIN_EMAILS;
  return String(raw)
    .split(',')
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
}

function extractBearer(req) {
  const auth = String(req.headers.authorization || '').trim();
  const m = /^Bearer\s+(.+)$/i.exec(auth);
  return m ? String(m[1] || '').trim() : '';
}

/**
 * @param {string} jwtSecret
 */
function createRequireAdminAuth(jwtSecret) {
  const secret = String(jwtSecret || process.env.JWT_SECRET || '').trim();

  return function requireAdminAuth(req, res, next) {
    const apiKeyExpected = String(process.env.HUB_ADMIN_API_KEY || '').trim();
    const apiKeyGot = String(req.headers['x-admin-api-key'] || '').trim();
    if (apiKeyExpected && apiKeyGot && secretsEqual(apiKeyGot, apiKeyExpected)) {
      req.admin = { via: 'api_key' };
      return next();
    }

    const token = extractBearer(req);
    if (!token) {
      return res.status(401).json({
        error:
          'Autenticação administrativa obrigatória (Bearer JWT de admin ou X-Admin-Api-Key).',
      });
    }

    if (!secret) {
      return res.status(503).json({ error: 'JWT_SECRET não configurado no Hub' });
    }

    try {
      const decoded = jwt.verify(token, secret);
      const email = String(decoded.email || '').trim().toLowerCase();
      if (!email || !getAdminEmails().includes(email)) {
        return res.status(403).json({ error: 'Acesso administrativo negado' });
      }
      req.admin = {
        via: 'jwt',
        email,
        userId: decoded.sub || null,
        role: 'admin',
      };
      return next();
    } catch {
      return res.status(401).json({ error: 'Token administrativo inválido ou expirado' });
    }
  };
}

module.exports = {
  createRequireAdminAuth,
  getAdminEmails,
  secretsEqual,
};
