'use strict';

const { verifyPassword } = require('../lib/passwords');
const { JWT_TTL, signVaultToken } = require('../lib/auth');

function registerAuthRoutes(app, pool) {
  app.post('/api/auth/login', async (req, res) => {
    try {
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const email = String(body.email || '').trim().toLowerCase();
      const senha = String(body.senha || '');
      if (!email || !senha) {
        return res.status(400).json({ error: 'Campos obrigatórios: email, senha' });
      }

      const result = await pool.query(
        `SELECT id, email, senha_hash, ativo FROM vault_admins WHERE email = $1 LIMIT 1`,
        [email]
      );
      const admin = result.rows[0];
      if (!admin || !admin.ativo || !verifyPassword(senha, admin.senha_hash)) {
        return res.status(401).json({ error: 'E-mail ou senha inválidos' });
      }

      const access_token = signVaultToken({ id: admin.id, email: admin.email });
      return res.status(200).json({
        access_token,
        token_type: 'bearer',
        expires_in: JWT_TTL,
        admin: { id: admin.id, email: admin.email },
      });
    } catch (err) {
      const status = err.status || 500;
      if (status === 503) {
        return res.status(503).json({ error: err.message });
      }
      console.error('[vault] POST /api/auth/login', err.message);
      return res.status(500).json({ error: 'Falha no login do cofre' });
    }
  });
}

module.exports = { registerAuthRoutes };
