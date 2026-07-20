'use strict';

const crypto = require('crypto');

const CACHE_TTL_MS = Number(process.env.SYSTEM_CONFIG_CACHE_MS || 15000);

let lockedCache = { value: null, expiresAt: 0 };

function invalidateSystemConfigCache() {
  lockedCache = { value: null, expiresAt: 0 };
}

function setSystemLockedCache(locked) {
  lockedCache = { value: !!locked, expiresAt: Date.now() + CACHE_TTL_MS };
}

function getProductionMasterKey() {
  return String(process.env.PRODUCTION_MASTER_KEY || '').trim();
}

function isGatekeeperAdminRouteEnabled() {
  if ((process.env.NODE_ENV || 'development') === 'production') return true;
  return String(process.env.GATEKEEPER_ALLOW_DEV || '').toLowerCase() === 'true';
}

function isValidMasterSecret(providedSecret) {
  const expected = getProductionMasterKey();
  const provided = String(providedSecret || '').trim();
  if (!expected || !provided) return false;
  try {
    const a = Buffer.from(expected, 'utf8');
    const b = Buffer.from(provided, 'utf8');
    if (a.length !== b.length) return false;
    return crypto.timingSafeEqual(a, b);
  } catch {
    return false;
  }
}

function createGatekeeper(pool) {
  async function ensureTable() {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS public.system_config (
        config_key   TEXT PRIMARY KEY,
        config_value TEXT NOT NULL,
        updated_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
      )
    `);
    await pool.query(`
      INSERT INTO public.system_config (config_key, config_value)
      VALUES ('system_locked', 'true')
      ON CONFLICT (config_key) DO NOTHING
    `);
  }

  async function isSystemLocked() {
    const now = Date.now();
    if (lockedCache.value !== null && now < lockedCache.expiresAt) {
      return lockedCache.value;
    }
    await ensureTable();
    const { rows } = await pool.query(
      `SELECT config_value FROM public.system_config WHERE config_key = 'system_locked' LIMIT 1`
    );
    const locked = rows.length
      ? String(rows[0].config_value).trim().toLowerCase() === 'true'
      : true;
    setSystemLockedCache(locked);
    return locked;
  }

  async function unlockSystem() {
    await ensureTable();
    await pool.query(
      `INSERT INTO public.system_config (config_key, config_value, updated_at)
       VALUES ('system_locked', 'false', CURRENT_TIMESTAMP)
       ON CONFLICT (config_key) DO UPDATE
       SET config_value = EXCLUDED.config_value, updated_at = CURRENT_TIMESTAMP`
    );
    setSystemLockedCache(false);
  }

  async function lockSystem() {
    await ensureTable();
    await pool.query(
      `INSERT INTO public.system_config (config_key, config_value, updated_at)
       VALUES ('system_locked', 'true', CURRENT_TIMESTAMP)
       ON CONFLICT (config_key) DO UPDATE
       SET config_value = EXCLUDED.config_value, updated_at = CURRENT_TIMESTAMP`
    );
    setSystemLockedCache(true);
  }

  function registerGatekeeperRoutes(app) {
    app.get('/gatekeeper/status', async (_req, res) => {
      try {
        const locked = await isSystemLocked();
        res.set('Cache-Control', 'private, max-age=5');
        return res.json({ locked, app: 'actionhub' });
      } catch (err) {
        console.error('[Gatekeeper] status:', err.message);
        const isProd = (process.env.NODE_ENV || 'development') === 'production';
        return res.status(isProd ? 200 : 500).json({ locked: isProd, app: 'actionhub' });
      }
    });

    app.get('/gatekeeper/unlock', async (req, res) => {
      if (!isGatekeeperAdminRouteEnabled()) {
        return res.status(403).send(
          'Rotas de homologação disponíveis apenas em produção. Em dev, GATEKEEPER_ALLOW_DEV=true.'
        );
      }
      if (!getProductionMasterKey() || !isValidMasterSecret(req.query.secret)) {
        return res.status(403).send('Acesso negado.');
      }
      try {
        await unlockSystem();
        return res.status(200).send('Sistema liberado para uso geral!');
      } catch (err) {
        console.error('[Gatekeeper] unlock:', err.message);
        return res.status(500).send('Falha ao liberar o sistema.');
      }
    });

    app.get('/gatekeeper/lock', async (req, res) => {
      if (!isGatekeeperAdminRouteEnabled()) {
        return res.status(403).send(
          'Rotas de homologação disponíveis apenas em produção. Em dev, GATEKEEPER_ALLOW_DEV=true.'
        );
      }
      if (!getProductionMasterKey() || !isValidMasterSecret(req.query.secret)) {
        return res.status(403).send('Acesso negado.');
      }
      try {
        await lockSystem();
        return res
          .status(200)
          .send('Sistema BLOQUEADO. Tela de manutenção ativada para o público.');
      } catch (err) {
        console.error('[Gatekeeper] lock:', err.message);
        return res.status(500).send('Falha ao bloquear o sistema.');
      }
    });
  }

  return {
    isSystemLocked,
    unlockSystem,
    lockSystem,
    invalidateSystemConfigCache,
    registerGatekeeperRoutes,
    isValidMasterSecret,
    getProductionMasterKey,
    isGatekeeperAdminRouteEnabled,
  };
}

module.exports = { createGatekeeper };
