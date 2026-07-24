/**
 * Exemplo Node (PanelDX / BFF) — GET /api/noticias ou /bff/noticias
 *
 * Em produção no PanelDX, /api/* costuma ir para o Flask no ALB.
 * Prefira registrar no Express como /bff/noticias, ou espelhar a mesma
 * lógica no Flask (ver inove4us/backend/cms_noticias_routes.py).
 *
 * Uso:
 *   const { createNoticiasHandler } = require('./cms-consumer-noticias');
 *   app.get('/bff/noticias', createNoticiasHandler({ sistema: 'paneldx' }));
 */

'use strict';

const CACHE_TTL_MS = Number(process.env.CMS_CACHE_TTL_MS || 8 * 60 * 1000);
const HUB_TIMEOUT_MS = Number(process.env.CMS_HUB_TIMEOUT_MS || 3500);

const cache = new Map(); // key -> { posts, fetchedAt }

function hubBase() {
  return (
    process.env.ACTION_HUB_API_URL ||
    process.env.HUB_API_URL ||
    'http://127.0.0.1:4001'
  ).replace(/\/$/, '');
}

async function fetchFromHub(sistema, limit) {
  const url = new URL(`${hubBase()}/api/cms/posts`);
  url.searchParams.set('sistema_destino', sistema);
  url.searchParams.set('limit', String(limit));

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), HUB_TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      signal: ctrl.signal,
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) throw new Error(`Hub HTTP ${res.status}`);
    const data = await res.json();
    return Array.isArray(data?.posts) ? data.posts : [];
  } finally {
    clearTimeout(timer);
  }
}

function createNoticiasHandler(options = {}) {
  const defaultSistema = options.sistema || 'paneldx';
  const defaultLimit = options.limit || 5;

  return async function noticiasHandler(req, res) {
    const sistema = String(req.query.sistema_destino || defaultSistema).trim() || defaultSistema;
    let limit = parseInt(String(req.query.limit || defaultLimit), 10);
    if (!Number.isFinite(limit) || limit < 1) limit = defaultLimit;
    if (limit > 50) limit = 50;

    const key = `${sistema}:${limit}`;
    const now = Date.now();
    const hit = cache.get(key);
    if (hit && now - hit.fetchedAt < CACHE_TTL_MS) {
      return res.status(200).json(hit.posts);
    }

    try {
      const posts = await fetchFromHub(sistema, limit);
      cache.set(key, { posts, fetchedAt: now });
      return res.status(200).json(posts);
    } catch (err) {
      console.warn('[cms] Hub indisponível:', err?.message || err);
      if (hit?.posts) return res.status(200).json(hit.posts);
      return res.status(200).json([]);
    }
  };
}

module.exports = { createNoticiasHandler, fetchFromHub };
