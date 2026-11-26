'use strict';

/**
 * BLOG-024d — avisa o blog LePain que o CMS mudou (cache em memória do blog = 60 s).
 * Nunca lança: falha de rede ou chave ausente só vira log.
 */

const axios = require('axios');

const DEFAULT_PURGE_URL = 'https://lepain.lojadepaes.com.br/api/cms/purge';
const PURGE_TIMEOUT_MS = 4000;

let warnedNoKey = false;

async function notifyLepainPurge(opts = {}) {
  const env = opts.env || process.env;
  const log = opts.logger || console;
  const key = String(env.LEPAIN_CMS_KEY || '').trim();
  if (!key) {
    if (!warnedNoKey) {
      warnedNoKey = true;
      log.warn('[lepain-purge] LEPAIN_CMS_KEY ausente; purge do blog ignorado');
    }
    return { ok: false, skipped: 'sem_chave' };
  }
  const url = String(env.LEPAIN_PURGE_URL || DEFAULT_PURGE_URL).trim();
  try {
    const res = await (opts.http || axios).post(
      url,
      {},
      {
        timeout: opts.timeoutMs || PURGE_TIMEOUT_MS,
        headers: { 'X-LePain-Key': key },
        validateStatus: () => true,
      }
    );
    if (res.status >= 200 && res.status < 300) return { ok: true, status: res.status };
    log.warn(`[lepain-purge] blog respondeu HTTP ${res.status}`);
    return { ok: false, status: res.status };
  } catch (err) {
    log.warn(`[lepain-purge] falha ao avisar o blog: ${err && err.message ? err.message : err}`);
    return { ok: false, error: String(err && err.message ? err.message : err) };
  }
}

function resetLepainPurgeWarningForTests() {
  warnedNoKey = false;
}

module.exports = {
  DEFAULT_PURGE_URL,
  PURGE_TIMEOUT_MS,
  notifyLepainPurge,
  resetLepainPurgeWarningForTests,
};
