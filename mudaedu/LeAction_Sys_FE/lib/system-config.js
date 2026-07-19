'use strict';

const { pool } = require('./postgres-pool');

/** Cache em memória — evita query a cada clique (padrão: 15s). */
const CACHE_TTL_MS = Number(process.env.SYSTEM_CONFIG_CACHE_MS || 15000);

let lockedCache = {
    value: null,
    expiresAt: 0,
};

function invalidateSystemConfigCache() {
    lockedCache = { value: null, expiresAt: 0 };
}

/** Atualiza cache imediatamente (ex.: após GET /gatekeeper/unlock ou /gatekeeper/lock). */
function setSystemLockedCache(locked) {
    lockedCache = {
        value: !!locked,
        expiresAt: Date.now() + CACHE_TTL_MS,
    };
}

async function getConfigValue(configKey, defaultValue = null) {
    const { rows } = await pool.query(
        `SELECT config_value
         FROM public.system_config
         WHERE config_key = $1
         LIMIT 1`,
        [configKey]
    );
    if (!rows.length) {
        return defaultValue;
    }
    return rows[0].config_value;
}

async function isSystemLocked() {
    const now = Date.now();
    if (lockedCache.value !== null && now < lockedCache.expiresAt) {
        return lockedCache.value;
    }

    const raw = await getConfigValue('system_locked', 'false');
    const locked = String(raw).trim().toLowerCase() === 'true';
    lockedCache = {
        value: locked,
        expiresAt: now + CACHE_TTL_MS,
    };
    return locked;
}

async function unlockSystem() {
    const result = await pool.query(
        `UPDATE public.system_config
         SET config_value = 'false'
         WHERE config_key = 'system_locked'`
    );

    if (result.rowCount === 0) {
        await pool.query(
            `INSERT INTO public.system_config (config_key, config_value)
             VALUES ('system_locked', 'false')
             ON CONFLICT (config_key) DO UPDATE
             SET config_value = EXCLUDED.config_value`
        );
    }

    setSystemLockedCache(false);
}

async function lockSystem() {
    const result = await pool.query(
        `UPDATE public.system_config
         SET config_value = 'true'
         WHERE config_key = 'system_locked'`
    );

    if (result.rowCount === 0) {
        await pool.query(
            `INSERT INTO public.system_config (config_key, config_value)
             VALUES ('system_locked', 'true')
             ON CONFLICT (config_key) DO UPDATE
             SET config_value = EXCLUDED.config_value`
        );
    }

    setSystemLockedCache(true);
}

module.exports = {
    getConfigValue,
    isSystemLocked,
    unlockSystem,
    lockSystem,
    invalidateSystemConfigCache,
    setSystemLockedCache,
};
