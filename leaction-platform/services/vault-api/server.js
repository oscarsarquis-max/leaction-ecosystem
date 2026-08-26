'use strict';

/**
 * vault-api — cofre de credenciais de infraestrutura (isolado do Action Hub).
 *
 * Variáveis de ambiente:
 *   VAULT_DATABASE_URL   Postgres leaction_vault (NÃO use o DATABASE_URL do Hub)
 *   VAULT_MASTER_KEY     32 bytes AES-256-GCM (hex 64 chars ou base64) — nunca no banco
 *   VAULT_JWT_SECRET     JWT próprio deste serviço (não reaproveitar JWT_SECRET do Hub)
 *   VAULT_PORT           porta HTTP (default 4020)
 *
 * Rotação: POST /api/secrets/:id/rotacionar (+ confirmar-aplicacao / historico).
 * Este processo é o único que deve ter credencial de escrita em leaction_vault.
 */

const express = require('express');
const cors = require('cors');
const path = require('path');

require('dotenv').config({
  path: path.join(__dirname, '.env'),
  override: true,
});

const { createPool } = require('./lib/db');
const { createRequireVaultAuth } = require('./lib/auth');
const { registerAuthRoutes } = require('./domain/auth-routes');
const { registerSistemasRoutes } = require('./domain/sistemas');
const { registerSecretsRoutes } = require('./domain/secrets');

function createApp(pool) {
  const app = express();
  app.use(cors());
  app.use(express.json({ limit: '256kb' }));

  app.get('/health', (_req, res) => {
    res.status(200).json({ ok: true, service: 'vault-api' });
  });
  app.get('/api/health', (_req, res) => {
    res.status(200).json({ ok: true, service: 'vault-api' });
  });

  registerAuthRoutes(app, pool);

  const requireAuth = createRequireVaultAuth(pool);
  registerSistemasRoutes(app, pool, { requireAuth });
  registerSecretsRoutes(app, pool, { requireAuth });

  app.use((req, res) => {
    res.status(404).json({ error: 'Rota não encontrada no cofre' });
  });

  return app;
}

function start() {
  const pool = createPool();
  const app = createApp(pool);
  const port = Number(process.env.VAULT_PORT || 4020);
  app.listen(port, () => {
    console.log(`🔐 vault-api online na porta ${port}`);
  });
}

if (require.main === module) {
  start();
}

module.exports = { createApp, start };
