'use strict';

/**
 * Micro-CMS migrado do PanelDX (ctdi_cms_config → cms_site_config no Hub).
 * APIs compatíveis: GET /api/public/cms · GET/PUT /api/admin/cms
 */

const { createRequireAdminAuth } = require('../admin/auth');
const {
  defaultCmsLanding,
  defaultCmsInstructions,
  normalizeCmsLanding,
  serializeCmsRow,
} = require('./cms-landing');
const {
  applyBlogPostsToLanding,
  stripBlogColumnsFromLanding,
} = require('./cms-blog-sync');

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

async function seedDefaultIfNeeded(pool) {
  const existing = await pool.query(
    `SELECT id_cms FROM cms_site_config WHERE config_key = 'default' LIMIT 1`
  );
  if (existing.rows.length) return;
  await pool.query(
    `INSERT INTO cms_site_config (config_key, landing_page_data, instructions_data)
     VALUES ('default', $1::jsonb, $2)
     ON CONFLICT (config_key) DO NOTHING`,
    [JSON.stringify(defaultCmsLanding()), defaultCmsInstructions()]
  );
}

async function fetchRow(pool) {
  await ensureTable(pool);
  await seedDefaultIfNeeded(pool);
  const result = await pool.query(
    `SELECT landing_page_data, instructions_data, updated_at
     FROM cms_site_config
     WHERE config_key = 'default'
     LIMIT 1`
  );
  return result.rows[0] || null;
}

/**
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {{ jwtSecret?: string }} [options]
 */
function registerCmsSiteConfigRoutes(app, pool, options = {}) {
  const requireAdmin = createRequireAdminAuth(options.jwtSecret || process.env.JWT_SECRET);

  async function serializeWithBlog(row) {
    const base = serializeCmsRow(row);
    const landing = await applyBlogPostsToLanding(base.landing_page_data);
    return { ...base, landing_page_data: landing };
  }

  app.get('/api/public/cms', async (_req, res) => {
    try {
      const row = await fetchRow(pool);
      return res.status(200).json({ success: true, ...(await serializeWithBlog(row)) });
    } catch (err) {
      console.error('[cms-site] GET /api/public/cms', err.message);
      return res.status(200).json({
        success: true,
        ...(await serializeWithBlog(null)),
      });
    }
  });

  app.get('/api/admin/cms', requireAdmin, async (_req, res) => {
    try {
      const row = await fetchRow(pool);
      return res.status(200).json({ success: true, ...(await serializeWithBlog(row)) });
    } catch (err) {
      console.error('[cms-site] GET /api/admin/cms', err.message);
      return res.status(500).json({ success: false, error: 'Falha ao carregar CMS' });
    }
  });

  app.put('/api/admin/cms', requireAdmin, async (req, res) => {
    try {
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      let landing = body.landing_page_data;
      const instructions = body.instructions_data;

      if (landing == null && instructions == null) {
        return res.status(400).json({
          success: false,
          error: 'Nenhum dado para atualizar.',
        });
      }

      await ensureTable(pool);
      await seedDefaultIfNeeded(pool);

      if (landing != null) {
        landing = stripBlogColumnsFromLanding(normalizeCmsLanding(landing));
      }

      let result;
      if (landing != null && instructions != null) {
        result = await pool.query(
          `UPDATE cms_site_config
           SET landing_page_data = $1::jsonb,
               instructions_data = $2,
               updated_at = CURRENT_TIMESTAMP
           WHERE config_key = 'default'
           RETURNING landing_page_data, instructions_data, updated_at`,
          [JSON.stringify(landing), String(instructions)]
        );
      } else if (landing != null) {
        result = await pool.query(
          `UPDATE cms_site_config
           SET landing_page_data = $1::jsonb,
               updated_at = CURRENT_TIMESTAMP
           WHERE config_key = 'default'
           RETURNING landing_page_data, instructions_data, updated_at`,
          [JSON.stringify(landing)]
        );
      } else {
        result = await pool.query(
          `UPDATE cms_site_config
           SET instructions_data = $1,
               updated_at = CURRENT_TIMESTAMP
           WHERE config_key = 'default'
           RETURNING landing_page_data, instructions_data, updated_at`,
          [String(instructions)]
        );
      }

      return res.status(200).json({
        success: true,
        ...serializeCmsRow(result.rows[0]),
      });
    } catch (err) {
      console.error('[cms-site] PUT /api/admin/cms', err.message);
      return res.status(500).json({ success: false, error: 'Falha ao salvar CMS' });
    }
  });

  console.log('📰 [cms] Micro-CMS site (/api/public/cms + /api/admin/cms) registrado');
}

module.exports = { registerCmsSiteConfigRoutes, ensureTable, fetchRow };
