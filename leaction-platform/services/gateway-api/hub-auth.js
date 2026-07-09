const { randomBytes, scryptSync, timingSafeEqual } = require('crypto');

const SCRYPT_KEYLEN = 64;

function hashPassword(password) {
  const salt = randomBytes(16).toString('hex');
  const hash = scryptSync(String(password), salt, SCRYPT_KEYLEN).toString('hex');
  return `scrypt$${salt}$${hash}`;
}

function verifyPassword(password, stored) {
  if (!stored || typeof stored !== 'string') return false;
  const parts = stored.split('$');
  if (parts.length !== 3 || parts[0] !== 'scrypt') return false;
  const [, salt, expectedHex] = parts;
  if (!salt || !expectedHex) return false;
  try {
    const actual = scryptSync(String(password), salt, SCRYPT_KEYLEN);
    const expected = Buffer.from(expectedHex, 'hex');
    if (actual.length !== expected.length) return false;
    return timingSafeEqual(actual, expected);
  } catch {
    return false;
  }
}

function publicUser(row) {
  if (!row) return null;
  return {
    id: row.id,
    email: row.email,
    name: row.full_name,
    document_id: row.document_id ?? null,
    phone: row.phone ?? null,
    company: row.company ?? null,
    address: row.address ?? null,
    city: row.city ?? null,
    state: row.state ?? null,
  };
}

/**
 * Garante coluna password_hash (idempotente).
 */
async function ensurePasswordColumn(pool) {
  await pool.query('ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT');
}

/**
 * Login / primeiro acesso:
 * - usuário inexistente → cria conta com a senha informada
 * - usuário sem senha → define a senha (migração do fluxo só-e-mail)
 * - usuário com senha → valida
 */
async function loginOrRegister(pool, { email, password, name }) {
  const emailNorm = String(email || '')
    .trim()
    .toLowerCase();
  const pass = String(password || '');
  const displayName = String(name || '').trim() || emailNorm.split('@')[0] || 'LeActioner';

  if (!emailNorm.includes('@')) {
    const err = new Error('E-mail inválido');
    err.status = 400;
    throw err;
  }
  if (pass.length < 4) {
    const err = new Error('Senha deve ter pelo menos 4 caracteres');
    err.status = 400;
    throw err;
  }

  await ensurePasswordColumn(pool);

  const existing = await pool.query(
    `SELECT id, email, full_name, document_id, phone, company, address, city, state, password_hash
     FROM users WHERE email = $1`,
    [emailNorm]
  );

  if (!existing.rows.length) {
    const passwordHash = hashPassword(pass);
    const inserted = await pool.query(
      `INSERT INTO users (email, full_name, password_hash)
       VALUES ($1, $2, $3)
       RETURNING id, email, full_name, document_id, phone, company, address, city, state`,
      [emailNorm, displayName, passwordHash]
    );
    return { user: publicUser(inserted.rows[0]), created: true };
  }

  const row = existing.rows[0];
  if (!row.password_hash) {
    const passwordHash = hashPassword(pass);
    const updated = await pool.query(
      `UPDATE users SET password_hash = $2
       WHERE id = $1
       RETURNING id, email, full_name, document_id, phone, company, address, city, state`,
      [row.id, passwordHash]
    );
    return { user: publicUser(updated.rows[0]), created: false, passwordSet: true };
  }

  if (!verifyPassword(pass, row.password_hash)) {
    const err = new Error('Usuário ou senha inválidos');
    err.status = 401;
    throw err;
  }

  return { user: publicUser(row), created: false };
}

module.exports = {
  hashPassword,
  verifyPassword,
  publicUser,
  ensurePasswordColumn,
  loginOrRegister,
};
