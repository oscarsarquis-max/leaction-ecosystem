/**
 * Upsert do sysadmin ActionHub (login home + Action-Sponge).
 *
 * Uso:
 *   node scripts/seed-hub-sysadmin.js
 *   DATABASE_URL=postgresql://... node scripts/seed-hub-sysadmin.js
 *
 * Defaults:
 *   email    = sysadmin@inove4us.com.br
 *   password = Curadoria2026
 *   name     = SysAdmin inove4us
 */
const { Client } = require('pg');
const { hashPassword } = require('../services/gateway-api/hub-auth');

const DATABASE_URL =
  process.env.DATABASE_URL ||
  'postgresql://admin:password123@localhost:5433/leaction_hub';
const EMAIL = (process.env.HUB_SYSADMIN_EMAIL || 'sysadmin@inove4us.com.br')
  .trim()
  .toLowerCase();
const PASSWORD = process.env.HUB_SYSADMIN_PASSWORD || 'Curadoria2026';
const NAME = process.env.HUB_SYSADMIN_NAME || 'SysAdmin inove4us';

async function main() {
  const forceSsl =
    /sslmode=(require|verify-full|verify-ca)/i.test(DATABASE_URL) ||
    DATABASE_URL.includes('rds.amazonaws.com');
  const client = new Client({
    connectionString: DATABASE_URL,
    ssl: forceSsl ? { rejectUnauthorized: false } : false,
  });
  await client.connect();
  await client.query('ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT');

  const passwordHash = hashPassword(PASSWORD);
  const existing = await client.query('SELECT id, email FROM users WHERE email = $1', [EMAIL]);

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

  await client.end();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
