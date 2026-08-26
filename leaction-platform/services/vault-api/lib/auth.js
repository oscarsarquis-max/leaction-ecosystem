'use strict';

const jwt = require('jsonwebtoken');

const JWT_TTL = '2h';

function vaultJwtSecret() {
  const secret = String(process.env.VAULT_JWT_SECRET || '').trim();
  if (!secret) {
    const err = new Error('VAULT_JWT_SECRET não configurado');
    err.status = 503;
    throw err;
  }
  return secret;
}

function signVaultToken({ id, email }) {
  return jwt.sign(
    { sub: String(id), email: String(email).trim().toLowerCase() },
    vaultJwtSecret(),
    { expiresIn: JWT_TTL, issuer: 'vault-api' }
  );
}

function extractBearer(req) {
  const auth = String(req.headers.authorization || '').trim();
  const m = /^Bearer\s+(.+)$/i.exec(auth);
  return m ? String(m[1] || '').trim() : '';
}

function clientIp(req) {
  const fwd = String(req.headers['x-forwarded-for'] || '')
    .split(',')[0]
    .trim();
  if (fwd) return fwd;
  return String(req.socket?.remoteAddress || req.ip || '').trim() || null;
}

function createRequireVaultAuth(pool) {
  return async function requireVaultAuth(req, res, next) {
    const token = extractBearer(req);
    if (!token) {
      return res.status(401).json({
        error: 'Autenticação do cofre obrigatória (Bearer JWT do vault-api).',
      });
    }

    let secret;
    try {
      secret = vaultJwtSecret();
    } catch (err) {
      return res.status(err.status || 503).json({ error: err.message });
    }

    let decoded;
    try {
      decoded = jwt.verify(token, secret, { issuer: 'vault-api' });
    } catch {
      return res.status(401).json({ error: 'Token do cofre inválido ou expirado' });
    }

    const email = String(decoded.email || '').trim().toLowerCase();
    if (!email) {
      return res.status(401).json({ error: 'Token do cofre malformado' });
    }

    try {
      const result = await pool.query(
        `SELECT id, email, ativo FROM vault_admins WHERE email = $1 LIMIT 1`,
        [email]
      );
      const admin = result.rows[0];
      if (!admin || !admin.ativo) {
        return res.status(403).json({ error: 'Acesso ao cofre negado' });
      }
      req.vaultAdmin = { id: admin.id, email: admin.email };
      return next();
    } catch (err) {
      console.error('[vault] auth', err.message);
      return res.status(500).json({ error: 'Falha ao validar sessão do cofre' });
    }
  };
}

module.exports = {
  JWT_TTL,
  signVaultToken,
  extractBearer,
  clientIp,
  createRequireVaultAuth,
  vaultJwtSecret,
};
