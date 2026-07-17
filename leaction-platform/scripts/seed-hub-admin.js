/**
 * Seed do administrador nativo do Action Hub.
 *
 * Uso:
 *   node scripts/seed-hub-admin.js
 *   DATABASE_URL=postgresql://... node scripts/seed-hub-admin.js
 *
 * Defaults:
 *   email    = admin@actionhub.com.br
 *   password = ActionHub2026
 *   name     = Admin ActionHub
 *
 * Override:
 *   HUB_ADMIN_EMAIL / HUB_ADMIN_PASSWORD / HUB_ADMIN_NAME
 */
'use strict';

const { Client } = require('pg');
const { hashPassword } = require('../services/gateway-api/hub-auth');

const DATABASE_URL =
  process.env.DATABASE_URL ||
  'postgresql://admin:password123@localhost:5433/leaction_hub';
const EMAIL = (process.env.HUB_ADMIN_EMAIL || 'admin@actionhub.com.br')
  .trim()
  .toLowerCase();
const PASSWORD = process.env.HUB_ADMIN_PASSWORD || 'ActionHub2026';
const NAME = process.env.HUB_ADMIN_NAME || 'Admin ActionHub';

function stripSslMode(url) {
  if (!url) return '';
  let out = String(url).replace(/([?&])sslmode=[^&]*/gi, '$1');
  return out.replace(/\?&/, '?').replace(/[?&]$/, '');
}

async function main() {
  const forceSsl =
    /sslmode=(require|verify-full|verify-ca)/i.test(DATABASE_URL) ||
    DATABASE_URL.includes('rds.amazonaws.com');
  const client = new Client({
    connectionString: forceSsl ? stripSslMode(DATABASE_URL) : DATABASE_URL,
    ssl: forceSsl ? { rejectUnauthorized: false } : false,
  });
  await client.connect();
  await client.query('ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT');

  const passwordHash = hashPassword(PASSWORD);
  const existing = await client.query('SELECT id, email FROM users WHERE email = $1', [
    EMAIL,
  ]);

  if (existing.rows.length) {
    await client.query(
      `UPDATE users
       SET full_name = $2, password_hash = $3
       WHERE email = $1`,
      [EMAIL, NAME, passwordHash]
    );
    console.log(`updated ${EMAIL} (${existing.rows[0].id})`);
  } else {
    const inserted = await client.query(
      `INSERT INTO users (email, full_name, password_hash)
       VALUES ($1, $2, $3)
       RETURNING id`,
      [EMAIL, NAME, passwordHash]
    );
    console.log(`created ${EMAIL} (${inserted.rows[0].id})`);
  }

  console.log('');
  console.log('────────────────────────────────────────');
  console.log('Action Hub admin seed');
  console.log(`  email:    ${EMAIL}`);
  console.log(`  password: ${PASSWORD}`);
  console.log(`  name:     ${NAME}`);
  console.log('────────────────────────────────────────');
  console.log(
    'Garanta que este e-mail esteja em HUB_ADMIN_EMAILS / NEXT_PUBLIC_HUB_ADMIN_EMAILS.'
  );

  await client.end();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
