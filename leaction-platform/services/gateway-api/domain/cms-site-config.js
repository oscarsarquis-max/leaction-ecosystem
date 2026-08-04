'use strict';

/**
 * Micro-CMS migrado do PanelDX (ctdi_cms_config → cms_site_config no Hub).
 * APIs: GET /api/public/cms · GET/PUT /api/admin/cms
 * Query/body: config_key=default|inove4us|inove4us-school (default = landing PanelDX).
 *
 * Persistência:
 * - Postgres = leitura rápida / operacional
 * - S3 (CMS_S3_BUCKET) = snapshot durável por config_key
 *   Em todo PUT admin, grava DB + S3.
 *   No boot (e se o DB estiver vazio), reidrata do S3.
 * Deploy de app NÃO deve apagar o S3 — conteúdo de CMS sobrevive.
 */

const { createRequireAdminAuth } = require('../admin/auth');
const {
  defaultsForConfigKey,
  serializeCmsRow,
  normalizeCmsLanding,
} = require('./cms-landing');
const {
  applyBlogPostsToLanding,
  stripBlogColumnsFromLanding,
} = require('./cms-blog-sync');
const cmsS3 = require('../lib/cms-s3-storage');

const ALLOWED_CONFIG_KEYS = new Set(['default', 'inove4us', 'inove4us-school']);

function resolveConfigKey(raw) {
  const key = String(raw || 'default').trim().toLowerCase() || 'default';
  return ALLOWED_CONFIG_KEYS.has(key) ? key : null;
}

async function ensureTable(pool) {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS cms_site_config (
      id_cms SERIAL PRIMARY KEY,
      config_key VARCHAR(50) NOT NULL DEFAULT 'default',
      landing_page_data JSONB NOT NULL DEFAULT '{}'::jsonb,
      instructions_data TEXT,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
      CONSTRAINT uq_cms_site_config_key UNIQUE (config_key)
    )
  `);
}

async function upsertSiteRow(pool, configKey, landing, instructions) {
  await pool.query(
    `INSERT INTO cms_site_config (config_key, landing_page_data, instructions_data, updated_at)
     VALUES ($1, $2::jsonb, $3, CURRENT_TIMESTAMP)
     ON CONFLICT (config_key) DO UPDATE
       SET landing_page_data = EXCLUDED.landing_page_data,
           instructions_data = EXCLUDED.instructions_data,
           updated_at = CURRENT_TIMESTAMP`,
    [
      configKey,
      JSON.stringify(landing ?? {}),
      instructions == null ? null : String(instructions),
    ]
  );
}

async function seedConfigIfNeeded(pool, configKey) {
  const existing = await pool.query(
    `SELECT id_cms FROM cms_site_config WHERE config_key = $1 LIMIT 1`,
    [configKey]
  );
  if (existing.rows.length) return;
  const { landing, instructions } = defaultsForConfigKey(configKey);
  await pool.query(
    `INSERT INTO cms_site_config (config_key, landing_page_data, instructions_data)
     VALUES ($1, $2::jsonb, $3)
     ON CONFLICT (config_key) DO NOTHING`,
    [configKey, JSON.stringify(landing), instructions]
  );
}

/**
 * Se existir snapshot no S3, aplica no Postgres (S3 vence).
 * @returns {boolean} true se reidratou
 */
async function hydrateSiteConfigFromS3(pool, configKey) {
  if (!cmsS3.isCmsS3Enabled()) return false;
  try {
    const snap = await cmsS3.getCmsSiteConfig(configKey);
    if (!snap) return false;
    const { landing: defaultLanding } = defaultsForConfigKey(configKey);
    let landing = normalizeCmsLanding(snap.landing_page_data || {}, defaultLanding);
    if (configKey === 'default') {
      landing = stripBlogColumnsFromLanding(landing);
    }
    await upsertSiteRow(pool, configKey, landing, snap.instructions_data);
    console.log(`[cms-site] Reidratado config_key=${configKey} a partir do S3`);
    return true;
  } catch (err) {
    console.warn(`[cms-site] Falha ao ler S3 (${configKey}):`, err.message);
    return false;
  }
}

async function persistSiteConfigToS3(configKey, landing, instructions) {
  if (!cmsS3.isCmsS3Enabled()) return null;
  try {
    const saved = await cmsS3.putCmsSiteConfig(configKey, {
      landing_page_data: landing,
      instructions_data: instructions,
    });
    console.log(
      `[cms-site] Snapshot S3 ok config_key=${configKey} key=${saved.objectKey}`
    );
    return saved;
  } catch (err) {
    console.error(`[cms-site] Falha ao gravar S3 (${configKey}):`, err.message);
    throw err;
  }
}

async function fetchRow(pool, configKey = 'default') {
  await ensureTable(pool);
  await seedConfigIfNeeded(pool, configKey);
  const result = await pool.query(
    `SELECT landing_page_data, instructions_data, updated_at
     FROM cms_site_config
     WHERE config_key = $1
     LIMIT 1`,
    [configKey]
  );
  return result.rows[0] || null;
}

/**
 * No boot: garante tabela + tenta puxar S3 para cada key conhecida.
 * Assim um deploy/restart não “esquece” o conteúdo de produção.
 */
async function hydrateAllSiteConfigsFromS3(pool) {
  if (!cmsS3.isCmsS3Enabled()) {
    console.log(
      '[cms-site] CMS_S3_BUCKET ausente — snapshots de site config desativados (só Postgres).'
    );
    return;
  }
  await ensureTable(pool);
  for (const key of ALLOWED_CONFIG_KEYS) {
    await hydrateSiteConfigFromS3(pool, key);
  }
}

/**
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {{ jwtSecret?: string }} [options]
 */
function registerCmsSiteConfigRoutes(app, pool, options = {}) {
  const requireAdmin = createRequireAdminAuth(options.jwtSecret || process.env.JWT_SECRET);

  async function serializeWithBlog(row, configKey) {
    const base = serializeCmsRow(row, configKey);
    if (configKey !== 'default') {
      return base;
    }
    const landing = await applyBlogPostsToLanding(base.landing_page_data);
    return { ...base, landing_page_data: landing };
  }

  app.get('/api/public/cms', async (req, res) => {
    const configKey = resolveConfigKey(req.query.config_key || req.query.sistema);
    if (!configKey) {
      return res.status(400).json({
        success: false,
        error: `config_key inválido (use: ${[...ALLOWED_CONFIG_KEYS].join(', ')})`,
      });
    }
    try {
      let row = await fetchRow(pool, configKey);
      // Se o seed default ainda está “vazio” e há S3, tenta reidratar sob demanda.
      if (cmsS3.isCmsS3Enabled()) {
        const landing = row?.landing_page_data;
        const emptyish =
          !landing ||
          (typeof landing === 'object' && Object.keys(landing).length === 0);
        if (emptyish) {
          const ok = await hydrateSiteConfigFromS3(pool, configKey);
          if (ok) row = await fetchRow(pool, configKey);
        }
      }
      return res.status(200).json({ success: true, ...(await serializeWithBlog(row, configKey)) });
    } catch (err) {
      console.error('[cms-site] GET /api/public/cms', err.message);
      return res.status(200).json({
        success: true,
        ...(await serializeWithBlog(null, configKey)),
      });
    }
  });

  app.get('/api/admin/cms', requireAdmin, async (req, res) => {
    const configKey = resolveConfigKey(req.query.config_key || req.query.sistema);
    if (!configKey) {
      return res.status(400).json({
        success: false,
        error: `config_key inválido (use: ${[...ALLOWED_CONFIG_KEYS].join(', ')})`,
      });
    }
    try {
      const row = await fetchRow(pool, configKey);
      return res.status(200).json({ success: true, ...(await serializeWithBlog(row, configKey)) });
    } catch (err) {
      console.error('[cms-site] GET /api/admin/cms', err.message);
      return res.status(500).json({ success: false, error: 'Falha ao carregar CMS' });
    }
  });

  app.put('/api/admin/cms', requireAdmin, async (req, res) => {
    try {
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const configKey = resolveConfigKey(
        body.config_key || req.query.config_key || req.query.sistema
      );
      if (!configKey) {
        return res.status(400).json({
          success: false,
          error: `config_key inválido (use: ${[...ALLOWED_CONFIG_KEYS].join(', ')})`,
        });
      }

      let landing = body.landing_page_data;
      const instructions = body.instructions_data;

      if (landing == null && instructions == null) {
        return res.status(400).json({
          success: false,
          error: 'Nenhum dado para atualizar.',
        });
      }

      await ensureTable(pool);
      await seedConfigIfNeeded(pool, configKey);

      const { landing: defaultLanding } = defaultsForConfigKey(configKey);

      if (landing != null) {
        landing = normalizeCmsLanding(landing, defaultLanding);
        if (configKey === 'default') {
          landing = stripBlogColumnsFromLanding(landing);
        }
      }

      let result;
      if (landing != null && instructions != null) {
        result = await pool.query(
          `UPDATE cms_site_config
           SET landing_page_data = $1::jsonb,
               instructions_data = $2,
               updated_at = CURRENT_TIMESTAMP
           WHERE config_key = $3
           RETURNING landing_page_data, instructions_data, updated_at`,
          [JSON.stringify(landing), String(instructions), configKey]
        );
      } else if (landing != null) {
        result = await pool.query(
          `UPDATE cms_site_config
           SET landing_page_data = $1::jsonb,
               updated_at = CURRENT_TIMESTAMP
           WHERE config_key = $2
           RETURNING landing_page_data, instructions_data, updated_at`,
          [JSON.stringify(landing), configKey]
        );
      } else {
        result = await pool.query(
          `UPDATE cms_site_config
           SET instructions_data = $1,
               updated_at = CURRENT_TIMESTAMP
           WHERE config_key = $2
           RETURNING landing_page_data, instructions_data, updated_at`,
          [String(instructions), configKey]
        );
      }

      const savedRow = result.rows[0];
      // Snapshot durável — falha no S3 não descarta o save no DB, mas avisa.
      let s3Meta = null;
      if (cmsS3.isCmsS3Enabled()) {
        try {
          s3Meta = await persistSiteConfigToS3(
            configKey,
            savedRow.landing_page_data,
            savedRow.instructions_data
          );
        } catch (s3err) {
          console.error(
            '[cms-site] Conteúdo salvo no Postgres, mas snapshot S3 falhou:',
            s3err.message
          );
        }
      }

      return res.status(200).json({
        success: true,
        ...serializeCmsRow(savedRow, configKey),
        s3_snapshot: s3Meta
          ? { ok: true, objectKey: s3Meta.objectKey, updated_at: s3Meta.updated_at }
          : cmsS3.isCmsS3Enabled()
            ? { ok: false }
            : { ok: false, skipped: true },
      });
    } catch (err) {
      console.error('[cms-site] PUT /api/admin/cms', err.message);
      return res.status(500).json({ success: false, error: 'Falha ao salvar CMS' });
    }
  });

  // Boot async — não bloqueia o listen do gateway.
  void hydrateAllSiteConfigsFromS3(pool).catch((err) => {
    console.warn('[cms-site] hydrate boot:', err.message);
  });

  console.log(
    '📰 [cms] Micro-CMS site (/api/public/cms + /api/admin/cms) registrado — keys: default, inove4us, inove4us-school' +
      (cmsS3.isCmsS3Enabled() ? ' · S3 snapshot ON' : ' · S3 snapshot OFF')
  );
}

module.exports = {
  registerCmsSiteConfigRoutes,
  ensureTable,
  fetchRow,
  resolveConfigKey,
  ALLOWED_CONFIG_KEYS,
  hydrateAllSiteConfigsFromS3,
  persistSiteConfigToS3,
};
