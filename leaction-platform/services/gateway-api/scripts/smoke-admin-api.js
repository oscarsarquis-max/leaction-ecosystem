'use strict';

const express = require('express');
const jwt = require('jsonwebtoken');
const { Pool } = require('pg');
const { registerAdminRoutes } = require('../admin');
require('dotenv').config({ path: '../../../.env', override: true });

const JWT_SECRET = process.env.JWT_SECRET || 'super-secret-hub-key-2026';
const ADMIN_EMAIL = process.env.HUB_SYSADMIN_EMAIL || 'sysadmin@inove4us.com.br';

const pool = new Pool({
  host: process.env.DB_HOST || '127.0.0.1',
  port: Number(process.env.DB_PORT || 5433),
  database: process.env.DB_NAME || 'leaction_hub',
  user: process.env.DB_USER || 'admin',
  password: process.env.DB_PASS || 'password123',
});

function request(app, method, url, { token, body, apiKey } = {}) {
  return new Promise((resolve, reject) => {
    const server = app.listen(0, '127.0.0.1', async () => {
      const { port } = server.address();
      try {
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers.Authorization = `Bearer ${token}`;
        if (apiKey) headers['X-Admin-Api-Key'] = apiKey;
        const res = await fetch(`http://127.0.0.1:${port}${url}`, {
          method,
          headers,
          body: body ? JSON.stringify(body) : undefined,
        });
        const text = await res.text();
        let json;
        try {
          json = JSON.parse(text);
        } catch {
          json = { raw: text };
        }
        resolve({ status: res.status, json });
      } catch (err) {
        reject(err);
      } finally {
        server.close();
      }
    });
  });
}

(async () => {
  // garante tabela
  await pool.query(`
    CREATE TABLE IF NOT EXISTS catalog_plans (
      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
      app_id TEXT NOT NULL REFERENCES app_registry(app_id),
      name TEXT NOT NULL,
      type TEXT NOT NULL CHECK (type IN ('plan', 'credit_pack', 'addon', 'seat')),
      sku TEXT NOT NULL,
      price NUMERIC(12, 2) NOT NULL DEFAULT 0,
      currency TEXT NOT NULL DEFAULT 'BRL',
      features JSONB NOT NULL DEFAULT '[]'::jsonb,
      meta_json JSONB NOT NULL DEFAULT '{}'::jsonb,
      active BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      CONSTRAINT uq_catalog_plans_app_sku UNIQUE (app_id, sku)
    )
  `).catch(async () => {
    // constraint pode já existir — tenta só CREATE IF NOT EXISTS via patch file path
    const fs = require('fs');
    const path = require('path');
    const sql = fs.readFileSync(
      path.join(__dirname, '../../../shared/database/patch_hub_catalog_plans.sql'),
      'utf8'
    );
    await pool.query(sql);
  });

  const app = express();
  app.use(express.json());
  registerAdminRoutes(app, pool, { jwtSecret: JWT_SECRET });

  const denied = await request(app, 'GET', '/admin/apps');
  if (denied.status !== 401) throw new Error(`expected 401, got ${denied.status}`);

  const token = jwt.sign({ sub: 'smoke', email: ADMIN_EMAIL }, JWT_SECRET, {
    expiresIn: '1h',
  });

  const apps = await request(app, 'GET', '/admin/apps', { token });
  if (apps.status !== 200) throw new Error(`apps ${apps.status} ${JSON.stringify(apps.json)}`);
  const sample = apps.json.apps?.[0];
  if (!sample) throw new Error('nenhum app no registry');
  if (Object.prototype.hasOwnProperty.call(sample, 'webhook_secret')) {
    throw new Error('webhook_secret vazou no GET');
  }
  if (typeof sample.has_secret !== 'boolean') {
    throw new Error('has_secret ausente');
  }
  console.log('apps_ok', sample.app_id, 'has_secret=', sample.has_secret);

  const sku = `SMOKE_CREDITS_${Date.now()}`;
  const created = await request(app, 'POST', '/admin/plans', {
    token,
    body: {
      app_id: 'inove4us',
      name: 'Pacote smoke 10',
      type: 'credit_pack',
      sku,
      price: 29.9,
      features: ['10 créditos IA'],
    },
  });
  if (created.status !== 201) {
    throw new Error(`create ${created.status} ${JSON.stringify(created.json)}`);
  }
  const planId = created.json.plan.id;

  const listed = await request(app, 'GET', '/admin/plans?app_id=inove4us', { token });
  if (listed.status !== 200 || !listed.json.plans.some((p) => p.id === planId)) {
    throw new Error('list plans falhou');
  }

  const updated = await request(app, 'PUT', `/admin/plans/${planId}`, {
    token,
    body: { price: 39.9, active: true },
  });
  if (updated.status !== 200 || Number(updated.json.plan.price) !== 39.9) {
    throw new Error(`update plan ${JSON.stringify(updated.json)}`);
  }

  const appUp = await request(app, 'PUT', '/admin/apps/inove4us', {
    token,
    body: { name: 'inove4us', active: true },
  });
  if (appUp.status !== 200 || appUp.json.app?.has_secret === undefined) {
    throw new Error(`update app ${JSON.stringify(appUp.json)}`);
  }

  console.log('SMOKE_OK', { planId, sku });
  await pool.end();
})().catch(async (e) => {
  console.error(e);
  try {
    await pool.end();
  } catch (_) {
    /* ignore */
  }
  process.exit(1);
});
