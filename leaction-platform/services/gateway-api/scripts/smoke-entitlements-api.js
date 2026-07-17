'use strict';

/**
 * Smoke da API de entitlements (sem HTTP — chama o domínio direto).
 * Garante secret no app_registry, snapshot e respostas active/empty/expired.
 */

const { Pool } = require('pg');
const {
  authenticateApp,
  getEntitlementForSubject,
} = require('../domain/entitlements-api');
require('dotenv').config({ path: '../../../.env', override: true });

const DEV_SECRET = 'dev-hub-app-secret-inove4us';
const APP_ID = 'inove4us';
const SUBJECT = 'entitlements.smoke@test.local';

const pool = new Pool({
  host: process.env.DB_HOST || '127.0.0.1',
  port: Number(process.env.DB_PORT || 5433),
  database: process.env.DB_NAME || 'leaction_hub',
  user: process.env.DB_USER || 'admin',
  password: process.env.DB_PASS || 'password123',
});

(async () => {
  await pool.query(
    `INSERT INTO app_registry (app_id, name, webhook_secret, return_origins, active)
     VALUES ($1, 'inove4us', $2, ARRAY['http://localhost:5174']::TEXT[], TRUE)
     ON CONFLICT (app_id) DO UPDATE
       SET webhook_secret = EXCLUDED.webhook_secret,
           active = TRUE`,
    [APP_ID, DEV_SECRET]
  );

  const bad = await authenticateApp(pool, APP_ID, 'wrong');
  if (bad.ok) throw new Error('auth deveria falhar com secret errado');
  console.log('auth_reject', bad);

  const ok = await authenticateApp(pool, APP_ID, DEV_SECRET);
  if (!ok.ok) throw new Error(`auth deveria passar: ${ok.error}`);
  console.log('auth_ok', ok.app.app_id);

  await pool.query(
    `INSERT INTO entitlement_snapshots (app_id, subject_id, payload_json, valid_until)
     VALUES ($1, $2, $3::jsonb, NULL)
     ON CONFLICT (app_id, subject_id) DO UPDATE
       SET payload_json = EXCLUDED.payload_json,
           valid_until = NULL,
           updated_at = CURRENT_TIMESTAMP`,
    [APP_ID, SUBJECT, JSON.stringify({ credits: 42, premium: false, plan: null })]
  );

  const active = await getEntitlementForSubject(pool, {
    appId: APP_ID,
    subjectId: SUBJECT,
  });
  console.log('active', JSON.stringify(active));
  if (!active.active || active.entitlement.credits !== 42) {
    throw new Error('snapshot ativo inválido');
  }

  const missing = await getEntitlementForSubject(pool, {
    appId: APP_ID,
    subjectId: 'nobody@test.local',
  });
  console.log('missing', JSON.stringify(missing));
  if (missing.active || missing.reason !== 'no_entitlement') {
    throw new Error('missing deveria ser no_entitlement');
  }

  await pool.query(
    `UPDATE entitlement_snapshots
     SET valid_until = NOW() - INTERVAL '1 day'
     WHERE app_id = $1 AND subject_id = $2`,
    [APP_ID, SUBJECT]
  );
  const expired = await getEntitlementForSubject(pool, {
    appId: APP_ID,
    subjectId: SUBJECT,
  });
  console.log('expired', JSON.stringify(expired));
  if (expired.active || expired.reason !== 'expired') {
    throw new Error('deveria ser expired');
  }

  console.log('SMOKE_OK');
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
